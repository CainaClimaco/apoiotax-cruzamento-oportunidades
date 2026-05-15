"""
dados_uso_consumo.py
────────────────────
Extraction and normalization utilities for the Use & Consumption cross-referencing module.

Follows the same rename_columns pattern established in dados_receita.py, extracting
C100, C170, and 0150 records from both EFDs and returning clean DataFrames with
semantic column names sourced from the official SPED layout.
"""

import polars as pl
import datatricks.sped.sped_definitions as dfn
import cruzamento.cruzamento_definition as cd
from cruzamento.dados_receita import rename_columns


# ─── Internal helpers ────────────────────────────────────────────────────────

def _safe_select(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Select only the columns that exist in df (guards against version differences)."""
    existing = [c for c in cols if c in df.columns]
    return df.select(existing) if existing else df.clear()


def _to_float(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """Cast string monetary columns (comma decimal separator) to Float64."""
    exprs = []
    for col in cols:
        if col in df.columns:
            exprs.append(
                pl.col(col).str.replace(",", ".").cast(pl.Float64, strict=False).alias(col)
            )
    return df.with_columns(exprs) if exprs else df


def _cast_id_to_str(df: pl.DataFrame) -> pl.DataFrame:
    """Cast ID-SPED and ID-PAI to Utf8 text."""
    exprs = [pl.col(c).cast(pl.Utf8) for c in [dfn.ID_SPED, dfn.ID_PAI] if c in df.columns]
    return df.with_columns(exprs) if exprs else df


# ─── EFD ICMS IPI extractors ─────────────────────────────────────────────────

def extrair_c100_fiscal(
    df_fiscal: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extracts C100 records from EFD ICMS IPI with all fields needed for
    U&C cross-referencing (filtering is done in uso_consumo.py).

    Key columns returned:
        ID_SPED (dfn.ID_SPED), ID_PAI (dfn.ID_PAI),
        IND_OPER, COD_PART, COD_SIT, SER, NUM_DOC, CHV_NFE, DT_DOC, VL_DOC
    """
    if df_fiscal.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_fiscal.filter(pl.col(dfn.REGISTRO) == "C100")
    if raw.is_empty():
        return pl.DataFrame()

    renamed = rename_columns(raw, df_assets, versao, "C100")

    desired = [
        dfn.ID_SPED, dfn.ID_PAI,
        "IND_OPER", "IND_EMIT", "COD_PART", "COD_SIT",
        "SER", "NUM_DOC", "CHV_NFE", "DT_DOC", "VL_DOC",
    ]
    result = _safe_select(renamed, desired)
    return _to_float(result, ["VL_DOC"])


def extrair_c170_fiscal(
    df_fiscal: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extracts C170 records from EFD ICMS IPI, enriched with their parent C100's
    CHV_NFE, COD_SIT, and COD_PART via forward-fill.

    leitor_sped already computes CHV_NFE / COD_SIT / COD_PART as non-null for
    C100 rows and null for all other rows. Sorting by ID-SPED and forward-filling
    within each Periodo group propagates those values from each C100 record down
    to its C170 children — this works because the SPED file is strictly sequential
    (C100 always precedes its C170 children within the same block).

    Key columns returned:
        CHV_NFE, COD_SIT, COD_PART  (from parent C100, via forward-fill)
        NUM_ITEM, COD_ITEM, DESCR_COMPL, VL_ITEM, CFOP,
        CST_ICMS, ALIQ_ICMS, VL_ICMS  (from C170 layout)
        dfn.ID_SPED, dfn.ID_PAI
    """
    if df_fiscal.is_empty() or versao is None:
        return pl.DataFrame()

    # 1. Forward-fill C100 computed columns to C170 rows.
    #    Only the columns that actually exist in this leitor_sped output.
    ff_cols = [c for c in [cd.CHV_NFE, cd.COD_SIT, cd.COD_PART, "COD_PART_C100", "NUM_DOC", "DT_DOC"] if c in df_fiscal.columns]
    if ff_cols:
        periodo_col = dfn.PERIODO if dfn.PERIODO in df_fiscal.columns else "Periodo"
        df_enriched = df_fiscal.sort(dfn.ID_SPED).with_columns([
            pl.col(c).forward_fill().over(periodo_col).alias(c)
            for c in ff_cols
        ])
    else:
        df_enriched = df_fiscal

    # 2. Filter for C170 rows (now enriched with parent's CHV_NFE etc.)
    raw = df_enriched.filter(pl.col(dfn.REGISTRO) == "C170")
    if raw.is_empty():
        return pl.DataFrame()

    # 3. Rename layout-specific field columns to semantic names.
    renamed = rename_columns(raw, df_assets, versao, "C170")

    # 4. Select desired columns (CHV_NFE/COD_SIT survived rename as they don't
    #    start with 'field_' and weren't in the positional rename mapping).
    desired = [
        dfn.PERIODO, dfn.CNPJ,
        dfn.ID_SPED, dfn.ID_PAI,
        "NUM_ITEM", "COD_ITEM", "DESCR_COMPL",
        "VL_ITEM", "CFOP", "CST_ICMS", "ALIQ_ICMS", "VL_ICMS",
        cd.CHV_NFE,   # forward-filled from parent C100
        cd.COD_SIT,   # forward-filled from parent C100
        cd.COD_PART,  # forward-filled from parent C100
        "NUM_DOC",    # forward-filled from parent C100
        "DT_DOC",     # forward-filled from parent C100
    ]
    result = _safe_select(renamed, desired)
    result = _to_float(result, ["VL_ITEM", "ALIQ_ICMS", "VL_ICMS"])
    return _cast_id_to_str(result)


# ─── EFD Contribuições extractors ────────────────────────────────────────────

def extrair_c100_contribuicoes(
    df_contribuicoes: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extracts C100 records from EFD Contribuições (PIS/COFINS).

    Key columns returned:
        ID_SPED, ID_PAI, COD_PART, COD_SIT, SER, NUM_DOC, CHV_NFE, DT_DOC
    """
    if df_contribuicoes.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_contribuicoes.filter(pl.col(dfn.REGISTRO) == "C100")
    if raw.is_empty():
        return pl.DataFrame()

    renamed = rename_columns(raw, df_assets, versao, "C100")

    desired = [
        dfn.ID_SPED, dfn.ID_PAI,
        "IND_OPER", "COD_PART", "COD_SIT",
        "SER", "NUM_DOC", "CHV_NFE", "DT_DOC",
    ]
    return _safe_select(renamed, desired)


def extrair_c170_contribuicoes(
    df_contribuicoes: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extracts C170 records from EFD Contribuições (PIS/COFINS), enriched with
    their parent C100's CHV_NFE and COD_SIT via forward-fill (same technique
    as extrair_c170_fiscal).

    Key columns returned:
        CHV_NFE, COD_SIT (from parent C100, forward-filled)
        dfn.ID_SPED, dfn.ID_PAI,
        NUM_ITEM, COD_ITEM (when present in layout)
        CST_PIS, VL_BC_PIS, ALIQ_PIS, VL_PIS,
        CST_COFINS, VL_BC_COFINS, ALIQ_COFINS, VL_COFINS
    """
    if df_contribuicoes.is_empty() or versao is None:
        return pl.DataFrame()

    # Forward-fill CHV_NFE / COD_SIT / NUM_DOC / DT_DOC from C100 to C170
    ff_cols = [c for c in [cd.CHV_NFE, cd.COD_SIT, cd.COD_PART, "COD_PART_C100", "NUM_DOC", "DT_DOC"] if c in df_contribuicoes.columns]
    if ff_cols:
        periodo_col = dfn.PERIODO if dfn.PERIODO in df_contribuicoes.columns else "Periodo"
        df_enriched = df_contribuicoes.sort(dfn.ID_SPED).with_columns([
            pl.col(c).forward_fill().over(periodo_col).alias(c)
            for c in ff_cols
        ])
    else:
        df_enriched = df_contribuicoes

    raw = df_enriched.filter(pl.col(dfn.REGISTRO) == "C170")
    if raw.is_empty():
        return pl.DataFrame()

    renamed = rename_columns(raw, df_assets, versao, "C170")

    desired = [
        dfn.ID_SPED, dfn.ID_PAI,
        "NUM_ITEM", "COD_ITEM",
        "CST_PIS", "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        "CST_COFINS", "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
        "NATBC_CRED", "IND_ORIG_CRED",
        cd.CHV_NFE,   # forward-filled from parent C100
        cd.COD_PART,  # forward-filled from parent C100
        "NUM_DOC",    # forward-filled from parent C100
        "DT_DOC",     # forward-filled from parent C100
    ]
    result = _safe_select(renamed, desired)
    result = _to_float(result, [
        "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
    ])
    return _cast_id_to_str(result)


# ─── Participants (0150) ─────────────────────────────────────────────────────

def extrair_participantes_uc(
    df_fiscal: pl.DataFrame,
    df_assets_f: pl.DataFrame,
    versao_f: str | None,
    df_contribuicoes: pl.DataFrame,
    df_assets_c: pl.DataFrame,
    versao_c: str | None,
) -> pl.DataFrame:
    """
    Builds a unified participants lookup table (0150) from both EFDs.

    Returns columns: ID_SPED, COD_PART, RAZAO_SOCIAL, CNPJ_EMIT
    Deduplicates by [ID_SPED, COD_PART], preferring entries with non-null CNPJ_EMIT.
    """
    frames = []

    # CNPJ field names vary between EFD ICMS IPI and EFD Contribuições 0150 layouts
    CNPJ_CANDIDATES = ["CNPJ_CPF", "CNPJ", "CPF_CNPJ", "CNPJ_PART"]

    for df, df_assets, versao in [
        (df_fiscal, df_assets_f, versao_f),
        (df_contribuicoes, df_assets_c, versao_c),
    ]:
        if df.is_empty() or versao is None:
            continue
        raw = df.filter(pl.col(dfn.REGISTRO) == "0150")
        if raw.is_empty():
            continue
        try:
            renamed = rename_columns(raw, df_assets, versao, "0150")

            # Pick whichever CNPJ column exists in this EFD's 0150 layout
            cnpj_col = next((c for c in CNPJ_CANDIDATES if c in renamed.columns), None)
            desired = [c for c in [dfn.ID_SPED, "COD_PART", "NOME", cnpj_col] if c is not None]
            selected = _safe_select(renamed, desired)

            if "NOME" in selected.columns:
                selected = selected.rename({"NOME": cd.RAZAO_SOCIAL})
            if cnpj_col and cnpj_col in selected.columns:
                selected = selected.rename({cnpj_col: "CNPJ_EMIT"})

            frames.append(selected)
        except Exception:
            continue

    if not frames:
        return pl.DataFrame({dfn.ID_SPED: [], "COD_PART": [], cd.RAZAO_SOCIAL: [], "CNPJ_EMIT": []})

    participantes = pl.concat(frames, how="diagonal")

    # Prefer rows with CNPJ filled; keep one per [ID_SPED, COD_PART]
    dedup_cols = [c for c in [dfn.ID_SPED, "COD_PART"] if c in participantes.columns]
    if "CNPJ_EMIT" in participantes.columns:
        participantes = (
            participantes
            .sort("CNPJ_EMIT", nulls_last=True)
            .unique(subset=dedup_cols or ["COD_PART"], keep="first")
        )
    else:
        participantes = participantes.unique(subset=dedup_cols or ["COD_PART"], keep="first")

    return _cast_id_to_str(participantes)


# ─── C190 (ICMS analytical summary) ──────────────────────────────────────────

def extrair_c190_fiscal(
    df_fiscal: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extracts C190 (ICMS analytical summary by CFOP/CST) from EFD ICMS IPI.

    C190 is a period-level summary that aggregates C170 items by CFOP and CST.
    It has no direct counterpart in EFD Contribuições (standalone EFD_F output).

    Columns returned: ID_SPED, CST_ICMS, CFOP, ALIQ_ICMS, VL_OPR,
                      VL_BC_ICMS, VL_ICMS, VL_BC_ICMS_ST, VL_ICMS_ST, VL_RED_BC, VL_IPI
    """
    if df_fiscal.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_fiscal.filter(pl.col(dfn.REGISTRO) == "C190")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "C190")
    except Exception:
        renamed = raw

    desired = [
        dfn.PERIODO, dfn.CNPJ,
        dfn.ID_SPED, dfn.ID_PAI,
        "CST_ICMS", "CFOP", "ALIQ_ICMS", "VL_OPR",
        "VL_BC_ICMS", "VL_ICMS", "VL_BC_ICMS_ST", "VL_ICMS_ST",
        "VL_RED_BC", "VL_IPI",
    ]
    result = _safe_select(renamed, desired)
    result = _to_float(result, [
        "ALIQ_ICMS", "VL_OPR", "VL_BC_ICMS", "VL_ICMS",
        "VL_BC_ICMS_ST", "VL_ICMS_ST", "VL_RED_BC", "VL_IPI",
    ])
    return _cast_id_to_str(result)


# ─── Products (0200) ─────────────────────────────────────────────────────────

def extrair_0200_fiscal(
    df_fiscal: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extracts 0200 (product/item master) from EFD ICMS IPI.

    Returns columns: ID_SPED, COD_ITEM, DESCR_ITEM, UNID_INV, TIPO_ITEM, COD_NCM
    Deduplicates by [ID_SPED, COD_ITEM].
    """
    if df_fiscal.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_fiscal.filter(pl.col(dfn.REGISTRO) == "0200")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "0200")
    except Exception:
        renamed = raw

    desired = [dfn.ID_SPED, "COD_ITEM", "DESCR_ITEM", "UNID_INV", "TIPO_ITEM", "COD_NCM"]
    result = _safe_select(renamed, desired)
    if result.is_empty():
        return pl.DataFrame()

    dedup_cols = [c for c in [dfn.ID_SPED, "COD_ITEM"] if c in result.columns]
    result = result.unique(subset=dedup_cols or ["COD_ITEM"], keep="first")
    return _cast_id_to_str(result)


# ─── Accounts (0500) ─────────────────────────────────────────────────────────

def extrair_0500_fiscal(
    df_fiscal: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extracts 0500 (accounting chart of accounts) from EFD ICMS IPI.

    Returns columns: ID_SPED, COD_CTA, NOME_CTA, COD_NAT_CC
    Deduplicates by [ID_SPED, COD_CTA].
    """
    if df_fiscal.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_fiscal.filter(pl.col(dfn.REGISTRO) == "0500")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "0500")
    except Exception:
        renamed = raw

    desired = [dfn.ID_SPED, "COD_CTA", "NOME_CTA", "COD_NAT_CC"]
    result = _safe_select(renamed, desired)
    if result.is_empty():
        return pl.DataFrame()

    dedup_cols = [c for c in [dfn.ID_SPED, "COD_CTA"] if c in result.columns]
    result = result.unique(subset=dedup_cols or ["COD_CTA"], keep="first")
    return _cast_id_to_str(result)
