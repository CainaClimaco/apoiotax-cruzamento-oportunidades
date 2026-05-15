"""
dados_bloco_m.py
────────────────
Extração do Bloco M (Apuração PIS/COFINS) do EFD Contribuições.

Registros extraídos:
  M200 / M600 — Resumo da apuração PIS e COFINS (totais do período)
  M210 / M610 — Detalhamento por CST (base de cálculo por tipo de receita)
  M110 / M510 — Ajustes da apuração PIS e COFINS
  M220 / M620 — Ajustes/benefícios/incentivos PIS e COFINS

Esses registros são ao nível de período (mês/ano + CNPJ).
Cruzamento com Bloco E do EFD_F: Período + CNPJ (nível macro).

Validação principal:
  SUM(M210.VL_BC_CONT WHERE CST IN CSTs_tributáveis) + ICMS (E110.VL_TOT_DEBITOS)
  ≈ Faturamento tributável ICMS do período
"""

import polars as pl
import datatricks.sped.sped_definitions as dfn
from cruzamento.dados_receita import rename_columns
from cruzamento.dados_oportunidades import _safe_select, _to_float, _cast_id_to_str


def _extrair_registro(
    df: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
    registro: str,
    desired: list[str],
    float_cols: list[str],
) -> pl.DataFrame:
    if df.is_empty() or versao is None:
        return pl.DataFrame()
    raw = df.filter(pl.col(dfn.REGISTRO) == registro)
    if raw.is_empty():
        return pl.DataFrame()
    try:
        renamed = rename_columns(raw, df_assets, versao, registro)
    except Exception:
        renamed = raw
    result = _safe_select(renamed, desired)
    result = _to_float(result, float_cols)
    return _cast_id_to_str(result)


# ── PIS ───────────────────────────────────────────────────────────────────────

def extrair_m200_contribuicoes(df, df_assets, versao):
    """Apuração total PIS do período."""
    desired = [
        dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI,
        "VL_TOT_CONT_NC_PER", "VL_TOT_CRED_DESC", "VL_TOT_CRED_DESC_ANT",
        "VL_TOT_CONT_NC_DEV", "VL_RET_NC", "VL_OUT_DED_NC", "VL_CONT_NC_REC",
        "VL_TOT_CONT_CUM_PER", "VL_RET_CUM", "VL_OUT_DED_CUM", "VL_CONT_CUM_REC",
        "VL_TOT_CONT_REC",
    ]
    float_cols = [c for c in desired if c not in (dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI)]
    return _extrair_registro(df, df_assets, versao, "M200", desired, float_cols)


def extrair_m210_contribuicoes(df, df_assets, versao):
    """Detalhamento PIS por CST (base de cálculo por natureza de receita)."""
    desired = [
        dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI,
        "COD_CONT", "VL_REC_BRT", "VL_BC_CONT", "ALIQ_PIS",
        "QUANT_BC_PIS", "ALIQ_PIS_QUANT", "VL_CONT_APUR",
        "VL_AJUS_ACRES", "VL_AJUS_REDUC", "VL_CONT_DIFER", "VL_CONT_DIFER_ANT",
        "VL_CONT_PER",
    ]
    _skip = {dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI, "COD_CONT"}
    float_cols = [c for c in desired if c not in _skip]
    return _extrair_registro(df, df_assets, versao, "M210", desired, float_cols)


def extrair_m110_contribuicoes(df, df_assets, versao):
    """Ajustes da apuração PIS."""
    desired = [
        dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI,
        "IND_AJ", "VL_AJ", "COD_AJ", "NUM_DOC", "DESCR_AJ", "DT_REF",
    ]
    return _extrair_registro(df, df_assets, versao, "M110", desired, ["VL_AJ"])


def extrair_m220_contribuicoes(df, df_assets, versao):
    """Ajustes/benefícios/incentivos da contribuição apurada para PIS."""
    desired = [
        dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI,
        "IND_AJ", "VL_AJ", "COD_AJ", "NUM_DOC", "DESCR_AJ", "DT_REF",
    ]
    return _extrair_registro(df, df_assets, versao, "M220", desired, ["VL_AJ"])


# ── COFINS ────────────────────────────────────────────────────────────────────

def extrair_m600_contribuicoes(df, df_assets, versao):
    """Apuração total COFINS do período."""
    desired = [
        dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI,
        "VL_TOT_CONT_NC_PER", "VL_TOT_CRED_DESC", "VL_TOT_CRED_DESC_ANT",
        "VL_TOT_CONT_NC_DEV", "VL_RET_NC", "VL_OUT_DED_NC", "VL_CONT_NC_REC",
        "VL_TOT_CONT_CUM_PER", "VL_RET_CUM", "VL_OUT_DED_CUM", "VL_CONT_CUM_REC",
        "VL_TOT_CONT_REC",
    ]
    float_cols = [c for c in desired if c not in (dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI)]
    return _extrair_registro(df, df_assets, versao, "M600", desired, float_cols)


def extrair_m610_contribuicoes(df, df_assets, versao):
    """Detalhamento COFINS por CST (base de cálculo por natureza de receita)."""
    desired = [
        dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI,
        "COD_CONT", "VL_REC_BRT", "VL_BC_CONT", "ALIQ_COFINS",
        "QUANT_BC_COFINS", "ALIQ_COFINS_QUANT", "VL_CONT_APUR",
        "VL_AJUS_ACRES", "VL_AJUS_REDUC", "VL_CONT_DIFER", "VL_CONT_DIFER_ANT",
        "VL_CONT_PER",
    ]
    _skip = {dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI, "COD_CONT"}
    float_cols = [c for c in desired if c not in _skip]
    return _extrair_registro(df, df_assets, versao, "M610", desired, float_cols)


def extrair_m510_contribuicoes(df, df_assets, versao):
    """Ajustes da apuração COFINS."""
    desired = [
        dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI,
        "IND_AJ", "VL_AJ", "COD_AJ", "NUM_DOC", "DESCR_AJ", "DT_REF",
    ]
    return _extrair_registro(df, df_assets, versao, "M510", desired, ["VL_AJ"])


def extrair_m620_contribuicoes(df, df_assets, versao):
    """Ajustes/benefícios/incentivos da contribuição apurada para COFINS."""
    desired = [
        dfn.PERIODO, dfn.CNPJ, dfn.ID_SPED, dfn.ID_PAI,
        "IND_AJ", "VL_AJ", "COD_AJ", "NUM_DOC", "DESCR_AJ", "DT_REF",
    ]
    return _extrair_registro(df, df_assets, versao, "M620", desired, ["VL_AJ"])
