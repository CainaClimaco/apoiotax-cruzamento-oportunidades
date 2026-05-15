"""
dados_bloco_e.py
────────────────
Extração do Bloco E (Apuração do ICMS e IPI) do EFD ICMS/IPI.

Registros extraídos:
  E110 — Apuração do ICMS próprio (saldos e débitos/créditos do período)
  E210 — Apuração do ICMS-ST (substituição tributária)
  E520 — Apuração do IPI

Esses registros são ao nível de período (mês/ano + CNPJ),
não ao nível de item. O cruzamento com o Bloco M do EFD_C é feito
por Período + CNPJ para validações macro de base de cálculo.
"""

import polars as pl
import datatricks.sped.sped_definitions as dfn
from cruzamento.dados_receita import rename_columns
from cruzamento.dados_oportunidades import _safe_select, _to_float, _cast_id_to_str


def extrair_e110_fiscal(
    df_fiscal: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extrai E110 (apuração ICMS próprio) do EFD ICMS/IPI.

    Campos principais: VL_TOT_DEBITOS (débitos por saídas), VL_TOT_CREDITOS,
    VL_SLD_CREDOR_ANT, VL_SLD_APURADO, VL_TOT_DED, VL_ICMS_RECOLHER,
    VL_SLD_CREDOR_TRANSP
    """
    if df_fiscal.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_fiscal.filter(pl.col(dfn.REGISTRO) == "E110")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "E110")
    except Exception:
        renamed = raw

    desired = [
        dfn.PERIODO, dfn.CNPJ,
        dfn.ID_SPED, dfn.ID_PAI,
        "VL_TOT_DEBITOS", "VL_AJ_DEBITOS", "VL_TOT_AJ_DEBITOS",
        "VL_ESTORNOS_CRED", "VL_TOT_CREDITOS", "VL_AJ_CREDITOS",
        "VL_TOT_AJ_CREDITOS", "VL_ESTORNOS_DEB", "VL_SLD_CREDOR_ANT",
        "VL_SLD_APURADO", "VL_TOT_DED", "VL_ICMS_RECOLHER",
        "VL_SLD_CREDOR_TRANSP", "DEB_ESP",
    ]
    result = _safe_select(renamed, desired)
    result = _to_float(result, [
        "VL_TOT_DEBITOS", "VL_AJ_DEBITOS", "VL_TOT_AJ_DEBITOS",
        "VL_ESTORNOS_CRED", "VL_TOT_CREDITOS", "VL_AJ_CREDITOS",
        "VL_TOT_AJ_CREDITOS", "VL_ESTORNOS_DEB", "VL_SLD_CREDOR_ANT",
        "VL_SLD_APURADO", "VL_TOT_DED", "VL_ICMS_RECOLHER",
        "VL_SLD_CREDOR_TRANSP", "DEB_ESP",
    ])
    return _cast_id_to_str(result)


def extrair_e210_fiscal(
    df_fiscal: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extrai E210 (apuração ICMS-ST) do EFD ICMS/IPI.

    Nota: ICMS-ST não tem correspondente direto no Bloco M da EFD Contribuições
    (tratamento monofásico e substituição são escriturados de forma diferente).
    """
    if df_fiscal.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_fiscal.filter(pl.col(dfn.REGISTRO) == "E210")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "E210")
    except Exception:
        renamed = raw

    desired = [
        dfn.PERIODO, dfn.CNPJ,
        dfn.ID_SPED, dfn.ID_PAI,
        "IND_MOV_ST", "VL_SLD_CRED_ANT_ST", "VL_DEVOL_ST", "VL_RESSARC_ST",
        "VL_OUT_CRED_ST", "VL_AJ_CREDITOS_ST", "VL_RETENCAO_ST",
        "VL_OUT_DEB_ST", "VL_AJ_DEBITOS_ST", "VL_SLD_DEVEDOR_ANT_ST",
        "VL_DEDUÇÕES_ST", "VL_ICMS_RECOL_ST", "VL_SLD_CRED_ST_TRANSP",
        "DEB_ESP_ST",
    ]
    result = _safe_select(renamed, desired)
    result = _to_float(result, [
        "VL_SLD_CRED_ANT_ST", "VL_DEVOL_ST", "VL_RESSARC_ST",
        "VL_OUT_CRED_ST", "VL_AJ_CREDITOS_ST", "VL_RETENCAO_ST",
        "VL_OUT_DEB_ST", "VL_AJ_DEBITOS_ST", "VL_SLD_DEVEDOR_ANT_ST",
        "VL_DEDUÇÕES_ST", "VL_ICMS_RECOL_ST", "VL_SLD_CRED_ST_TRANSP",
        "DEB_ESP_ST",
    ])
    return _cast_id_to_str(result)


def extrair_e520_fiscal(
    df_fiscal: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extrai E520 (apuração IPI) do EFD ICMS/IPI.

    Nota: IPI não tem correspondente no EFD Contribuições.
    """
    if df_fiscal.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_fiscal.filter(pl.col(dfn.REGISTRO) == "E520")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "E520")
    except Exception:
        renamed = raw

    desired = [
        dfn.PERIODO, dfn.CNPJ,
        dfn.ID_SPED, dfn.ID_PAI,
        "VL_SD_ANT_IPI", "VL_DEBITOS_IPI", "VL_OUTROS_DEB_IPI",
        "VL_AJ_DEBITOS_IPI", "VL_CREDITOS_IPI", "VL_OUTROS_CRED_IPI",
        "VL_AJ_CREDITOS_IPI", "VL_SD_IPI",
    ]
    result = _safe_select(renamed, desired)
    result = _to_float(result, [
        "VL_SD_ANT_IPI", "VL_DEBITOS_IPI", "VL_OUTROS_DEB_IPI",
        "VL_AJ_DEBITOS_IPI", "VL_CREDITOS_IPI", "VL_OUTROS_CRED_IPI",
        "VL_AJ_CREDITOS_IPI", "VL_SD_IPI",
    ])
    return _cast_id_to_str(result)
