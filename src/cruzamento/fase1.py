"""
fase1.py
────────
Ponto de entrada para o fluxo FASE 1: base completa de cruzamento
EFD ICMS/IPI x EFD Contribuicoes, sem filtros de elegibilidade.

Chama cruzamento_fase1.executar_fase1() e gera o Excel via write_excel.excel_fase1().
"""

import time
import datatricks.sped.conversor_sped as cv
import datatricks.sped.sped_definitions as dfn
import cruzamento.cruzamento_definition as cd
import cruzamento.cruzamento_fase1 as cf1
import cruzamento.empresa as em
import cruzamento.write_excel as we


def _get_versao(df) -> str | None:
    if df is None or df.is_empty() or dfn.VERSAO not in df.columns:
        return None
    val = df.select(dfn.VERSAO).item(0, 0)
    return str(val) if val is not None else None


def _build_resumo_info(
    empresa: str,
    cnpj: str,
    versao_f: str | None,
    versao_c: str | None,
    df_fiscal,
    df_contribuicoes,
    fase1_data: dict,
) -> dict:
    import polars as pl

    def _periodos_set(df) -> set:
        if df is None or df.is_empty() or dfn.PERIODO not in df.columns:
            return set()
        try:
            return set(df.select(pl.col(dfn.PERIODO).drop_nulls().unique()).to_series().cast(pl.Utf8).to_list())
        except Exception:
            return set()

    def _cnpjs(df) -> list:
        if df is None or df.is_empty() or cd.CNPJ not in df.columns:
            return []
        try:
            return sorted(df.select(pl.col(cd.CNPJ).drop_nulls().unique()).to_series().cast(pl.Utf8).to_list())
        except Exception:
            return []

    # Períodos por obrigação: EFD_F via resultado, EFD_C via DataFrame bruto
    periodos_f = _periodos_set(fase1_data.get("C170")) | _periodos_set(fase1_data.get("D190"))
    periodos_c = _periodos_set(df_contribuicoes)

    # Dict de cobertura por período: {periodo: {"f": bool, "c": bool}}
    todos_periodos = sorted(periodos_f | periodos_c)
    cobertura = {
        p: {"f": p in periodos_f, "c": p in periodos_c}
        for p in todos_periodos
    }

    cnpjs_f = _cnpjs(df_fiscal)
    cnpjs_c = _cnpjs(df_contribuicoes)

    return {
        "empresa":    empresa,
        "cnpj_f":     cnpjs_f[0] if cnpjs_f else cnpj,
        "cnpj_c":     cnpjs_c[0] if cnpjs_c else "",
        "versao_f":   versao_f,
        "versao_c":   versao_c,
        "tem_efdf":   versao_f is not None,
        "tem_efdc":   versao_c is not None,
        "cobertura":  cobertura,
        "cnpjs_f":    cnpjs_f,
        "cnpjs_c":    cnpjs_c,
    }


def process_fase1(inbound, df_contribuicoes, df_fiscal, self, projeto, path_env):
    t0 = time.perf_counter()
    self.logger.info("[FASE1] Iniciando processamento FASE 1.")

    df_assets_c = cv.get_remote_assets(dfn.EFDC.get(dfn.OBRIGACAO), path_env)
    df_assets_f = cv.get_remote_assets(dfn.EFDF.get(dfn.OBRIGACAO), path_env)
    versao_c = _get_versao(df_contribuicoes)
    versao_f = _get_versao(df_fiscal)

    self.logger.info(f"[FASE1] Versoes SPED — EFDC: {versao_c}  EFDF: {versao_f}")

    empresa, cnpj = em.empresa_cnpj(inbound, df_fiscal, df_contribuicoes)
    self.logger.info(f"[FASE1] Empresa: {empresa} | CNPJ: {cnpj}")

    fase1_data = cf1.executar_fase1(
        df_fiscal, df_assets_f, versao_f,
        df_contribuicoes, df_assets_c, versao_c,
    )

    sizes = {k: len(v) for k, v in fase1_data.items() if not v.is_empty()}
    self.logger.info(f"[FASE1] Registros extraidos: {sizes}")

    resumo_info = _build_resumo_info(
        empresa, cnpj, versao_f, versao_c,
        df_fiscal, df_contribuicoes, fase1_data,
    )

    we.excel_fase1(self, empresa, fase1_data, projeto, resumo_info)

    elapsed = round(time.perf_counter() - t0, 1)
    self.logger.info(f"[FASE1] Concluido em {elapsed}s.")
