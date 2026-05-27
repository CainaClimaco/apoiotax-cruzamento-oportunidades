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
from concurrent.futures import ThreadPoolExecutor
import datatricks.sped.sped_definitions as dfn
import cruzamento.cruzamento_definition as cd
import cruzamento.dados_oportunidades as dop
import cruzamento.dados_bloco_d as dbd
import cruzamento.dados_bloco_a as dba
import cruzamento.dados_bloco_f as dbf

_CFOP_USO_CONSUMO = {"1556", "2556", "1407", "2407"}
_CFOP_INSUMOS = {"1101", "2101"}
_CFOP_REVENDA = {"1102", "2102"}
_CFOP_ATIVO_IMOB = {"1551", "2551", "1406", "2406"}


def _reorder_c170(df: pl.DataFrame) -> pl.DataFrame:
    """Ordem exata de colunas para a aba C170 conforme estrutura definida."""
    if df.is_empty():
        return df
    template = [
        # bloco identidade (datatricks)
        dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI,
        # cabeçalho documento EFD_F
        cd.CHV_NFE, "NUM_DOC", "DT_DOC",
        cd.IND_OPER,                    # entrada (0) / saída (1) — do C100 EFD Fiscal
        cd.COD_PART, cd.RAZAO_SOCIAL, "CNPJ_EMIT", cd.UF_EMIT,
        cd.CNAE_PRINCIPAL, cd.ATIVIDADE_PRINCIPAL,
        cd.CNAE_SECUNDARIA, cd.ATIVIDADE_SECUNDARIA,
        cd.OPCAO_SIMPLES,
        # item EFD_F
        "COD_ITEM",
        cd.DESCR_ITEM, cd.UNID_INV, cd.TIPO_ITEM, cd.COD_NCM,
        "VL_ITEM", "CFOP", cd.DESCR_CFOP,
        "CST_ICMS", cd.DESCR_CST_ICMS, "ALIQ_ICMS", "VL_ICMS",
        cd.COD_SIT,
        "COD_CTA", cd.NOME_CTA,
        # chave de cruzamento
        "ITEM_KEY",
        cd.EM_EFD_C,
        # espelho EFD_C
        f"{dfn.ID_SPED}_c", f"{dfn.ID_PAI}_c",
        "CHV_NFE_c", "NUM_DOC_c", "DT_DOC_c",
        f"{cd.IND_OPER}_c",             # entrada (0) / saída (1) — do C100 EFD Contribuições
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
        "CHV_CTE", "DT_DOC", "VL_DOC",
        cd.COD_PART, cd.RAZAO_SOCIAL, "CNPJ_EMIT", cd.UF_EMIT,
        cd.CNAE_PRINCIPAL, cd.ATIVIDADE_PRINCIPAL,
        cd.CNAE_SECUNDARIA, cd.ATIVIDADE_SECUNDARIA,
        cd.OPCAO_SIMPLES,
        cd.COD_SIT,
        "COD_CTA", cd.NOME_CTA,
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


def _reorder_a170(df: pl.DataFrame) -> pl.DataFrame:
    """Ordem exata de colunas para a aba A170 conforme estrutura definida."""
    template = [
        # bloco identidade (datatricks)
        "Período", "Registro", "Quebra CNPJ", "ID-SPED", "ID-PAI", "ID-REG",
        # campos A100 (documento)
        "REG", "IND_MOV", "REG2", "CNPJ", "REG3",
        "IND_OPER", "IND_EMIT", cd.COD_PART, cd.RAZAO_SOCIAL, "CNPJ_EMIT", cd.UF_EMIT,
        cd.CNAE_PRINCIPAL, cd.ATIVIDADE_PRINCIPAL,
        cd.CNAE_SECUNDARIA, cd.ATIVIDADE_SECUNDARIA,
        cd.OPCAO_SIMPLES,
        cd.COD_SIT, "SER", "SUB", "NUM_DOC", "CHV_NFSE",
        "DT_DOC", "DT_EXE_SERV", "VL_DOC", "IND_PGTO", "VL_DESC",
        "VL_BC_PIS", "VL_PIS", "VL_BC_COFINS", "VL_COFINS",
        "VL_PIS_RET", "VL_COFINS_RET", "VL_ISS",
        # campos A170 (item)
        "REG4", "NUM_ITEM", "COD_ITEM", "DESCR_COMPL", "VL_ITEM", "VL_DESC2",
        "NAT_BC_CRED", "IND_ORIG_CRED",
        "CST_PIS", cd.DESCR_CST_PIS, "VL_BC_PIS2", "ALIQ_PIS", "VL_PIS2",
        "CST_COFINS", cd.DESCR_CST_COFINS, "VL_BC_COFINS2", "ALIQ_COFINS", "VL_COFINS2",
        "COD_CTA", cd.NOME_CTA, "COD_CCUS",
    ]
    if df.is_empty():
        return pl.DataFrame({col: pl.Series([], dtype=pl.Utf8) for col in template})
    existing = set(df.columns)
    ordered = [c for c in template if c in existing]
    placed = set(ordered)
    for col in df.columns:
        if col not in placed:
            ordered.append(col)
    return df.select(ordered)


def _reorder_f100(df: pl.DataFrame) -> pl.DataFrame:
    """Ordem exata de colunas para a aba F100 conforme estrutura definida."""
    template = [
        # bloco identidade (datatricks)
        "Período", "Registro", "Quebra CNPJ", "ID-SPED", "ID-PAI", "ID-REG",
        # campos F100
        "REG", "IND_MOV", "REG2", "CNPJ", "REG3",
        "IND_OPER", cd.COD_PART, cd.RAZAO_SOCIAL, "CNPJ_EMIT", cd.UF_EMIT,
        "COD_ITEM", "DT_OPER", "VL_OPER",
        "CST_PIS", cd.DESCR_CST_PIS, "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        "CST_COFINS", cd.DESCR_CST_COFINS, "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
        "NAT_BC_CRED", "IND_ORIG_CRED",
        "COD_CTA", cd.NOME_CTA, "COD_CCUS", "DESC_DOC_OPER",
    ]
    if df.is_empty():
        return pl.DataFrame({col: pl.Series([], dtype=pl.Utf8) for col in template})
    existing = set(df.columns)
    ordered = [c for c in template if c in existing]
    placed = set(ordered)
    for col in df.columns:
        if col not in placed:
            ordered.append(col)
    return df.select(ordered)


def _resumo_c190(df: pl.DataFrame) -> dict:
    """
    Agrupa C190 por CFOP (+DESCR_CFOP se disponível), soma VL_OPR/VL_BC_ICMS/VL_ICMS,
    divide em Entradas (IND_OPER=0) e Saídas (IND_OPER=1).
    Retorna dict {"ent": df_entrada, "sai": df_saida}; nunca retorna DataFrames vazios
    (usa skeleton com linha TOTAL zerada quando sem dados).
    """
    def _skeleton_side() -> pl.DataFrame:
        return pl.DataFrame({
            "CFOP":        pl.Series([" TOTAL"], dtype=pl.Utf8),
            cd.DESCR_CFOP: pl.Series([None],    dtype=pl.Utf8),
            "VL_OPR":      pl.Series([0.0],     dtype=pl.Float64),
            "VL_BC_ICMS":  pl.Series([0.0],     dtype=pl.Float64),
            "VL_ICMS":     pl.Series([0.0],     dtype=pl.Float64),
        })
    _EMPTY = {"ent": _skeleton_side(), "sai": _skeleton_side()}

    if df.is_empty() or "CFOP" not in df.columns or "VL_OPR" not in df.columns:
        return _EMPTY
    if cd.IND_OPER not in df.columns:
        return _EMPTY

    df = df.with_columns(pl.col("CFOP").cast(pl.Utf8))
    grupo_cols = ["CFOP"] + ([cd.DESCR_CFOP] if cd.DESCR_CFOP in df.columns else [])
    sum_cols   = [c for c in ["VL_OPR", "VL_BC_ICMS", "VL_ICMS"] if c in df.columns]

    def _lado(ind_oper_val):
        lado = df.filter(pl.col(cd.IND_OPER).cast(pl.Utf8) == ind_oper_val)
        if lado.is_empty():
            return _skeleton_side()
        agrupado = (
            lado.group_by(grupo_cols)
                .agg([pl.col(c).sum() for c in sum_cols])
                .sort("VL_OPR", descending=True)
        )
        total_row = {
            col: ([" TOTAL"] if col in grupo_cols else [agrupado[col].sum()])
            for col in agrupado.columns
        }
        return pl.concat([agrupado, pl.DataFrame(total_row, schema=agrupado.schema)])

    return {"ent": _lado("0"), "sai": _lado("1")}


def _resumo_c170_produtos(df: pl.DataFrame) -> dict:
    """
    Agrupa C170 por DESCR_COMPL (fallback DESCR_ITEM), soma VL_ITEM e calcula
    PERC, dividindo em Entradas (IND_OPER=0) e Saídas (IND_OPER=1).
    Não filtra por EM_EFD_C — cobre todos os itens do C170.
    Retorna dict {"ent": df_entrada, "sai": df_saida}; nunca retorna DataFrames vazios.
    """
    descr_col = (
        "DESCR_COMPL" if (df.is_empty() or "DESCR_COMPL" in df.columns)
        else ("DESCR_ITEM" if "DESCR_ITEM" in df.columns else "DESCR_COMPL")
    )

    def _skeleton_side() -> pl.DataFrame:
        return pl.DataFrame({
            descr_col:  pl.Series([" TOTAL"], dtype=pl.Utf8),
            "VL_ITEM":  pl.Series([0.0],     dtype=pl.Float64),
            "PERC":     pl.Series([0.0],     dtype=pl.Float64),
        })
    _EMPTY = {"ent": _skeleton_side(), "sai": _skeleton_side()}

    if df.is_empty() or "VL_ITEM" not in df.columns or cd.IND_OPER not in df.columns:
        return _EMPTY
    if descr_col not in df.columns:
        return _EMPTY

    df = df.filter(
        pl.col(descr_col).is_not_null()
        & (pl.col(descr_col).str.strip_chars() != "")
    )

    def _lado(ind_oper_val):
        lado = df.filter(pl.col(cd.IND_OPER).cast(pl.Utf8) == ind_oper_val)
        if lado.is_empty():
            return _skeleton_side()
        agrupado = (
            lado.group_by(descr_col)
                .agg(pl.col("VL_ITEM").sum())
                .sort("VL_ITEM", descending=True)
        )
        total = agrupado["VL_ITEM"].sum()
        perc  = (
            (pl.col("VL_ITEM") / total)
            if total
            else pl.lit(0.0).cast(pl.Float64)
        )
        agrupado = agrupado.with_columns(perc.alias("PERC"))
        total_row = {
            descr_col: [" TOTAL"],
            "VL_ITEM":  [agrupado["VL_ITEM"].sum()],
            "PERC":     [agrupado["PERC"].sum()],
        }
        return pl.concat([agrupado, pl.DataFrame(total_row, schema=agrupado.schema)])

    return {"ent": _lado("0"), "sai": _lado("1")}


def _resumo_c190_por_cfop(df: pl.DataFrame, cfops: set[str]) -> pl.DataFrame:
    """
    Filtra C190 pelo conjunto de CFOPs, agrupa por CFOP + DESCR_CFOP,
    soma VL_OPR/VL_BC_ICMS/VL_ICMS e adiciona linha de total.
    Retorna sempre DataFrame não-vazio (skeleton com TOTAL zerado quando sem dados).
    """
    def _skeleton() -> pl.DataFrame:
        return pl.DataFrame({
            "CFOP":        pl.Series([" TOTAL"], dtype=pl.Utf8),
            cd.DESCR_CFOP: pl.Series([None],    dtype=pl.Utf8),
            "VL_OPR":      pl.Series([0.0],     dtype=pl.Float64),
            "VL_BC_ICMS":  pl.Series([0.0],     dtype=pl.Float64),
            "VL_ICMS":     pl.Series([0.0],     dtype=pl.Float64),
        })

    if df.is_empty() or "CFOP" not in df.columns or "VL_OPR" not in df.columns:
        return _skeleton()

    filtrado = df.filter(pl.col("CFOP").cast(pl.Utf8).is_in(cfops))
    if filtrado.is_empty():
        return _skeleton()

    grupo_cols = ["CFOP"] + ([cd.DESCR_CFOP] if cd.DESCR_CFOP in filtrado.columns else [])
    sum_cols   = [c for c in ["VL_OPR", "VL_BC_ICMS", "VL_ICMS"] if c in filtrado.columns]

    agrupado = (
        filtrado.group_by(grupo_cols)
                .agg([pl.col(c).sum() for c in sum_cols])
                .sort("VL_OPR", descending=True)
    )
    total_row = {
        col: ([" TOTAL"] if col in grupo_cols else [agrupado[col].sum()])
        for col in agrupado.columns
    }
    return pl.concat([agrupado, pl.DataFrame(total_row, schema=agrupado.schema)])


# ── Analytics por categoria de CFOP (C170-based) ──────────────────────────────

def _resumo_por_cfop(df: pl.DataFrame, cfops: set[str]) -> pl.DataFrame:
    """
    Filtra C170 por CFOP e agrupa apenas por DESCR_COMPL (sem CFOP/DESCR_CFOP),
    soma VL_ITEM e calcula percentual do total.
    Retorna sempre DataFrame não-vazio (skeleton com TOTAL zerado quando sem dados).
    """
    descr_col = (
        "DESCR_COMPL" if (df.is_empty() or "DESCR_COMPL" in df.columns)
        else ("DESCR_ITEM" if "DESCR_ITEM" in df.columns else "DESCR_COMPL")
    )

    def _skeleton() -> pl.DataFrame:
        return pl.DataFrame({
            descr_col: pl.Series([" TOTAL"], dtype=pl.Utf8),
            "VL_ITEM": pl.Series([0.0],      dtype=pl.Float64),
            "PERC":    pl.Series([0.0],      dtype=pl.Float64),
        })

    if df.is_empty() or "CFOP" not in df.columns or "VL_ITEM" not in df.columns:
        return _skeleton()
    if cd.EM_EFD_C not in df.columns:
        return _skeleton()

    filtrado = df.filter(
        pl.col("CFOP").cast(pl.Utf8).is_in(cfops)
        & (pl.col(cd.EM_EFD_C) == "Nao encontrado")
    )
    if filtrado.is_empty():
        return _skeleton()

    if descr_col not in filtrado.columns:
        return _skeleton()

    filtrado = filtrado.filter(
        pl.col(descr_col).is_not_null()
        & (pl.col(descr_col).str.strip_chars() != "")
    )
    if filtrado.is_empty():
        return _skeleton()

    agrupado = (
        filtrado
        .group_by(descr_col)
        .agg(pl.col("VL_ITEM").sum())
        .sort("VL_ITEM", descending=True)
    )
    total = agrupado["VL_ITEM"].sum()
    perc = (pl.col("VL_ITEM") / total) if total else pl.lit(0.0).cast(pl.Float64)
    agrupado = agrupado.with_columns(perc.alias("PERC"))

    total_row = {
        descr_col: [" TOTAL"],
        "VL_ITEM":  [agrupado["VL_ITEM"].sum()],
        "PERC":     [agrupado["PERC"].sum()],
    }
    return pl.concat([agrupado, pl.DataFrame(total_row, schema=agrupado.schema)])


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


def _coletar_cnpjs_emit(dfs: list[pl.DataFrame]) -> list[str]:
    """
    Coleta CNPJs únicos normalizados (14 dígitos) da coluna CNPJ_EMIT de cada DataFrame.
    Usado para carregar apenas os registros relevantes de ESTABELECIMENTO.
    """
    result: set[str] = set()
    for df in dfs:
        if df.is_empty() or "CNPJ_EMIT" not in df.columns:
            continue
        vals = (
            df.select(
                pl.col("CNPJ_EMIT").cast(pl.Utf8)
                .str.replace_all(r"\D", "").str.zfill(14)
            )
            .drop_nulls()
            .unique()
            ["CNPJ_EMIT"]
            .to_list()
        )
        result.update(v for v in vals if v)
    return list(result)


def _carregar_estabelecimento(cnpjs: list[str] | None = None) -> pl.DataFrame:
    """
    Carrega ESTABELECIMENTO.parquet usando predicate pushdown.

    Se cnpjs fornecido, filtra o Parquet de 3 GB para apenas as linhas com
    _CNPJ_E na lista (scan lazy + collect), evitando carregar o arquivo inteiro
    em memória. Retorna DataFrame com _CNPJ_E e colunas CNAE renomeadas.
    """
    try:
        lf = pl.scan_parquet(cd.CAMINHO_ESTABELECIMENTO)
        if cnpjs:
            lf = lf.filter(pl.col("_CNPJ_E").is_in(cnpjs))
        df = lf.collect()
        rename = {
            "CNAE FISCAL PRINCIPAL":          cd.CNAE_PRINCIPAL,
            "ATIVIDADE ECONOMICA PRINCIPAL":  cd.ATIVIDADE_PRINCIPAL,
            "CNAE FISCAL SECUNDARIA":         cd.CNAE_SECUNDARIA,
            "ATIVIDADE ECONOMICA SECUNDARIA": cd.ATIVIDADE_SECUNDARIA,
        }
        rename = {k: v for k, v in rename.items() if k in df.columns}
        if rename:
            df = df.rename(rename)
        return df
    except Exception:
        return pl.DataFrame()


def _carregar_simples(raizes: list[str] | None = None) -> pl.DataFrame:
    """
    Carrega SIMPLES.parquet filtrando por raiz de CNPJ (8 dig.) quando fornecido.

    Sem filtro: carrega os 47 M registros (223 MB — uso somente em testes).
    Com filtro: scan lazy + predicate pushdown retorna apenas as linhas necessárias.
    O Parquet já tem 'N'/'NC' -> 'RPA' da conversão; 'S' -> 'Simples Nacional'
    é aplicado aqui em memória.
    """
    try:
        lf = pl.scan_parquet(cd.CAMINHO_SIMPLES)
        if raizes:
            lf = lf.filter(pl.col("CNPJ BASICO").is_in(raizes))
        df = lf.collect()
        rename = {
            "CNPJ BASICO":        "_CNPJ_RAIZ_S",
            "OPCAO PELO SIMPLES": cd.OPCAO_SIMPLES,
        }
        rename = {k: v for k, v in rename.items() if k in df.columns}
        if rename:
            df = df.rename(rename)
        if cd.OPCAO_SIMPLES in df.columns:
            df = df.with_columns(
                pl.when(pl.col(cd.OPCAO_SIMPLES) == "S")
                .then(pl.lit("Simples Nacional"))
                .otherwise(pl.col(cd.OPCAO_SIMPLES))
                .alias(cd.OPCAO_SIMPLES)
            )
        return df
    except Exception:
        return pl.DataFrame()


# ── Enriquecimento ─────────────────────────────────────────────────────────────

def _enriquecer_participantes(df: pl.DataFrame, participantes: pl.DataFrame) -> pl.DataFrame:
    if participantes.is_empty() or "COD_PART" not in df.columns:
        return df
    to_drop = [c for c in [cd.RAZAO_SOCIAL, "CNPJ_EMIT", cd.UF_EMIT] if c in df.columns]
    if to_drop:
        df = df.drop(to_drop)
    # Seleciona apenas as colunas necessárias — evita ID-SPED_right no resultado
    lookup_cols = [c for c in ["COD_PART", cd.RAZAO_SOCIAL, "CNPJ_EMIT", cd.UF_EMIT]
                   if c in participantes.columns]
    return df.join(participantes.select(lookup_cols), on="COD_PART", how="left")


def _enriquecer_cnae(df: pl.DataFrame, estab_df: pl.DataFrame) -> pl.DataFrame:
    """Adiciona CNAE principal/secundario e atividades do emitente via CNPJ_EMIT (14 dig.)."""
    if estab_df.is_empty() or "CNPJ_EMIT" not in df.columns:
        return df
    to_drop = [c for c in [cd.CNAE_PRINCIPAL, cd.ATIVIDADE_PRINCIPAL,
                            cd.CNAE_SECUNDARIA, cd.ATIVIDADE_SECUNDARIA] if c in df.columns]
    if to_drop:
        df = df.drop(to_drop)
    df = df.with_columns(
        pl.col("CNPJ_EMIT").cast(pl.Utf8)
        .str.replace_all(r"\D", "").str.zfill(14).alias("_CNPJ_E")
    )
    df = df.join(estab_df, on="_CNPJ_E", how="left")
    return df.drop("_CNPJ_E")


def _enriquecer_simples(df: pl.DataFrame, simples_df: pl.DataFrame) -> pl.DataFrame:
    """Adiciona OPCAO_SIMPLES via raiz do CNPJ_EMIT (8 primeiros dígitos)."""
    if simples_df.is_empty() or "CNPJ_EMIT" not in df.columns:
        return df
    if cd.OPCAO_SIMPLES in df.columns:
        df = df.drop(cd.OPCAO_SIMPLES)
    df = df.with_columns(
        pl.col("CNPJ_EMIT").cast(pl.Utf8)
        .str.replace_all(r"\D", "").str.slice(0, 8).alias("_CNPJ_RAIZ")
    )
    df = df.join(simples_df, left_on="_CNPJ_RAIZ", right_on="_CNPJ_RAIZ_S", how="left")
    return df.drop("_CNPJ_RAIZ")


def _enriquecer_0200(df: pl.DataFrame, itens_0200: pl.DataFrame) -> pl.DataFrame:
    if itens_0200.is_empty() or "COD_ITEM" not in df.columns:
        return df
    join_keys = [k for k in [dfn.ID_SPED, "COD_ITEM"] if k in df.columns and k in itens_0200.columns]
    to_drop = [c for c in ["DESCR_ITEM", "UNID_INV", "TIPO_ITEM", "COD_NCM"] if c in df.columns]
    if to_drop:
        df = df.drop(to_drop)
    return df.join(itens_0200, on=join_keys or ["COD_ITEM"], how="left")


def _enriquecer_0500(df: pl.DataFrame, df_0500: pl.DataFrame) -> pl.DataFrame:
    """Adiciona NOME_CTA via join com registro 0500 (plano de contas referencial).

    A chave é apenas COD_CTA. O lookup é construído a partir de ambos os arquivos
    SPED (fiscal e contribuições), pois cada um pode ter planos de contas distintos.
    """
    if df_0500.is_empty() or df.is_empty() or "COD_CTA" not in df.columns:
        return df
    if cd.NOME_CTA not in df_0500.columns or "COD_CTA" not in df_0500.columns:
        return df
    lookup = (
        df_0500
        .select(["COD_CTA", cd.NOME_CTA])
        .unique(subset=["COD_CTA"], keep="first")
    )
    if cd.NOME_CTA in df.columns:
        df = df.drop(cd.NOME_CTA)
    return df.join(lookup, on="COD_CTA", how="left")


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
_C170_C_SUM = ["VL_BC_PIS", "VL_PIS", "VL_BC_COFINS", "VL_COFINS", "VL_ITEM"]


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
    """D190_F LEFT JOIN D101_C em CHV_CTE. Adiciona ITEM_KEY e flag EM_EFD_C."""
    if d190_f.is_empty():
        return pl.DataFrame()

    join_cols = [
        c for c in ["CHV_CTE"]
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

    item_parts = [c for c in ["CHV_CTE"] if c in cruzado.columns]
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

    # ── Fase 1: lookups pequenos em paralelo ──────────────────────────────────
    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_cfop     = pool.submit(_carregar_cfop)
        fut_cst      = pool.submit(_carregar_cst)
        fut_cst_icms = pool.submit(_carregar_cst_icms)
        cfop_df     = fut_cfop.result()
        cst_df      = fut_cst.result()
        cst_icms_df = fut_cst_icms.result()

    # ── Fase 2: extrações SPED em paralelo ───────────────────────────────────
    # Todas as funções extrair_* são puras: recebem DataFrames imutáveis e
    # retornam novos DataFrames sem efeitos colaterais — thread-safe.
    with ThreadPoolExecutor(max_workers=11) as pool:
        fut_c170_f = pool.submit(
            dop.extrair_c170_fiscal, df_fiscal, df_assets_f, versao_f)
        fut_c170_c = pool.submit(
            dop.extrair_c170_contribuicoes, df_contribuicoes, df_assets_c, versao_c)
        fut_d190_f = pool.submit(
            dbd.extrair_d190_fiscal, df_fiscal, df_assets_f, versao_f)
        fut_d101_c = pool.submit(
            dbd.extrair_d101_contribuicoes, df_contribuicoes, df_assets_c, versao_c)
        fut_a170   = pool.submit(
            dba.extrair_a170_contribuicoes, df_contribuicoes, df_assets_c, versao_c)
        fut_f100   = pool.submit(
            dbf.extrair_f100_contribuicoes, df_contribuicoes, df_assets_c, versao_c)
        fut_part   = pool.submit(
            dop.extrair_participantes_uc,
            df_fiscal, df_assets_f, versao_f,
            df_contribuicoes, df_assets_c, versao_c)
        fut_0200   = pool.submit(
            dop.extrair_0200_fiscal, df_fiscal, df_assets_f, versao_f)
        fut_c190   = pool.submit(
            dop.extrair_c190_fiscal, df_fiscal, df_assets_f, versao_f)
        fut_0500_f = pool.submit(
            dop.extrair_0500_fiscal, df_fiscal, df_assets_f, versao_f)
        fut_0500_c = pool.submit(
            dop.extrair_0500_fiscal, df_contribuicoes, df_assets_c, versao_c)

        c170_f        = fut_c170_f.result()
        c170_c        = fut_c170_c.result()
        d190_f        = fut_d190_f.result()
        d101_c        = fut_d101_c.result()
        df_a170       = fut_a170.result()
        df_f100       = fut_f100.result()
        participantes = fut_part.result()
        itens_0200    = fut_0200.result()
        df_c190       = fut_c190.result()
        _0500_f       = fut_0500_f.result()
        _0500_c       = fut_0500_c.result()

    # ── Fase 3: cruzamentos + coleta de CNPJs + lookups pesados em paralelo ──
    c170_f  = _consolidar_c170(c170_f, _C170_F_SUM)
    c170_c  = _consolidar_c170(c170_c, _C170_C_SUM)
    df_c170 = _cruzar_c170(c170_f, c170_c)
    if not df_c170.is_empty():
        df_c170 = _enriquecer_participantes(df_c170, participantes)

    df_d190 = _cruzar_d190(d190_f, d101_c)
    if not df_d190.is_empty():
        df_d190 = _enriquecer_participantes(df_d190, participantes)

    if not df_a170.is_empty():
        df_a170 = _enriquecer_participantes(df_a170, participantes)

    if not df_f100.is_empty():
        df_f100 = _enriquecer_participantes(df_f100, participantes)

    # ESTABELECIMENTO (3 GB, filtrado por CNPJ) e SIMPLES (223 MB, filtrado por
    # raiz CNPJ) carregados em paralelo — I/O independente.
    cnpjs_e        = _coletar_cnpjs_emit([df_c170, df_d190, df_a170])
    raizes_simples = list({c[:8] for c in cnpjs_e if len(c) >= 8})

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_estab   = pool.submit(_carregar_estabelecimento, cnpjs_e)
        fut_simples = pool.submit(_carregar_simples, raizes_simples)
        estab_df   = fut_estab.result()
        simples_df = fut_simples.result()

    if not df_c190.is_empty():
        df_c190 = _enriquecer_cfop(df_c190, cfop_df)

    # ── Fase 4: enriquecimentos em paralelo ──────────────────────────────────
    # Cada tabela trabalha no seu próprio DataFrame — sem dependência cruzada.
    def _enrich_c170(df: pl.DataFrame) -> pl.DataFrame:
        df = _enriquecer_cnae(df, estab_df)
        df = _enriquecer_simples(df, simples_df)
        df = _enriquecer_0200(df, itens_0200)
        df = _enriquecer_cfop(df, cfop_df)
        df = _enriquecer_cst_icms(df, cst_icms_df)
        df = _enriquecer_cst(df, cst_df)
        df = _enriquecer_0500(df, _0500_f)    # 0500 do EFD Fiscal
        return df

    def _enrich_d190(df: pl.DataFrame) -> pl.DataFrame:
        df = _enriquecer_cnae(df, estab_df)
        df = _enriquecer_simples(df, simples_df)
        df = _enriquecer_cfop(df, cfop_df)
        df = _enriquecer_cst_icms(df, cst_icms_df)
        df = _enriquecer_cst(df, cst_df)
        df = _enriquecer_0500(df, _0500_f)    # 0500 do EFD Fiscal
        return df

    def _enrich_a170(df: pl.DataFrame) -> pl.DataFrame:
        df = _enriquecer_cnae(df, estab_df)
        df = _enriquecer_simples(df, simples_df)
        df = _enriquecer_cst(df, cst_df)
        df = _enriquecer_0500(df, _0500_c)    # 0500 do EFD Contribuições
        return df

    def _enrich_f100(df: pl.DataFrame) -> pl.DataFrame:
        df = _enriquecer_cst(df, cst_df)
        df = _enriquecer_0500(df, _0500_c)    # 0500 do EFD Contribuições
        return df

    with ThreadPoolExecutor(max_workers=4) as pool:
        fut_ec170 = pool.submit(_enrich_c170, df_c170) if not df_c170.is_empty() else None
        fut_ed190 = pool.submit(_enrich_d190, df_d190) if not df_d190.is_empty() else None
        fut_ea170 = pool.submit(_enrich_a170, df_a170) if not df_a170.is_empty() else None
        fut_ef100 = pool.submit(_enrich_f100, df_f100) if not df_f100.is_empty() else None

        if fut_ec170: df_c170 = fut_ec170.result()
        if fut_ed190: df_d190 = fut_ed190.result()
        if fut_ea170: df_a170 = fut_ea170.result()
        if fut_ef100: df_f100 = fut_ef100.result()

    # ── Analytics e resultado ─────────────────────────────────────────────────
    # ANALISE_PRODUTOS usa c170_c (EFD Contribuicoes, pre-cruzamento).
    resultado["ANALISE_PRODUTOS"]    = _resumo_c170_produtos(c170_c)
    resultado["ANALISE_OPERACOES"]   = _resumo_c190(df_c190)
    resultado["ANALISE_USO_CONSUMO"] = _resumo_por_cfop(df_c170, _CFOP_USO_CONSUMO)
    resultado["ANALISE_INSUMOS"]     = _resumo_por_cfop(df_c170, _CFOP_INSUMOS)
    resultado["ANALISE_REVENDA"]     = _resumo_por_cfop(df_c170, _CFOP_REVENDA)
    resultado["ANALISE_ATIVO_IMOB"]  = _resumo_por_cfop(df_c170, _CFOP_ATIVO_IMOB)
    # Metadado: CFOPs usados em cada análise (para exibição no subtítulo do Excel)
    resultado["_CFOPS"] = {
        "ANALISE_USO_CONSUMO": sorted(_CFOP_USO_CONSUMO),
        "ANALISE_INSUMOS":     sorted(_CFOP_INSUMOS),
        "ANALISE_REVENDA":     sorted(_CFOP_REVENDA),
        "ANALISE_ATIVO_IMOB":  sorted(_CFOP_ATIVO_IMOB),
    }
    resultado["C170"] = _reorder_c170(df_c170)
    resultado["D190"] = _reorder_d190(df_d190)
    resultado["A170"] = _reorder_a170(df_a170)
    resultado["F100"] = _reorder_f100(df_f100)

    return resultado
