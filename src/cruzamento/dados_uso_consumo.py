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


# ─── Regime tributário ───────────────────────────────────────────────────────

def identificar_regime(
    df_contribuicoes: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> tuple[str, str | None]:
    """
    Reads the COD_INC_TRIB field from the 0000 record of EFD Contribuições.

    Returns:
        regime: human-readable regime label (cd.REGIME_REAL / cd.REGIME_PRESUMIDO)
        cod_inc_trib: raw value from the SPED ("1", "2", "3", ...)
    """
    if df_contribuicoes.is_empty() or versao is None:
        return cd.REGIME_OUTRO, None

    reg_0000 = df_contribuicoes.filter(pl.col(dfn.REGISTRO) == "0000")
    if reg_0000.is_empty():
        return cd.REGIME_OUTRO, None

    try:
        reg_0000 = rename_columns(reg_0000, df_assets, versao, "0000")
    except Exception:
        return cd.REGIME_OUTRO, None

    if cd.COD_INC_TRIB not in reg_0000.columns:
        return cd.REGIME_OUTRO, None

    cod = reg_0000.select(pl.col(cd.COD_INC_TRIB)).item(0, 0)
    cod = str(cod).strip() if cod is not None else None

    if cod == "1":
        return cd.REGIME_REAL, cod
    elif cod in ("2", "3"):
        return cd.REGIME_PRESUMIDO, cod
    else:
        return cd.REGIME_OUTRO, cod


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
    ff_cols = [c for c in [cd.CHV_NFE, cd.COD_SIT, cd.COD_PART, "COD_PART_C100"] if c in df_fiscal.columns]
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
        dfn.ID_SPED, dfn.ID_PAI,
        "NUM_ITEM", "COD_ITEM", "DESCR_COMPL",
        "VL_ITEM", "CFOP", "CST_ICMS", "ALIQ_ICMS", "VL_ICMS",
        cd.CHV_NFE,   # forward-filled from parent C100
        cd.COD_SIT,   # forward-filled from parent C100
        cd.COD_PART,  # forward-filled from parent C100
    ]
    result = _safe_select(renamed, desired)
    return _to_float(result, ["VL_ITEM", "ALIQ_ICMS", "VL_ICMS"])


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

    # Forward-fill CHV_NFE / COD_SIT from C100 to C170 (same logic as fiscal)
    ff_cols = [c for c in [cd.CHV_NFE, cd.COD_SIT, cd.COD_PART, "COD_PART_C100"] if c in df_contribuicoes.columns]
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
        cd.CHV_NFE,   # forward-filled from parent C100
        cd.COD_SIT,   # forward-filled from parent C100
        cd.COD_PART,  # forward-filled from parent C100
    ]
    result = _safe_select(renamed, desired)
    return _to_float(result, [
        "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
    ])


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

    Returns columns: COD_PART, NOME_DEST (razão social), CNPJ_DEST
    Deduplicates by COD_PART, preferring entries with non-null CNPJ_DEST.
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
            desired = [c for c in ["COD_PART", "NOME", cnpj_col] if c is not None]
            selected = _safe_select(renamed, desired)

            if "NOME" in selected.columns:
                selected = selected.rename({"NOME": cd.RAZAO_SOCIAL})
            if cnpj_col and cnpj_col in selected.columns:
                selected = selected.rename({cnpj_col: "CNPJ_EMIT"})

            frames.append(selected)
        except Exception:
            continue

    if not frames:
        return pl.DataFrame({"COD_PART": [], cd.RAZAO_SOCIAL: [], "CNPJ_EMIT": []})

    participantes = pl.concat(frames, how="diagonal")

    # Prefer rows with CNPJ filled; keep one per COD_PART
    # Guard: sort on CNPJ_EMIT only if the column actually exists
    if "CNPJ_EMIT" in participantes.columns:
        participantes = (
            participantes
            .sort("CNPJ_EMIT", nulls_last=True)
            .unique(subset=["COD_PART"], keep="first")
        )
    else:
        participantes = participantes.unique(subset=["COD_PART"], keep="first")

    return participantes
