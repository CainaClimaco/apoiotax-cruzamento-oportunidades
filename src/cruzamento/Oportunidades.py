"""
Oportunidades.py
────────────────
Ponto de entrada para o fluxo Oportunidades: base completa de cruzamento
EFD ICMS/IPI x EFD Contribuicoes, sem filtros de elegibilidade.

Chama cruzamento_oportunidades.executar_oportunidades() e gera o Excel via
write_excel.excel_oportunidades().
"""

import time
import datatricks.sped.conversor_sped as cv
import datatricks.sped.sped_definitions as dfn
import cruzamento.cruzamento_definition as cd
import cruzamento.cruzamento_oportunidades as co
import cruzamento.empresa as em
import cruzamento.write_excel as we


def _get_versao(df) -> str | None:
    if df is None or df.is_empty() or dfn.VERSAO not in df.columns:
        return None
    val = df.select(dfn.VERSAO).item(0, 0)
    return str(val) if val is not None else None


def _raiz_cnpj(cnpj: str) -> str:
    digits = "".join(c for c in cnpj if c.isdigit())
    return digits[:8] if len(digits) >= 8 else digits


def _build_resumo_info(
    empresa: str,
    cnpj: str,
    versao_f: str | None,
    versao_c: str | None,
    df_fiscal,
    df_contribuicoes,
    oportunidades_data: dict,
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

    periodos_f = _periodos_set(oportunidades_data.get("C170")) | _periodos_set(oportunidades_data.get("D190"))
    periodos_c = _periodos_set(df_contribuicoes)

    todos_periodos = sorted(periodos_f | periodos_c)
    cobertura = {
        p: {"f": p in periodos_f, "c": p in periodos_c}
        for p in todos_periodos
    }

    cnpjs_f = _cnpjs(df_fiscal)
    cnpjs_c = _cnpjs(df_contribuicoes)

    raizes_f = sorted({_raiz_cnpj(c) for c in cnpjs_f if c})
    raizes_c = sorted({_raiz_cnpj(c) for c in cnpjs_c if c})
    raiz_ok  = bool(raizes_f) and bool(raizes_c) and set(raizes_f).issubset(set(raizes_c))

    contagens: dict = {}
    c170 = oportunidades_data.get("C170")
    if c170 is not None and not c170.is_empty() and dfn.PERIODO in c170.columns:
        for periodo in todos_periodos:
            sub = c170.filter(pl.col(dfn.PERIODO).cast(pl.Utf8) == periodo)
            n_f = sub.height
            n_c = sub.filter(pl.col(cd.EM_EFD_C) == "Encontrado").height if cd.EM_EFD_C in sub.columns else 0
            contagens[periodo] = {"n_f": n_f, "n_c": n_c}

    return {
        "empresa":    empresa,
        "versao_f":   versao_f,
        "versao_c":   versao_c,
        "cobertura":  cobertura,
        "cnpjs_f":    cnpjs_f,
        "cnpjs_c":    cnpjs_c,
        "raizes_f":   raizes_f,
        "raizes_c":   raizes_c,
        "raiz_ok":    raiz_ok,
        "contagens":  contagens,
    }


def process_oportunidades(inbound, df_contribuicoes, df_fiscal, self, projeto, path_env):
    t0 = time.perf_counter()
    self.logger.info("[OPORTUNIDADES] Iniciando processamento.")

    df_assets_c = cv.get_remote_assets(dfn.EFDC.get(dfn.OBRIGACAO), path_env)
    df_assets_f = cv.get_remote_assets(dfn.EFDF.get(dfn.OBRIGACAO), path_env)
    versao_c = _get_versao(df_contribuicoes)
    versao_f = _get_versao(df_fiscal)

    self.logger.info(f"[OPORTUNIDADES] Versoes SPED — EFDC: {versao_c}  EFDF: {versao_f}")

    empresa, cnpj = em.empresa_cnpj(inbound, df_fiscal, df_contribuicoes)
    self.logger.info(f"[OPORTUNIDADES] Empresa: {empresa} | CNPJ: {cnpj}")

    oportunidades_data = co.executar_oportunidades(
        df_fiscal, df_assets_f, versao_f,
        df_contribuicoes, df_assets_c, versao_c,
    )

    sizes = {k: len(v) for k, v in oportunidades_data.items() if not v.is_empty()}
    self.logger.info(f"[OPORTUNIDADES] Registros extraidos: {sizes}")

    resumo_info = _build_resumo_info(
        empresa, cnpj, versao_f, versao_c,
        df_fiscal, df_contribuicoes, oportunidades_data,
    )

    we.excel_oportunidades(self, empresa, oportunidades_data, projeto, resumo_info)

    elapsed = round(time.perf_counter() - t0, 1)
    self.logger.info(f"[OPORTUNIDADES] Concluido em {elapsed}s.")
