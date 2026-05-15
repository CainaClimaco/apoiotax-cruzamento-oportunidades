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
    Extrai registros A170 (itens NF de serviço ISS) do EFD Contribuições,
    enriquecidos com campos do A100 pai via forward-fill.

    Colunas retornadas:
      ID_SPED, ID_PAI, NUM_ITEM, COD_ITEM, DESCR_SERV, VL_ITEM,
      CST_PIS, CST_COFINS, ALIQ_PIS, ALIQ_COFINS, VL_BC_PIS, VL_BC_COFINS,
      VL_PIS, VL_COFINS, NATBC_CRED, IND_ORIG_CRED,
      COD_PART, COD_SIT, NUM_DOC, DT_DOC (forward-filled do A100)
    """
    if df_contribuicoes.is_empty() or versao is None:
        return pl.DataFrame()

    ff_cols = [c for c in [cd.COD_PART, cd.COD_SIT, "NUM_DOC", "DT_DOC"] if c in df_contribuicoes.columns]
    if ff_cols:
        periodo_col = dfn.PERIODO if dfn.PERIODO in df_contribuicoes.columns else "Periodo"
        df_enriched = df_contribuicoes.sort(dfn.ID_SPED).with_columns([
            pl.col(c).forward_fill().over(periodo_col).alias(c)
            for c in ff_cols
        ])
    else:
        df_enriched = df_contribuicoes

    raw = df_enriched.filter(pl.col(dfn.REGISTRO) == "A170")
    if raw.is_empty():
        return pl.DataFrame()

    try:
        renamed = rename_columns(raw, df_assets, versao, "A170")
    except Exception:
        renamed = raw

    desired = [
        dfn.PERIODO, dfn.CNPJ,
        dfn.ID_SPED, dfn.ID_PAI,
        "NUM_ITEM", "COD_ITEM", "DESCR_SERV",
        "VL_ITEM",
        "CST_PIS", "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        "CST_COFINS", "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
        "NATBC_CRED", "IND_ORIG_CRED",
        cd.COD_PART, cd.COD_SIT, "NUM_DOC", "DT_DOC",
    ]
    result = _safe_select(renamed, desired)
    result = _to_float(result, [
        "VL_ITEM",
        "VL_BC_PIS", "ALIQ_PIS", "VL_PIS",
        "VL_BC_COFINS", "ALIQ_COFINS", "VL_COFINS",
    ])
    return _cast_id_to_str(result)
