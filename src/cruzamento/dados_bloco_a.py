"""
dados_bloco_a.py
────────────────
Extração do Bloco A (Documentos Fiscais de Serviços — ISS) do EFD Contribuições.

Registros extraídos:
  A100 — Cabeçalho da NF de Serviço
  A170 — Itens da NF de Serviço
"""

import polars as pl
import datatricks.sped.sped_definitions as dfn
import cruzamento.cruzamento_definition as cd
from cruzamento.dados_receita import rename_columns
from cruzamento.dados_oportunidades import _safe_select, _to_float, _cast_id_to_str


def extrair_a100_contribuicoes(
    df_contribuicoes: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extrai registros A100 (cabeçalho NF de serviço ISS) do EFD Contribuições.

    Colunas retornadas: ID_SPED, ID_PAI, COD_PART, COD_SIT, NUM_DOC, DT_DOC, VL_DOC
    """
    if df_contribuicoes.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_contribuicoes.filter(pl.col(dfn.REGISTRO) == "A100")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "A100")
    except Exception:
        renamed = raw

    desired = [
        dfn.ID_SPED, dfn.ID_PAI,
        "COD_PART", "COD_SIT", "NUM_DOC", "DT_DOC", "VL_DOC",
    ]
    result = _safe_select(renamed, desired)
    return _to_float(result, ["VL_DOC"])


def extrair_a170_contribuicoes(
    df_contribuicoes: pl.DataFrame,
    df_assets: pl.DataFrame,
    versao: str | None,
) -> pl.DataFrame:
    """
    Extrai registros A170 (itens NF de serviço ISS) do EFD Contribuições.

    rename_columns já propaga toda a hierarquia (A001 -> A100 -> A170), incluindo
    campos do documento pai (VL_BC_PIS, VL_DOC, etc.) e campos de item com sufixo
    '2' (VL_BC_PIS2, VL_PIS2, etc.) para distinguir os dois níveis.
    """
    if df_contribuicoes.is_empty() or versao is None:
        return pl.DataFrame()

    raw = df_contribuicoes.filter(pl.col(dfn.REGISTRO) == "A170")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "A170")
    except Exception:
        renamed = raw

    desired = [
        "Período", "Registro", "Quebra CNPJ", "ID-SPED", "ID-PAI", "ID-REG",
        "REG", "IND_MOV", "REG2", "CNPJ", "REG3",
        "IND_OPER", "IND_EMIT", cd.COD_PART,
        cd.COD_SIT, "SER", "SUB", "NUM_DOC", "CHV_NFSE",
        "DT_DOC", "DT_EXE_SERV", "VL_DOC", "IND_PGTO", "VL_DESC",
        "VL_BC_PIS", "VL_PIS", "VL_BC_COFINS", "VL_COFINS",
        "VL_PIS_RET", "VL_COFINS_RET", "VL_ISS",
        "REG4", "NUM_ITEM", "COD_ITEM", "DESCR_COMPL", "VL_ITEM", "VL_DESC2",
        "NAT_BC_CRED", "IND_ORIG_CRED",
        "CST_PIS", "VL_BC_PIS2", "ALIQ_PIS", "VL_PIS2",
        "CST_COFINS", "VL_BC_COFINS2", "ALIQ_COFINS", "VL_COFINS2",
        "COD_CTA", "COD_CCUS",
    ]
    result = _safe_select(renamed, desired)
    result = _to_float(result, [
        "VL_DOC", "VL_DESC",
        "VL_BC_PIS", "VL_PIS", "VL_BC_COFINS", "VL_COFINS",
        "VL_PIS_RET", "VL_COFINS_RET", "VL_ISS",
        "VL_ITEM", "VL_DESC2",
        "VL_BC_PIS2", "ALIQ_PIS", "VL_PIS2",
        "VL_BC_COFINS2", "ALIQ_COFINS", "VL_COFINS2",
    ])
    return _cast_id_to_str(result)
