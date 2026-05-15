"""
dados_bloco_f.py
────────────────
Extração do Bloco F (Demais Operações) do EFD Contribuições.

Esses registros NÃO têm correspondente no EFD ICMS/IPI — são exclusivos do EFD_C.

Registros extraídos:
  F100 — Receitas e despesas diversas (aluguel, serviços financeiros, royalties, etc.)
  F130 — Aquisições de ativo imobilizado
"""

import polars as pl
import datatricks.sped.sped_definitions as dfn
from cruzamento.dados_receita import rename_columns
from cruzamento.dados_oportunidades import _safe_select, _to_float, _cast_id_to_str


def extrair_f100_contribuicoes(
    df_contribuicoes: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extrai F100 (receitas/despesas diversas) do EFD Contribuições.
    Exclusivo do EFD_C — sem correspondente no EFD ICMS/IPI.

    Colunas retornadas:
      ID_SPED, IND_OPER, COD_PART, DT_OPER, VL_OPER,
      CST_PIS, CST_COFINS, VL_BC_PIS, VL_BC_COFINS,
      ALIQ_PIS, ALIQ_COFINS, VL_PIS, VL_COFINS, DESCR_DOC_OPER
    """
    if df_contribuicoes.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_contribuicoes.filter(pl.col(dfn.REGISTRO) == "F100")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "F100")
    except Exception:
        renamed = raw

    desired = [
        dfn.PERIODO, dfn.CNPJ,
        dfn.ID_SPED, dfn.ID_PAI,
        "IND_OPER", "COD_PART", "DT_OPER", "VL_OPER",
        "CST_PIS", "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        "CST_COFINS", "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
        "DESCR_DOC_OPER",
    ]
    result = _safe_select(renamed, desired)
    result = _to_float(result, [
        "VL_OPER",
        "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
    ])
    return _cast_id_to_str(result)


def extrair_f130_contribuicoes(
    df_contribuicoes: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extrai F130 (aquisições de ativo imobilizado) do EFD Contribuições.
    Exclusivo do EFD_C — sem correspondente no EFD ICMS/IPI.

    Colunas retornadas:
      ID_SPED, COD_PART, DT_OPER, VL_OPER,
      CST_PIS, CST_COFINS, VL_BC_PIS, VL_BC_COFINS,
      ALIQ_PIS, ALIQ_COFINS, VL_PIS, VL_COFINS,
      IND_ORIG_CRED, DESCR_BEM
    """
    if df_contribuicoes.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_contribuicoes.filter(pl.col(dfn.REGISTRO) == "F130")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "F130")
    except Exception:
        renamed = raw

    desired = [
        dfn.PERIODO, dfn.CNPJ,
        dfn.ID_SPED, dfn.ID_PAI,
        "COD_PART", "DT_OPER", "VL_OPER",
        "CST_PIS", "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        "CST_COFINS", "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
        "IND_ORIG_CRED", "DESCR_BEM",
    ]
    result = _safe_select(renamed, desired)
    result = _to_float(result, [
        "VL_OPER",
        "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
    ])
    return _cast_id_to_str(result)
