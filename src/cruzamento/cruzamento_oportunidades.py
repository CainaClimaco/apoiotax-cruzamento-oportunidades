"""
cruzamento_oportunidades.py
────────────────────────────
Oportunidades — Base completa de cruzamento SPED Fiscal x EFD Contribuicoes.

Orquestra a extracao de todos os blocos SPED, aplica LEFT JOINs (EFD_F como
verdade), e enriquece os resultados com dados cadastrais (0150, 0200, 0500),
descricoes de CFOP e de CST PIS/COFINS.

Retorna um dict de DataFrames por chave de registro, pronto para excel_oportunidades().
"""

import json
import polars as pl
import datatricks.sped.sped_definitions as dfn
import cruzamento.cruzamento_definition as cd
import cruzamento.dados_oportunidades as dop
import cruzamento.dados_bloco_d as dbd


def _reorder_c170(df: pl.DataFrame) -> pl.DataFrame:
    """Ordem exata de colunas para a aba C170 conforme estrutura definida."""
    if df.is_empty():
        return df
    template = [
        # bloco identidade (datatricks)
        dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI,
        # cabeçalho documento EFD_F
        cd.CHV_NFE, "NUM_DOC", "DT_DOC",
        cd.COD_PART, cd.RAZAO_SOCIAL, "CNPJ_EMIT",
        # item EFD_F
        "COD_ITEM",
        cd.DESCR_ITEM, cd.UNID_INV, cd.TIPO_ITEM, cd.COD_NCM,
        "VL_ITEM", "CFOP", cd.DESCR_CFOP,
        "CST_ICMS", cd.DESCR_CST_ICMS, "ALIQ_ICMS", "VL_ICMS",
        cd.COD_SIT,
        # chave de cruzamento
        "ITEM_KEY",
        cd.EM_EFD_C,
        # espelho EFD_C
        f"{dfn.ID_SPED}_c", f"{dfn.ID_PAI}_c",
        "CHV_NFE_c", "NUM_DOC_c", "DT_DOC_c",
        "COD_PART_c", "COD_ITEM_c",
        # PIS (EFD_C)
        "CST_PIS", cd.DESCR_CST_PIS, "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        # COFINS (EFD_C)
        "CST_COFINS", cd.DESCR_CST_COFINS, "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
    ]
    _EXCLUDE = {"DESCR_COMPL"}
    existing = set(df.columns)
    ordered = [c for c in template if c in existing]
    placed = set(ordered) | _EXCLUDE
    for col in df.columns:
        if col not in placed:
            ordered.append(col)
    return df.select(ordered)


def _reorder_d190(df: pl.DataFrame) -> pl.DataFrame:
    """Ordem exata de colunas para a aba D190 conforme estrutura definida."""
    if df.is_empty():
        return df
    template = [
        # bloco identidade (datatricks)
        dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI,
        # cabeçalho documento EFD_F
        "CHV_CTE", "DT_DOC",
        cd.COD_PART, cd.RAZAO_SOCIAL, "CNPJ_EMIT",
        cd.COD_SIT,
        # item EFD_F
        "CFOP", cd.DESCR_CFOP,
        "CST_ICMS", cd.DESCR_CST_ICMS, "ALIQ_ICMS", "VL_BC_ICMS", "VL_ICMS",
        # chave de cruzamento
        "ITEM_KEY",
        cd.EM_EFD_C,
        # espelho EFD_C
        f"{dfn.ID_SPED}_c", f"{dfn.ID_PAI}_c",
        "DT_DOC_c", "COD_PART_c",
        # PIS (EFD_C)
        "CST_PIS", cd.DESCR_CST_PIS, "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        # COFINS (EFD_C)
        "CST_COFINS", cd.DESCR_CST_COFINS, "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
    ]
    existing = set(df.columns)
    ordered = [c for c in template if c in existing]
    placed = set(ordered)
    for col in df.columns:
        if col not in placed:
            ordered.append(col)
    return df.select(ordered)


# ── Loaders de lookup ──────────────────────────────────────────────────────────

def _carregar_cfop() -> pl.DataFrame:
    """Carrega CFOP.xlsx; retorna DataFrame com CFOP (Utf8) e coluna de descricao."""
    try:
        df = pl.read_excel(cd.CAMINHO_CFOP, engine="openpyxl")
        if "CFOP" in df.columns:
            df = df.with_columns(pl.col("CFOP").cast(pl.Utf8))
        return df
    except Exception:
        return pl.DataFrame()


def _carregar_cst() -> pl.DataFrame:
    """Carrega CST_PIS_COFINS.json; retorna DataFrame com colunas CST e DESCR_CST."""
    try:
        with open(cd.CAMINHO_CST_PIS_COFINS, encoding="utf-8") as fh:
            mapping = json.load(fh)
        return pl.DataFrame({"CST": list(mapping.keys()), "DESCR_CST": list(mapping.values())})
    except Exception:
        return pl.DataFrame()


def _carregar_cst_icms() -> pl.DataFrame:
    """Carrega CST_ICMS.json (chaves de 2 dígitos) para enriquecimento de DESCR_CST_ICMS."""
    try:
        with open(cd.CAMINHO_CST_ICMS, encoding="utf-8") as fh:
            mapping = json.load(fh)
        return pl.DataFrame({"CST": list(mapping.keys()), "DESCR_CST": list(mapping.values())})
    except Exception:
        return pl.DataFrame()


# ── Enriquecimento ─────────────────────────────────────────────────────────────

def _enriquecer_participantes(df: pl.DataFrame, participantes: pl.DataFrame) -> pl.DataFrame:
    if participantes.is_empty() or "COD_PART" not in df.columns:
        return df
    join_keys = [k for k in [dfn.ID_SPED, "COD_PART"] if k in df.columns and k in participantes.columns]
    to_drop = [c for c in [cd.RAZAO_SOCIAL, "CNPJ_EMIT"] if c in df.columns]
    if to_drop:
        df = df.drop(to_drop)
    return df.join(participantes, on=join_keys or ["COD_PART"], how="left")


def _enriquecer_0200(df: pl.DataFrame, itens_0200: pl.DataFrame) -> pl.DataFrame:
    if itens_0200.is_empty() or "COD_ITEM" not in df.columns:
        return df
    join_keys = [k for k in [dfn.ID_SPED, "COD_ITEM"] if k in df.columns and k in itens_0200.columns]
    to_drop = [c for c in ["DESCR_ITEM", "UNID_INV", "TIPO_ITEM", "COD_NCM"] if c in df.columns]
    if to_drop:
        df = df.drop(to_drop)
    return df.join(itens_0200, on=join_keys or ["COD_ITEM"], how="left")



def _enriquecer_cfop(df: pl.DataFrame, cfop_df: pl.DataFrame) -> pl.DataFrame:
    """Adiciona DESCR_CFOP. Join em CFOP (Utf8)."""
    if cfop_df.is_empty() or "CFOP" not in df.columns:
        return df
    df = df.with_columns(pl.col("CFOP").cast(pl.Utf8))
    # localiza coluna de descricao no DataFrame de CFOP
    descr_col = next((c for c in cfop_df.columns if c != "CFOP"), None)
    if descr_col is None:
        return df
    join_df = cfop_df.select(["CFOP", descr_col]).rename({descr_col: cd.DESCR_CFOP})
    if cd.DESCR_CFOP in df.columns:
        df = df.drop(cd.DESCR_CFOP)
    return df.join(join_df, on="CFOP", how="left")


def _enriquecer_cst_icms(df: pl.DataFrame, cst_icms_df: pl.DataFrame) -> pl.DataFrame:
    """Adiciona DESCR_CST_ICMS via lookup nos 2 dígitos finais do CST_ICMS (formato XXX)."""
    if cst_icms_df.is_empty() or "CST_ICMS" not in df.columns:
        return df
    if cd.DESCR_CST_ICMS in df.columns:
        df = df.drop(cd.DESCR_CST_ICMS)
    tmp = df.with_columns(
        pl.col("CST_ICMS").str.slice(-2).alias("_CST_BASE")
    )
    tmp = tmp.join(
        cst_icms_df.rename({"DESCR_CST": cd.DESCR_CST_ICMS}),
        left_on="_CST_BASE", right_on="CST", how="left",
    )
    return tmp.drop("_CST_BASE")


def _enriquecer_cst(df: pl.DataFrame, cst_df: pl.DataFrame) -> pl.DataFrame:
    """Adiciona DESCR_CST_PIS e DESCR_CST_COFINS a partir do JSON de CST."""
    if cst_df.is_empty():
        return df
    if "CST_PIS" in df.columns:
        if cd.DESCR_CST_PIS in df.columns:
            df = df.drop(cd.DESCR_CST_PIS)
        df = df.join(
            cst_df.rename({"DESCR_CST": cd.DESCR_CST_PIS}),
            left_on="CST_PIS", right_on="CST", how="left",
        )
    if "CST_COFINS" in df.columns:
        if cd.DESCR_CST_COFINS in df.columns:
            df = df.drop(cd.DESCR_CST_COFINS)
        df = df.join(
            cst_df.rename({"DESCR_CST": cd.DESCR_CST_COFINS}),
            left_on="CST_COFINS", right_on="CST", how="left",
        )
    return df


# ── Construtor de chave de item ────────────────────────────────────────────────

_C170_F_SUM = ["VL_ITEM", "VL_ICMS"]
_C170_C_SUM = ["VL_BC_PIS", "VL_PIS", "VL_BC_COFINS", "VL_COFINS"]


def _build_item_key(df: pl.DataFrame) -> pl.DataFrame:
    """
    Constroi ITEM_KEY para cruzamento C170 (pos-consolidacao).

    Primaria : CHV_NFE|COD_ITEM
    Fallback : NUM_DOC|SER|DT_DOC|COD_ITEM
    """
    has_chv  = "CHV_NFE" in df.columns
    has_item = "COD_ITEM" in df.columns

    if has_chv and has_item:
        primary_parts  = ["CHV_NFE", "COD_ITEM"]
        fallback_parts = [c for c in ["NUM_DOC", "SER", "DT_DOC", "COD_ITEM"] if c in df.columns]
        expr = (
            pl.when(pl.col("CHV_NFE").is_not_null() & pl.col("CHV_NFE").str.len_chars().gt(0))
            .then(pl.concat_str([pl.col(p).fill_null("") for p in primary_parts], separator="|"))
            .otherwise(pl.concat_str([pl.col(p).fill_null("") for p in fallback_parts], separator="|"))
            .alias("ITEM_KEY")
        )
    elif has_item:
        parts = [c for c in ["NUM_DOC", "SER", "DT_DOC", "COD_ITEM"] if c in df.columns]
        expr  = pl.concat_str([pl.col(p).fill_null("") for p in parts], separator="|").alias("ITEM_KEY")
    elif has_chv:
        expr = pl.col("CHV_NFE").alias("ITEM_KEY")
    else:
        expr = pl.lit(None).cast(pl.Utf8).alias("ITEM_KEY")

    return df.with_columns(expr)


def _consolidar_c170(df: pl.DataFrame, sum_cols: list[str]) -> pl.DataFrame:
    """
    Consolida C170 por PERIODO + CNPJ + CHV_NFE + COD_ITEM (quando disponiveis),
    somando colunas monetarias e mantendo o primeiro valor das demais.
    Remove NUM_ITEM antes do agrupamento.
    """
    if df.is_empty():
        return df
    df = df.drop([c for c in ["NUM_ITEM"] if c in df.columns])
    key    = [c for c in [dfn.PERIODO, dfn.CNPJ, "CHV_NFE", "COD_ITEM"] if c in df.columns]
    if not key:
        return df
    sums   = [c for c in sum_cols if c in df.columns]
    firsts = [c for c in df.columns if c not in key and c not in sums]
    return (
        df.group_by(key)
          .agg([pl.col(c).sum() for c in sums] + [pl.col(c).first() for c in firsts])
          .sort(key)
    )


# ── Cruzamentos transacionais ──────────────────────────────────────────────────

def _cruzar_c170(c170_f: pl.DataFrame, c170_c: pl.DataFrame) -> pl.DataFrame:
    """EFD_F LEFT JOIN EFD_C em ITEM_KEY. Adiciona flag EM_EFD_C."""
    if c170_f.is_empty():
        return pl.DataFrame()

    # Colunas do lado C que devem existir sempre para manter o template C170
    _C170_C_SIDE = [
        (f"{dfn.ID_SPED}_c", pl.Utf8),
        (f"{dfn.ID_PAI}_c",  pl.Utf8),
        ("CHV_NFE_c",        pl.Utf8),
        ("NUM_DOC_c",        pl.Utf8),
        ("DT_DOC_c",         pl.Utf8),
        ("COD_PART_c",       pl.Utf8),
        ("COD_ITEM_c",       pl.Utf8),
        ("CST_PIS",          pl.Utf8),
        ("VL_BC_PIS",        pl.Float64),
        ("ALIQ_PIS",         pl.Float64),
        ("VL_PIS",           pl.Float64),
        ("CST_COFINS",       pl.Utf8),
        ("VL_BC_COFINS",     pl.Float64),
        ("ALIQ_COFINS",      pl.Float64),
        ("VL_COFINS",        pl.Float64),
    ]

    f = _build_item_key(c170_f).with_columns(pl.lit(True).alias("_SRC_F"))

    if not c170_c.is_empty():
        c = _build_item_key(c170_c).with_columns(pl.lit(True).alias("_SRC_C"))
        cruzado = f.join(c, on="ITEM_KEY", how="left", suffix="_c", coalesce=True)
        missing = [
            pl.lit(None).cast(dtype).alias(col)
            for col, dtype in _C170_C_SIDE
            if col not in cruzado.columns
        ]
        if missing:
            cruzado = cruzado.with_columns(missing)
    else:
        null_cols = [
            pl.lit(None).cast(dtype).alias(col)
            for col, dtype in _C170_C_SIDE
            if col not in c170_f.columns
        ]
        cruzado = f.with_columns(
            [pl.lit(None).cast(pl.Boolean).alias("_SRC_C")] + null_cols
        )

    return (
        cruzado
        .with_columns(
            pl.when(pl.col("_SRC_C").is_not_null())
            .then(pl.lit("Encontrado"))
            .otherwise(pl.lit("Nao encontrado"))
            .alias(cd.EM_EFD_C)
        )
        .drop(["_SRC_F", "_SRC_C"], strict=False)
    )


def _cruzar_d190(d190_f: pl.DataFrame, d101_c: pl.DataFrame) -> pl.DataFrame:
    """D190_F LEFT JOIN D101_C em CHV_CTE + CFOP. Adiciona ITEM_KEY e flag EM_EFD_C."""
    if d190_f.is_empty():
        return pl.DataFrame()

    join_cols = [
        c for c in ["CHV_CTE", "CFOP"]
        if c in d190_f.columns and (d101_c.is_empty() or c in d101_c.columns)
    ]

    # Colunas do lado C que devem existir sempre (mesmo sem D101) para manter o template D190
    _C_SIDE_COLS = [
        (f"{dfn.ID_SPED}_c", pl.Utf8),
        (f"{dfn.ID_PAI}_c",  pl.Utf8),
        ("DT_DOC_c",         pl.Utf8),
        ("COD_PART_c",       pl.Utf8),
        ("CST_PIS",          pl.Utf8),
        ("VL_BC_PIS",        pl.Float64),
        ("ALIQ_PIS",         pl.Float64),
        ("VL_PIS",           pl.Float64),
        ("CST_COFINS",       pl.Utf8),
        ("VL_BC_COFINS",     pl.Float64),
        ("ALIQ_COFINS",      pl.Float64),
        ("VL_COFINS",        pl.Float64),
    ]

    if not d101_c.is_empty() and join_cols:
        f = d190_f.with_columns(pl.lit(True).alias("_SRC_F"))
        c = d101_c.with_columns(pl.lit(True).alias("_SRC_C"))
        cruzado = f.join(c, on=join_cols, how="left", suffix="_c", coalesce=True)
        # Garante que colunas ausentes (ex: não mapeadas no assets) existam como null
        missing = [
            pl.lit(None).cast(dtype).alias(col)
            for col, dtype in _C_SIDE_COLS
            if col not in cruzado.columns
        ]
        if missing:
            cruzado = cruzado.with_columns(missing)
    else:
        null_cols = [
            pl.lit(None).cast(dtype).alias(col)
            for col, dtype in _C_SIDE_COLS
            if col not in d190_f.columns
        ]
        cruzado = d190_f.with_columns(
            [pl.lit(True).alias("_SRC_F"),
             pl.lit(None).cast(pl.Boolean).alias("_SRC_C")]
            + null_cols
        )

    item_parts = [c for c in ["CHV_CTE", "CFOP"] if c in cruzado.columns]
    item_key_expr = (
        pl.concat_str([pl.col(c).fill_null("") for c in item_parts], separator="|")
        if item_parts
        else pl.lit(None).cast(pl.Utf8)
    ).alias("ITEM_KEY")

    return (
        cruzado
        .with_columns(
            item_key_expr,
            pl.when(pl.col("_SRC_C").is_not_null())
            .then(pl.lit("Encontrado"))
            .otherwise(pl.lit("Nao encontrado"))
            .alias(cd.EM_EFD_C),
        )
        .drop(["_SRC_F", "_SRC_C"], strict=False)
    )


# ── Orquestrador principal ─────────────────────────────────────────────────────

def executar_oportunidades(
    df_fiscal: pl.DataFrame,
    df_assets_f: pl.DataFrame,
    versao_f: str | None,
    df_contribuicoes: pl.DataFrame,
    df_assets_c: pl.DataFrame,
    versao_c: str | None,
) -> dict[str, pl.DataFrame]:
    """
    Oportunidades: extrai C170 e D190, cruza EFD_F LEFT JOIN EFD_C e enriquece com cadastros.

    Retorna dict com chaves "C170" e "D190".
    Passe o dict retornado para write_excel.excel_oportunidades().
    """
    resultado: dict[str, pl.DataFrame] = {}

    # ── Lookups ───────────────────────────────────────────────────────────────
    cfop_df     = _carregar_cfop()
    cst_df      = _carregar_cst()
    cst_icms_df = _carregar_cst_icms()

    # ── Dados cadastrais ──────────────────────────────────────────────────────
    participantes = dop.extrair_participantes_uc(
        df_fiscal, df_assets_f, versao_f,
        df_contribuicoes, df_assets_c, versao_c,
    )
    itens_0200 = dop.extrair_0200_fiscal(df_fiscal, df_assets_f, versao_f)

    # ── C170: itens NF-e — EFD_F LEFT JOIN EFD_C ──────────────────────────────
    c170_f = dop.extrair_c170_fiscal(df_fiscal, df_assets_f, versao_f)
    c170_c = dop.extrair_c170_contribuicoes(df_contribuicoes, df_assets_c, versao_c)
    c170_f = _consolidar_c170(c170_f, _C170_F_SUM)
    c170_c = _consolidar_c170(c170_c, _C170_C_SUM)
    df_c170 = _cruzar_c170(c170_f, c170_c)
    if not df_c170.is_empty():
        df_c170 = _enriquecer_participantes(df_c170, participantes)
        df_c170 = _enriquecer_0200(df_c170, itens_0200)
        df_c170 = _enriquecer_cfop(df_c170, cfop_df)
        df_c170 = _enriquecer_cst_icms(df_c170, cst_icms_df)
        df_c170 = _enriquecer_cst(df_c170, cst_df)
    resultado["C170"] = _reorder_c170(df_c170)

    # ── D190: CT-e — EFD_F LEFT JOIN D101_C ───────────────────────────────────
    d190_f = dbd.extrair_d190_fiscal(df_fiscal, df_assets_f, versao_f)
    d101_c = dbd.extrair_d101_contribuicoes(df_contribuicoes, df_assets_c, versao_c)
    df_d190 = _cruzar_d190(d190_f, d101_c)
    if not df_d190.is_empty():
        df_d190 = _enriquecer_participantes(df_d190, participantes)
        df_d190 = _enriquecer_cfop(df_d190, cfop_df)
        df_d190 = _enriquecer_cst_icms(df_d190, cst_icms_df)
        df_d190 = _enriquecer_cst(df_d190, cst_df)
    resultado["D190"] = _reorder_d190(df_d190)

    return resultado
