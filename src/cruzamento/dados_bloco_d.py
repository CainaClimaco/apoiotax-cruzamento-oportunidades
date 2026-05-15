"""
dados_bloco_d.py
────────────────
Extração do Bloco D (Documentos Fiscais de Transporte e Comunicação — CT-e) de ambas as EFDs.

EFD ICMS/IPI:
  D100 — Cabeçalho CT-e
  D190 — Analítico por CFOP / CST (nível de resumo)

EFD Contribuições:
  D100 — Cabeçalho CT-e
  D101 — Itens (nível de item, com CST_PIS/CST_COFINS)
"""

import polars as pl
import datatricks.sped.sped_definitions as dfn
import cruzamento.cruzamento_definition as cd
from cruzamento.dados_receita import rename_columns
from cruzamento.dados_oportunidades import _safe_select, _to_float, _cast_id_to_str


def extrair_d100_fiscal(
    df_fiscal: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extrai D100 (cabeçalho CT-e) do EFD ICMS/IPI.

    Colunas retornadas: ID_SPED, ID_PAI, COD_PART, COD_SIT, CHV_CTE, DT_DOC, VL_DOC
    """
    if df_fiscal.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_fiscal.filter(pl.col(dfn.REGISTRO) == "D100")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "D100")
    except Exception:
        renamed = raw

    desired = [
        dfn.ID_SPED, dfn.ID_PAI,
        "COD_PART", "COD_SIT", "CHV_CTE", "DT_DOC", "VL_DOC",
    ]
    result = _safe_select(renamed, desired)
    return _to_float(result, ["VL_DOC"])


def extrair_d190_fiscal(
    df_fiscal: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extrai D190 (analítico CT-e por CFOP/CST) do EFD ICMS/IPI,
    enriquecido com campos do D100 pai via forward-fill.

    Colunas retornadas:
      ID_SPED, ID_PAI, CFOP, CST_ICMS, ALIQ_ICMS, VL_BC_ICMS, VL_ICMS,
      COD_PART, COD_SIT, CHV_CTE, DT_DOC (forward-filled do D100)
    """
    if df_fiscal.is_empty() or versao is None:
        return pl.DataFrame()

    ff_cols = [c for c in [cd.COD_PART, cd.COD_SIT, "CHV_CTE", "DT_DOC"] if c in df_fiscal.columns]
    if ff_cols:
        periodo_col = dfn.PERIODO if dfn.PERIODO in df_fiscal.columns else "Periodo"
        df_enriched = df_fiscal.sort(dfn.ID_SPED).with_columns([
            pl.col(c).forward_fill().over(periodo_col).alias(c)
            for c in ff_cols
        ])
    else:
        df_enriched = df_fiscal

    raw = df_enriched.filter(pl.col(dfn.REGISTRO) == "D190")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "D190")
    except Exception:
        renamed = raw

    desired = [
        dfn.PERIODO, dfn.CNPJ,
        dfn.ID_SPED, dfn.ID_PAI,
        "CFOP", "CST_ICMS", "ALIQ_ICMS", "VL_BC_ICMS", "VL_ICMS",
        cd.COD_PART, cd.COD_SIT, "CHV_CTE", "DT_DOC",
    ]
    result = _safe_select(renamed, desired)
    result = _to_float(result, ["ALIQ_ICMS", "VL_BC_ICMS", "VL_ICMS"])
    return _cast_id_to_str(result)


def extrair_d100_contribuicoes(
    df_contribuicoes: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extrai D100 (cabeçalho CT-e) do EFD Contribuições.

    Colunas retornadas: ID_SPED, ID_PAI, COD_PART, COD_SIT, CHV_CTE, DT_DOC, VL_DOC
    """
    if df_contribuicoes.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_contribuicoes.filter(pl.col(dfn.REGISTRO) == "D100")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "D100")
    except Exception:
        renamed = raw

    desired = [
        dfn.ID_SPED, dfn.ID_PAI,
        "COD_PART", "COD_SIT", "CHV_CTE", "DT_DOC", "VL_DOC",
    ]
    result = _safe_select(renamed, desired)
    return _to_float(result, ["VL_DOC"])


def extrair_d101_contribuicoes(
    df_contribuicoes: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extrai e combina D101 (PIS) + D105 (COFINS) do EFD Contribuições.

    D101 e D105 são filhos do mesmo D100 (mesmo ID_PAI = CHV_CTE do CT-e).
    O join entre eles é feito por ID_PAI para reunir PIS e COFINS na mesma linha.

    Chave de cruzamento com D190_F: CHV_CTE
    """
    if df_contribuicoes.is_empty() or versao is None:
        return pl.DataFrame()

    ff_cols = [c for c in [cd.COD_PART, cd.COD_SIT, "CHV_CTE", "DT_DOC"] if c in df_contribuicoes.columns]
    if ff_cols:
        periodo_col = dfn.PERIODO if dfn.PERIODO in df_contribuicoes.columns else "Periodo"
        df_enriched = df_contribuicoes.sort(dfn.ID_SPED).with_columns([
            pl.col(c).forward_fill().over(periodo_col).alias(c)
            for c in ff_cols
        ])
    else:
        df_enriched = df_contribuicoes

    # ── D101: PIS ────────────────────────────────────────────────────
    raw_d101 = df_enriched.filter(pl.col(dfn.REGISTRO) == "D101")
    if not raw_d101.is_empty():
        try:
            raw_d101 = rename_columns(raw_d101, df_assets, versao, "D101")
        except Exception:
            pass
    desired_d101 = [
        dfn.ID_SPED, dfn.ID_PAI,
        "CST_PIS", "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        "NATBC_CRED",
        cd.COD_PART, "CHV_CTE", "DT_DOC",
    ]
    d101 = _safe_select(raw_d101, desired_d101) if not raw_d101.is_empty() else pl.DataFrame()
    if not d101.is_empty():
        d101 = _to_float(d101, ["VL_BC_PIS", "ALIQ_PIS", "VL_PIS"])
        d101 = _cast_id_to_str(d101)

    # ── D105: COFINS ─────────────────────────────────────────────────
    raw_d105 = df_enriched.filter(pl.col(dfn.REGISTRO) == "D105")
    if not raw_d105.is_empty():
        try:
            raw_d105 = rename_columns(raw_d105, df_assets, versao, "D105")
        except Exception:
            pass
    desired_d105 = [
        dfn.ID_PAI,
        "CST_COFINS", "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
    ]
    d105 = _safe_select(raw_d105, desired_d105) if not raw_d105.is_empty() else pl.DataFrame()
    if not d105.is_empty():
        d105 = _to_float(d105, ["VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS"])
        d105 = _cast_id_to_str(d105)

    if d101.is_empty() and d105.is_empty():
        return pl.DataFrame()

    if d101.is_empty():
        return d105

    if d105.is_empty():
        return d101

    # Join D101 + D105 por ID_PAI (ambos filhos do mesmo D100)
    cofins_cols = [c for c in d105.columns if c != dfn.ID_PAI]
    result = d101.join(
        d105.select([dfn.ID_PAI] + cofins_cols),
        on=dfn.ID_PAI,
        how="left",
    )
    return result
