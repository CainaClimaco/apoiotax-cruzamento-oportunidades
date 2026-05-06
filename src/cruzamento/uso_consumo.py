"""
uso_consumo.py
──────────────
Motor de Cruzamento e Análise de Elegibilidade de Crédito — Uso & Consumo.

Fluxo:
  1. Carrega configuração parametrizada (CFOPs, CSTs, alíquotas padrão)
  2. Identifica o regime tributário via COD_INC_TRIB do registro 0000 da EFD Contribuições
  3. Extrai e normaliza C100/C170/0150 de ambas as EFDs
  4. Filtra entradas válidas (IND_OPER=0, COD_SIT in {00,01})
  5. Constrói chave de vinculação: CHV_NFE (primária) | CNPJ+NUM+SER+DATA (fallback)
  6. Vincula C170 ao seu C100 pai via ID_PAI → ID_SPED
  7. Executa join full entre as duas EFDs; detecta órfãos
  8. Filtra itens de uso & consumo por CFOP e CST
  9. Aplica as 4 regras de elegibilidade e calcula crédito PIS/COFINS
 10. Gera DataFrames de Resumo, Detalhes e Órfãos → write_excel
"""

import json
import time
import polars as pl
import datatricks.sped.conversor_sped as cv
import datatricks.sped.sped_definitions as dfn
import cruzamento.cruzamento_definition as cd
import cruzamento.dados_uso_consumo as duc
import cruzamento.empresa as em
import cruzamento.write_excel as we
import cruzamento.classificador_llm as cllm


# ─── Configuration ───────────────────────────────────────────────────────────

def _load_config() -> dict:
    """Loads the parametrized JSON config for CFOPs, CSTs, and default rates."""
    with open(cd.CAMINHO_UC_CONFIG, encoding="utf-8") as fh:
        return json.load(fh)


def _get_versao(df: pl.DataFrame) -> str | None:
    """Safely extracts the SPED version from a parsed DataFrame."""
    if df.is_empty() or dfn.VERSAO not in df.columns:
        return None
    val = df.select(pl.col(dfn.VERSAO).max()).item(0, 0)
    return str(val) if val is not None else None


# ─── Join key construction ────────────────────────────────────────────────────

def _build_join_key(df: pl.DataFrame, suffix: str) -> pl.DataFrame:
    """
    Builds JOIN_KEY at the NF (document) level — used to carry CHV_NFE or the
    composite fallback into joined item rows.

    Primary  : CHV_NFE (44-digit NF-e key)
    Fallback : CNPJ_EMIT|NUM_DOC|SER|DT_DOC
    """
    exprs = []

    has_chv  = "CHV_NFE" in df.columns
    has_num  = "NUM_DOC" in df.columns
    has_ser  = "SER" in df.columns
    has_dt   = "DT_DOC" in df.columns
    cnpj_col = "CNPJ_EMIT" if "CNPJ_EMIT" in df.columns else (
                dfn.CNPJ if dfn.CNPJ in df.columns else None)

    if has_chv and has_num and cnpj_col:
        fallback_parts = [p for p in [cnpj_col, "NUM_DOC",
                                       "SER" if has_ser else None,
                                       "DT_DOC" if has_dt else None]
                          if p is not None]
        exprs.append(
            pl.when(pl.col("CHV_NFE").is_not_null() & pl.col("CHV_NFE").str.len_chars().gt(0))
            .then(pl.col("CHV_NFE"))
            .otherwise(pl.concat_str([pl.col(p).fill_null("") for p in fallback_parts], separator="|"))
            .alias(cd.JOIN_KEY)
        )
    elif has_chv:
        exprs.append(pl.col("CHV_NFE").alias(cd.JOIN_KEY))
    elif has_num and cnpj_col:
        fallback_parts = [cnpj_col, "NUM_DOC"]
        if has_ser: fallback_parts.append("SER")
        if has_dt:  fallback_parts.append("DT_DOC")
        exprs.append(
            pl.concat_str([pl.col(p).fill_null("") for p in fallback_parts], separator="|")
            .alias(cd.JOIN_KEY)
        )
    else:
        exprs.append(pl.lit(None).cast(pl.Utf8).alias(cd.JOIN_KEY))

    return df.with_columns(exprs)


def _build_item_key(df: pl.DataFrame) -> pl.DataFrame:
    """
    Builds ITEM_KEY at the NF-item level for cross-EFD matching.

    This key uniquely identifies a single line item within a nota fiscal,
    enabling precise matching between EFD ICMS IPI and EFD Contribuições.

    Primary  : CHV_NFE  + COD_ITEM + NUM_ITEM
    Fallback : CNPJ_EMIT + NUM_DOC + SER + DT_DOC + COD_ITEM + NUM_ITEM

    JOIN_KEY must already be present on the DataFrame (call _build_join_key first
    on the parent C100, which carries CHV_NFE into C170 rows via the ID_PAI join).
    """
    item_extras = [c for c in ["COD_ITEM", "NUM_ITEM"] if c in df.columns]

    if not item_extras:
        # No item discriminator available — fall back to document-level key
        return df.with_columns(pl.col(cd.JOIN_KEY).alias("ITEM_KEY"))

    has_chv = "CHV_NFE" in df.columns
    cnpj_col = "CNPJ_EMIT" if "CNPJ_EMIT" in df.columns else (
                dfn.CNPJ if dfn.CNPJ in df.columns else None)

    if has_chv:
        primary_parts  = ["CHV_NFE"] + item_extras
        fallback_candidates = [cnpj_col, "NUM_DOC", "SER", "DT_DOC"] if cnpj_col else ["NUM_DOC", "SER", "DT_DOC"]
        fallback_parts = [c for c in fallback_candidates + item_extras if c in df.columns]

        expr = (
            pl.when(pl.col("CHV_NFE").is_not_null() & pl.col("CHV_NFE").str.len_chars().gt(0))
            .then(pl.concat_str([pl.col(p).fill_null("") for p in primary_parts],  separator="|"))
            .otherwise(pl.concat_str([pl.col(p).fill_null("") for p in fallback_parts], separator="|"))
            .alias("ITEM_KEY")
        )
    elif cnpj_col:
        fallback_parts = [c for c in [cnpj_col, "NUM_DOC", "SER", "DT_DOC"] + item_extras if c in df.columns]
        expr = pl.concat_str([pl.col(p).fill_null("") for p in fallback_parts], separator="|").alias("ITEM_KEY")
    else:
        expr = pl.col(cd.JOIN_KEY).alias("ITEM_KEY")

    return df.with_columns([expr])


# ─── Orphan detection ────────────────────────────────────────────────────────

def _identificar_orfaos(cruzado: pl.DataFrame) -> pl.DataFrame:
    """
    Identifies NF items present in only one of the two EFDs.

    Output columns match the ORFAOS template tab (row 11):
      CHAVE_NF, CHV_NFE, COD_PART, NUM_DOC, SER, DT_DOC, VL_DOC,
      OBRIGACAO_FALTANTE
    Fields not available in C170 data are filled with null.
    """
    has_sentinel = "_SRC_FISCAL" in cruzado.columns and "_SRC_CONTRIB" in cruzado.columns

    if has_sentinel:
        fiscal_only_mask  = pl.col("_SRC_FISCAL").is_not_null() & pl.col("_SRC_CONTRIB").is_null()
        contrib_only_mask = pl.col("_SRC_CONTRIB").is_not_null() & pl.col("_SRC_FISCAL").is_null()
    elif "CFOP" in cruzado.columns and "CST_PIS" in cruzado.columns:
        fiscal_only_mask  = pl.col("CFOP").is_not_null()    & pl.col("CST_PIS").is_null()
        contrib_only_mask = pl.col("CST_PIS").is_not_null() & pl.col("CFOP").is_null()
    else:
        return pl.DataFrame()

    def _pick(col: str, alias_: str, dtype=pl.Utf8):
        if col in cruzado.columns:
            return pl.col(col).cast(dtype, strict=False).alias(alias_)
        return pl.lit(None).cast(dtype).alias(alias_)

    def _cpick(col_c: str, col: str, alias_: str, dtype=pl.Utf8):
        if col_c in cruzado.columns:
            return pl.col(col_c).cast(dtype, strict=False).alias(alias_)
        return _pick(col, alias_, dtype)

    # Template columns: CHAVE_NF, CHV_NFE, COD_PART, NUM_DOC, SER, DT_DOC, VL_DOC, OBRIGACAO_FALTANTE
    fiscal_sem_contrib = cruzado.filter(fiscal_only_mask).select([
        pl.col("ITEM_KEY").alias("CHAVE_NF"),
        _pick("CHV_NFE",  "CHV_NFE"),
        _pick("COD_PART", "COD_PART"),
        pl.lit(None).cast(pl.Utf8).alias("NUM_DOC"),
        pl.lit(None).cast(pl.Utf8).alias("SER"),
        pl.lit(None).cast(pl.Utf8).alias("DT_DOC"),
        _pick("VL_ITEM",  "VL_DOC", pl.Float64),
        pl.lit(cd.ORFAO_APENAS_FISCAL).alias(cd.OBRIGACAO_FALTANTE),
    ])

    contrib_sem_fiscal = cruzado.filter(contrib_only_mask).select([
        pl.col("ITEM_KEY").alias("CHAVE_NF"),
        _cpick("CHV_NFE_c",  "CHV_NFE",  "CHV_NFE"),
        _cpick("COD_PART_c", "COD_PART", "COD_PART"),
        pl.lit(None).cast(pl.Utf8).alias("NUM_DOC"),
        pl.lit(None).cast(pl.Utf8).alias("SER"),
        pl.lit(None).cast(pl.Utf8).alias("DT_DOC"),
        pl.lit(None).cast(pl.Float64).alias("VL_DOC"),
        pl.lit(cd.ORFAO_APENAS_CONTRIB).alias(cd.OBRIGACAO_FALTANTE),
    ])

    return pl.concat([fiscal_sem_contrib, contrib_sem_fiscal], how="diagonal")



# ─── Eligibility engine ──────────────────────────────────────────────────────

def _aplicar_elegibilidade(
    df: pl.DataFrame,
    regime: str,
    config: dict,
    aliq_pis_default: float,
    aliq_cofins_default: float,
) -> pl.DataFrame:
    """
    Applies eligibility analysis and calculates credits.
    - Rule 1: Lucro Presumido → non-eligible.
    - Rule 2 (Lucro Real): Classify via LLM (Gemini) based on item description.
    - Rule 3: Calculate PIS/COFINS credits for eligible items.
    """
    # ── Rule 1: Lucro Presumido → nao_elegivel ──
    if regime == cd.REGIME_PRESUMIDO:
        df = df.with_columns([
            pl.lit(cd.ELEG_NAO_ELEGIVEL).alias(cd.ELEGIBILIDADE),
            pl.lit(0.0).alias(cd.VL_CREDITO_PIS),
            pl.lit(0.0).alias(cd.VL_CREDITO_COFINS),
            pl.lit(0.0).alias(cd.VL_CREDITO_TOTAL),
            pl.lit("Regime cumulativo — sem direito a crédito PIS/COFINS").alias(cd.OBSERVACOES),
        ])
        return df

    # ── Rule 2: Lucro Real → LLM Classification ──
    api_key   = config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
    model_name = config.get("gemini_model", "gemini-2.0-flash")
    batch_size = config.get("llm_batch_size", 50)

    # This adds/fills ELEGIBILIDADE and OBSERVACOES
    df = cllm.classificar_itens(
        df, 
        api_key=api_key, 
        model_name=model_name, 
        batch_size=batch_size
    )

    # ── Rule 3: Credit Calculation ──
    # We calculate credits using default rates if the SPED record doesn't provide them,
    # but only for items classified as eligible or for review.
    has_aliq_pis    = "ALIQ_PIS" in df.columns
    has_aliq_cofins = "ALIQ_COFINS" in df.columns
    has_bc_pis      = "VL_BC_PIS" in df.columns
    has_bc_cofins   = "VL_BC_COFINS" in df.columns

    # Effective rates for calculation
    df = df.with_columns([
        pl.when(has_aliq_pis and (pl.col("ALIQ_PIS").is_not_null() & pl.col("ALIQ_PIS").gt(0.0)))
            .then(pl.col("ALIQ_PIS"))
            .otherwise(pl.lit(aliq_pis_default))
            .alias("_ALIQ_PIS_EFF"),
        pl.when(has_aliq_cofins and (pl.col("ALIQ_COFINS").is_not_null() & pl.col("ALIQ_COFINS").gt(0.0)))
            .then(pl.col("ALIQ_COFINS"))
            .otherwise(pl.lit(aliq_cofins_default))
            .alias("_ALIQ_COFINS_EFF"),
    ])

    # Calculate only if not "nao_elegivel"
    is_not_rejected = pl.col(cd.ELEGIBILIDADE).is_in([cd.ELEG_ELEGIVEL, cd.ELEG_REVISAO])
    
    bc_pis    = pl.col("VL_BC_PIS")    if has_bc_pis    else pl.lit(0.0)
    bc_cofins = pl.col("VL_BC_COFINS") if has_bc_cofins else pl.lit(0.0)

    df = df.with_columns([
        pl.when(is_not_rejected)
            .then((bc_pis * pl.col("_ALIQ_PIS_EFF") / 100.0).round(2))
            .otherwise(pl.lit(0.0))
            .alias(cd.VL_CREDITO_PIS),
        pl.when(is_not_rejected)
            .then((bc_cofins * pl.col("_ALIQ_COFINS_EFF") / 100.0).round(2))
            .otherwise(pl.lit(0.0))
            .alias(cd.VL_CREDITO_COFINS),
    ])

    df = df.with_columns(
        (pl.col(cd.VL_CREDITO_PIS) + pl.col(cd.VL_CREDITO_COFINS))
        .round(2)
        .alias(cd.VL_CREDITO_TOTAL)
    )

    return df.drop(["_ALIQ_PIS_EFF", "_ALIQ_COFINS_EFF"])


# ─── Summary builder ─────────────────────────────────────────────────────────

def _build_resumo(
    empresa: str,
    cnpj: str,
    regime: str,
    periodo_ini: str,
    periodo_fim: str,
    total_nfs: int,
    total_cruzados: int,
    detalhes: pl.DataFrame,
    orfaos: pl.DataFrame,
) -> pl.DataFrame:
    """Builds the summary DataFrame for the Resumo tab."""
    n_uc = len(detalhes)
    n_eleg     = len(detalhes.filter(pl.col(cd.ELEGIBILIDADE) == cd.ELEG_ELEGIVEL))
    n_revisao  = len(detalhes.filter(pl.col(cd.ELEGIBILIDADE) == cd.ELEG_REVISAO))
    n_nao_eleg = len(detalhes.filter(pl.col(cd.ELEGIBILIDADE) == cd.ELEG_NAO_ELEGIVEL))
    n_orfaos   = len(orfaos)

    vl_pis = vl_cofins = vl_total = 0.0
    if cd.VL_CREDITO_PIS in detalhes.columns:
        vl_pis = (
            detalhes
            .select(pl.col(cd.VL_CREDITO_PIS).cast(pl.Float64, strict=False).fill_null(0.0).sum())
            .item(0, 0)
        ) or 0.0
    if cd.VL_CREDITO_COFINS in detalhes.columns:
        vl_cofins = (
            detalhes
            .select(pl.col(cd.VL_CREDITO_COFINS).cast(pl.Float64, strict=False).fill_null(0.0).sum())
            .item(0, 0)
        ) or 0.0
    vl_total = round(vl_pis + vl_cofins, 2)

    return pl.DataFrame({
        "EMPRESA":                  [empresa],
        "CNPJ":                     [cnpj],
        "REGIME_TRIBUTARIO":        [regime],
        "PERIODO_INI":              [periodo_ini],
        "PERIODO_FIM":              [periodo_fim],
        "TOTAL_NFS_ANALISADAS":     [total_nfs],
        "TOTAL_ITENS_CRUZADOS":     [total_cruzados],
        "TOTAL_ITENS_USO_CONSUMO":  [n_uc],
        "TOTAL_ELEGIVEL":           [n_eleg],
        "TOTAL_REVISAO":            [n_revisao],
        "TOTAL_NAO_ELEGIVEL":       [n_nao_eleg],
        "TOTAL_ORFAOS":             [n_orfaos],
        "VL_CREDITO_PIS":           [round(vl_pis, 2)],
        "VL_CREDITO_COFINS":        [round(vl_cofins, 2)],
        "VL_CREDITO_TOTAL":         [vl_total],
    })


# ─── Details formatter ───────────────────────────────────────────────────────

def _build_detalhes(df: pl.DataFrame) -> pl.DataFrame:
    """
    Selects and orders the detail columns for the output report, matching the
    template column order at row 11 (23 columns B→X):
      B  ITEM_KEY      — chave do cruzamento (CHV_NFE|COD_ITEM|NUM_ITEM)
      C  CHV_NFE       — chave da NF-e (44 dígitos)
      D  COD_PART      — código do participante (fornecedor)
      E  RAZAO_SOCIAL  — razão social (via 0150)
      F  CNPJ_EMIT     — CNPJ do emitente
      G  NUM_DOC       — número da NF
      H  SER           — série
      I  DT_DOC        — data de emissão
      J  CFOP          — CFOP do item
      K  COD_ITEM      — código do produto/item
      L  DESCR_COMPL   — descrição do item
      M  CST_PIS       — CST PIS (EFD Contribuições)
      N  CST_COFINS    — CST COFINS
      O  ALIQ_PIS      — alíquota PIS (%)
      P  ALIQ_COFINS   — alíquota COFINS (%)
      Q  VL_ITEM       — valor do item
      R  VL_BC_PIS     — base de cálculo PIS
      S  VL_BC_COFINS  — base de cálculo COFINS
      T  ELEGIBILIDADE — resultado da classificação LLM
      U  VL_CREDITO_PIS    — crédito PIS estimado
      V  VL_CREDITO_COFINS — crédito COFINS estimado
      W  VL_CREDITO_TOTAL  — crédito total
      X  OBSERVACOES   — justificativa da classificação LLM

    Missing columns are null-filled so positional alignment is always correct.
    """
    eleg_order = {
        cd.ELEG_ELEGIVEL:     1,
        cd.ELEG_REVISAO:      2,
        cd.ELEG_NAO_ELEGIVEL: 3,
    }

    COLS_ORDERED = [
        ("ITEM_KEY",          pl.Utf8),
        ("CHV_NFE",           pl.Utf8),
        ("COD_PART",          pl.Utf8),
        (cd.RAZAO_SOCIAL,     pl.Utf8),
        ("CNPJ_EMIT",         pl.Utf8),
        ("NUM_DOC",           pl.Utf8),
        ("SER",               pl.Utf8),
        ("DT_DOC",            pl.Utf8),
        (cd.CFOP_UC,          pl.Utf8),
        ("COD_ITEM",          pl.Utf8),   # ← added: column K
        ("DESCR_COMPL",       pl.Utf8),
        (cd.CST_PIS,          pl.Utf8),
        (cd.CST_COFINS,       pl.Utf8),
        (cd.ALIQ_PIS,         pl.Float64),
        (cd.ALIQ_COFINS,      pl.Float64),
        ("VL_ITEM",           pl.Float64),
        (cd.VL_BC_PIS,        pl.Float64),
        (cd.VL_BC_COFINS,     pl.Float64),
        (cd.ELEGIBILIDADE,    pl.Utf8),
        (cd.VL_CREDITO_PIS,   pl.Float64),
        (cd.VL_CREDITO_COFINS,pl.Float64),
        (cd.VL_CREDITO_TOTAL, pl.Float64),
        (cd.OBSERVACOES,      pl.Utf8),
    ]

    exprs = [
        pl.col(col).cast(dtype, strict=False) if col in df.columns
        else pl.lit(None).cast(dtype).alias(col)
        for col, dtype in COLS_ORDERED
    ]
    result = df.select(exprs)

    result = result.with_columns(
        pl.col(cd.ELEGIBILIDADE)
        .replace_strict(eleg_order, return_dtype=pl.Int8, default=9)
        .alias("_ordem")
    ).sort(
        ["_ordem", cd.VL_CREDITO_TOTAL],
        descending=[False, True],
        nulls_last=True,
    ).drop("_ordem")

    return result


# ─── Period extractor ────────────────────────────────────────────────────────

def _extrair_periodo(df_contribuicoes: pl.DataFrame, df_fiscal: pl.DataFrame) -> tuple[str, str]:
    """
    Extracts analysis period from the 0000 record of either EFD.

    The SPED parser renames the start-date field to dfn.PERIODO (='Período').
    The end-date is the immediately following field (not renamed):
      - EFDC (EFD Contribuições): DT_INI = field_5 → DT_FIN = field_6
      - EFDF (EFD ICMS IPI)     : DT_INI = field_3 → DT_FIN = field_4
    """
    ini = fim = "N/D"

    # Map each DataFrame to its end-date field name
    efdc_fin = "field_6"   # EFDC: PERIODO=field_5, DT_FIN=field_6
    efdf_fin = "field_4"   # EFDF: PERIODO=field_3, DT_FIN=field_4

    sources = [
        (df_contribuicoes, efdc_fin),
        (df_fiscal,        efdf_fin),
    ]

    for df, fin_field in sources:
        if df is None or df.is_empty():
            continue
        reg = df.filter(pl.col(dfn.REGISTRO) == "0000")
        if reg.is_empty():
            continue

        # Start date — the renamed PERIODO column
        if dfn.PERIODO in reg.columns:
            v = reg.select(dfn.PERIODO).item(0, 0)
            if v:
                ini = str(v)

        # End date — the raw field_N column (not renamed by the parser)
        if fin_field in reg.columns:
            v = reg.select(fin_field).item(0, 0)
            if v:
                fim = str(v)

        if ini != "N/D" or fim != "N/D":
            break   # Got something — no need to try the other EFD

    return ini, fim


# ─── Main orchestrator ───────────────────────────────────────────────────────

def process_uso_consumo(inbound, df_contribuicoes, df_fiscal, self, projeto, path_env):  # noqa: PLR0914
    """
    Main entry point for the Use & Consumption cross-referencing and credit
    eligibility analysis.
    """
    t0 = time.perf_counter()
    self.logger.info("[U&C] Iniciando processamento de Uso e Consumo.")

    # 1. Config
    config             = _load_config()
    cfop_elegiveis     = config["cfop_elegiveis"]
    aliq_pis_default   = float(config["aliquota_pis_padrao"])
    aliq_cofins_default = float(config["aliquota_cofins_padrao"])
    regime_override    = config.get("regime_tributario", "auto").strip().lower()

    self.logger.info(f"[U&C] Config carregada — CFOPs: {cfop_elegiveis} | Regime override: {regime_override!r}")

    # 2. Remote assets
    df_assets_c = cv.get_remote_assets(dfn.EFDC.get(dfn.OBRIGACAO), path_env)
    df_assets_f = cv.get_remote_assets(dfn.EFDF.get(dfn.OBRIGACAO), path_env)
    versao_c = _get_versao(df_contribuicoes)
    versao_f = _get_versao(df_fiscal)

    self.logger.info(f"[U&C] Versões SPED — EFDC: {versao_c}  EFDF: {versao_f}")

    # 3. Tax regime — auto detection first, then config override fallback
    if regime_override == "real":
        regime = cd.REGIME_REAL
        self.logger.info(f"[U&C] Regime definido via config: {regime!r}")
    elif regime_override == "presumido":
        regime = cd.REGIME_PRESUMIDO
        self.logger.info(f"[U&C] Regime definido via config: {regime!r}")
    else:
        # Auto: read COD_INC_TRIB from EFDC 0000 record
        regime, cod_inc_trib = duc.identificar_regime(df_contribuicoes, df_assets_c, versao_c)
        if regime == cd.REGIME_OUTRO:
            self.logger.warning(
                f"[U&C] COD_INC_TRIB nao identificado (valor={cod_inc_trib!r}). "
                "Definindo como Lucro Real por padrao. "
                "Para forcar o regime, ajuste 'regime_tributario' no uso_consumo_config.json."
            )
            regime = cd.REGIME_REAL  # safe default: allows credit calculation
        else:
            self.logger.info(f"[U&C] Regime identificado via SPED: {regime!r} (COD_INC_TRIB={cod_inc_trib!r})")


    # 4. Extract records from both EFDs
    c100_f = duc.extrair_c100_fiscal(df_fiscal, df_assets_f, versao_f)
    c100_c = duc.extrair_c100_contribuicoes(df_contribuicoes, df_assets_c, versao_c)
    c170_f = duc.extrair_c170_fiscal(df_fiscal, df_assets_f, versao_f)
    c170_c = duc.extrair_c170_contribuicoes(df_contribuicoes, df_assets_c, versao_c)
    participantes = duc.extrair_participantes_uc(
        df_fiscal, df_assets_f, versao_f,
        df_contribuicoes, df_assets_c, versao_c,
    )

    self.logger.info(
        f"[U&C] Registros extraídos — C100_F:{len(c100_f)} C100_C:{len(c100_c)} "
        f"C170_F:{len(c170_f)} C170_C:{len(c170_c)}"
    )

    # 5. c170_f and c170_c already carry CHV_NFE/COD_SIT via forward-fill
    #    (see dados_uso_consumo.extrair_c170_fiscal / extrair_c170_contribuicoes).
    #    No ID_PAI join needed.
    fiscal_items  = c170_f
    contrib_items = c170_c

    if not fiscal_items.is_empty() and cd.COD_SIT in fiscal_items.columns:
        fiscal_items = fiscal_items.filter(pl.col(cd.COD_SIT).is_in(["00", "01"]))
    if not contrib_items.is_empty() and cd.COD_SIT in contrib_items.columns:
        contrib_items = contrib_items.filter(pl.col(cd.COD_SIT).is_in(["00", "01"]))

    chv_col = cd.CHV_NFE if cd.CHV_NFE in fiscal_items.columns else None
    total_nfs_fiscal = (
        fiscal_items.select(chv_col).drop_nulls().unique().height
        if chv_col and not fiscal_items.is_empty()
        else len(c100_f)
    )

    self.logger.info(
        f"[U&C] Itens C170 validos (pos filtro COD_SIT) — Fiscal:{len(fiscal_items)}  Contrib:{len(contrib_items)}"
    )
    self.logger.info(
        f"[U&C] Exemplo CHV_NFE fiscal: "
        f"{fiscal_items.select(cd.CHV_NFE).drop_nulls().head(2).to_series().to_list() if cd.CHV_NFE in fiscal_items.columns and not fiscal_items.is_empty() else 'sem CHV_NFE — forward-fill pode ter falhado'}"
    )


    total_cruzados = 0
    orfaos = pl.DataFrame()
    detalhes_final = pl.DataFrame()

    if fiscal_items.is_empty() and contrib_items.is_empty():
        self.logger.warning("[U&C] Nenhum item C170 encontrado em nenhuma EFD. Verifique os arquivos.")
    else:
        # 8. Build item-level key AFTER the ID_PAI join (so CHV_NFE is already in rows)
        #    ITEM_KEY = CHV_NFE|COD_ITEM|NUM_ITEM  (primary)
        #             = CNPJ|NUM_DOC|SER|DT_DOC|COD_ITEM|NUM_ITEM (fallback)
        if not fiscal_items.is_empty():
            fiscal_items  = _build_item_key(fiscal_items)
        if not contrib_items.is_empty():
            contrib_items = _build_item_key(contrib_items)

        self.logger.info(
            f"[U&C] ITEM_KEY exemplo fiscal: "
            f"{fiscal_items.select('ITEM_KEY').head(2).to_series().to_list() if not fiscal_items.is_empty() and 'ITEM_KEY' in fiscal_items.columns else 'N/A'}"
        )

        # Cross-EFD join on ITEM_KEY.
        # Add sentinel columns BEFORE the join so orphan detection works with
        # coalesce=True (which merges both sides' ITEM_KEY into one column,
        # preventing us from using ITEM_KEY_c to distinguish orphans).
        if not fiscal_items.is_empty():
            fiscal_items  = fiscal_items.with_columns(pl.lit(True).alias("_SRC_FISCAL"))
        if not contrib_items.is_empty():
            contrib_items = contrib_items.with_columns(pl.lit(True).alias("_SRC_CONTRIB"))

        if not fiscal_items.is_empty() and not contrib_items.is_empty():
            cruzado = fiscal_items.join(
                contrib_items,
                left_on="ITEM_KEY",
                right_on="ITEM_KEY",
                how="full",
                suffix="_c",
                coalesce=True,
            )
        elif not fiscal_items.is_empty():
            cruzado = fiscal_items.with_columns(pl.lit(None).cast(pl.Boolean).alias("_SRC_CONTRIB"))
        else:
            cruzado = contrib_items.with_columns(pl.lit(None).cast(pl.Boolean).alias("_SRC_FISCAL"))

        total_cruzados = len(cruzado)
        self.logger.info(f"[U&C] Total de pares cruzados (antes do filtro CFOP): {total_cruzados}")

        # 9. Orphan detection
        orfaos = _identificar_orfaos(cruzado)
        self.logger.info(f"[U&C] Órfãos identificados: {len(orfaos)}")

        # 10. Keep only matched items (present in both EFDs)
        # With coalesce=True, ITEM_KEY is merged. Use sentinels to distinguish.
        matched_mask = (
            pl.col("_SRC_FISCAL").is_not_null() & pl.col("_SRC_CONTRIB").is_not_null()
            if "_SRC_FISCAL" in cruzado.columns and "_SRC_CONTRIB" in cruzado.columns
            else pl.col("ITEM_KEY").is_not_null()
        )

        uc_items = cruzado.filter(matched_mask)

        # 11. Filter by CFOP (use & consumption CFOPs from config)
        if "CFOP" in uc_items.columns and uc_items.height > 0:
            uc_items = uc_items.with_columns(
                pl.col("CFOP").cast(pl.Int64, strict=False).alias("_CFOP_INT")
            ).filter(
                pl.col("_CFOP_INT").is_in(cfop_elegiveis)
            ).drop("_CFOP_INT")

        self.logger.info(f"[U&C] Itens após filtro CFOP: {len(uc_items)}")

        # 12. Eligibility analysis
        if uc_items.height > 0:
            uc_items = _aplicar_elegibilidade(
                uc_items, regime, config, aliq_pis_default, aliq_cofins_default
            )

            # 13. Enrich with razão social from 0150
            if not participantes.is_empty() and "COD_PART" in uc_items.columns:
                uc_items = uc_items.join(participantes, on="COD_PART", how="left")

            # 14. Add regime column for traceability
            uc_items = uc_items.with_columns(pl.lit(regime).alias(cd.REGIME))

            detalhes_final = _build_detalhes(uc_items)
        else:
            self.logger.info("[U&C] Nenhum item de uso e consumo encontrado após filtro de CFOP.")

    elapsed_extract = time.perf_counter() - t0
    self.logger.info(f"[U&C] Extração e análise concluídas em {elapsed_extract:.2f}s.")

    # 15. Company info and period
    empresa, cnpj = em.empresa_cnpj(inbound, df_fiscal, df_contribuicoes)
    periodo_ini, periodo_fim = _extrair_periodo(df_contribuicoes, df_fiscal)

    # 16. Build summary
    resumo = _build_resumo(
        empresa=empresa,
        cnpj=cnpj,
        regime=regime,
        periodo_ini=periodo_ini,
        periodo_fim=periodo_fim,
        total_nfs=total_nfs_fiscal,
        total_cruzados=total_cruzados,
        detalhes=detalhes_final if not detalhes_final.is_empty() else pl.DataFrame({cd.ELEGIBILIDADE: [], cd.VL_CREDITO_PIS: [], cd.VL_CREDITO_COFINS: []}),
        orfaos=orfaos,
    )

    # Log summary
    if detalhes_final.height > 0 and cd.ELEGIBILIDADE in detalhes_final.columns:
        n_el = len(detalhes_final.filter(pl.col(cd.ELEGIBILIDADE) == cd.ELEG_ELEGIVEL))
        n_rv = len(detalhes_final.filter(pl.col(cd.ELEGIBILIDADE) == cd.ELEG_REVISAO))
        n_ne = len(detalhes_final.filter(pl.col(cd.ELEGIBILIDADE) == cd.ELEG_NAO_ELEGIVEL))
        vl = resumo.select("VL_CREDITO_TOTAL").item(0, 0) or 0.0
        self.logger.info(
            f"[U&C] Elegível:{n_el}  Revisão:{n_rv}  Não elegível:{n_ne}  "
            f"Crédito total estimado: R$ {vl:,.2f}"
        )

    # 17. Write Excel
    we.excel_uso_consumo(self, empresa, cnpj, regime, periodo_ini, periodo_fim,
                         resumo, detalhes_final, orfaos, projeto)

    elapsed_total = time.perf_counter() - t0
    self.logger.info(f"[U&C] Processamento concluído em {elapsed_total:.2f}s.")
