"""
classificador_llm.py
====================
Classifies SPED items (Uso & Consumo) using the Gemini API.

Responsibilities:
  - Batch items for efficiency (avoids one API call per item).
  - Return elegivel / revisao / nao_elegivel + justificativa for each item.
  - Fall back to CST-based rules when the LLM is unavailable or fails.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Optional

import polars as pl

import cruzamento.cruzamento_definition as cd

logger = logging.getLogger(__name__)

# ── Labels ────────────────────────────────────────────────────────────────────
ELEGIVEL     = cd.ELEG_ELEGIVEL       # "elegivel"
REVISAO      = cd.ELEG_REVISAO        # "revisao"
NAO_ELEGIVEL = cd.ELEG_NAO_ELEGIVEL   # "nao_elegivel"

# ── Prompt ────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
Você é um especialista em tributação PIS/COFINS no regime de Lucro Real (não-cumulatividade).
Sua tarefa é classificar itens de notas fiscais de ENTRADA quanto ao direito de crédito de
PIS/COFINS por Uso & Consumo, conforme os artigos 3º da Lei 10.637/2002 e 10.833/2003.

Regras de classificação:
- ELEGÍVEL   → item claramente é insumo ou bem de uso e consumo que gera crédito de PIS/COFINS
               (ex: materiais de limpeza/consumo industrial, EPI, ferramentas de desgaste rápido,
               combustível de processo produtivo, peças de manutenção de ativos produtivos).
- REVISÃO    → item ambíguo ou que pode gerar crédito dependendo da atividade da empresa
               (ex: material de escritório administrativo, bens de uso misto, itens sem descrição clara).
- NÃO ELEGÍVEL → item claramente não gera crédito de PIS/COFINS
               (ex: refeições, lanches, passagens aéreas, despesas pessoais, combustível para veículos
               administrativos, bens do ativo imobilizado).

Para cada item, responda em JSON com os campos:
  "label": "elegivel" | "revisao" | "nao_elegivel"
  "obs":   texto curto (max 120 chars) explicando o motivo

Responda SOMENTE com um array JSON válido, sem markdown, com um objeto por item,
na mesma ordem recebida. Exemplo de formato:
[
  {"label": "elegivel", "obs": "Material de limpeza — consumo do processo produtivo"},
  {"label": "nao_elegivel", "obs": "Refeição — despesa pessoal sem direito a crédito"}
]
"""

USER_ITEM_TEMPLATE = "{idx}. CFOP={cfop} | COD={cod} | DESCR={descr}"


# ── CST-based fallback ─────────────────────────────────────────────────────────
_CST_ELEGIVEL     = {"50", "51", "52", "53", "54", "55", "56", "60", "61", "62", "63", "64", "65", "66"}
_CST_NAO_ELEGIVEL = {"70", "71", "72", "73", "74", "75", "98", "99"}


def _fallback_row(cst_pis: Optional[str], cst_cofins: Optional[str]) -> tuple[str, str]:
    """CST-based rule used when the LLM is unavailable."""
    cst = str(cst_pis or cst_cofins or "").strip()
    if cst in _CST_ELEGIVEL:
        return ELEGIVEL, "Classificação automática por CST (LLM indisponível)"
    if cst in _CST_NAO_ELEGIVEL:
        return NAO_ELEGIVEL, "Classificação automática por CST (LLM indisponível)"
    return REVISAO, "CST não identificado — requer revisão manual"


# ── Gemini client ─────────────────────────────────────────────────────────────
def _get_gemini_client(api_key: str, model_name: str):
    """Imports google-generativeai and returns a configured GenerativeModel."""
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError:
        raise ImportError(
            "Pacote 'google-generativeai' não instalado. "
            "Execute: pip install google-generativeai"
        )
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=model_name,
        generation_config=genai.GenerationConfig(
            temperature=0.1,       # low temperature → deterministic classification
            max_output_tokens=4096,
        ),
    )


# ── Batch call ────────────────────────────────────────────────────────────────
def _call_gemini_batch(model, items: list[dict]) -> list[dict]:
    """
    Sends one batch of items to Gemini and parses the JSON array response.
    items: list of {cfop, cod, descr, cst_pis, cst_cofins}
    Returns: list of {label, obs} (same length as items)
    """
    lines = [
        USER_ITEM_TEMPLATE.format(
            idx=i + 1,
            cfop=it.get("cfop") or "",
            cod=it.get("cod") or "",
            descr=(it.get("descr") or "")[:200],
        )
        for i, it in enumerate(items)
    ]
    user_msg = "\n".join(lines)

    try:
        response = model.generate_content(
            contents=[
                {"role": "user", "parts": [SYSTEM_PROMPT + "\n\n" + user_msg]}
            ]
        )
        raw = response.text.strip()

        # Strip optional markdown fences
        raw = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.IGNORECASE)
        raw = re.sub(r"\n?```$", "", raw)

        parsed: list[dict] = json.loads(raw)
        if len(parsed) != len(items):
            raise ValueError(
                f"Gemini retornou {len(parsed)} resultados para {len(items)} itens."
            )
        # Normalize labels
        for entry in parsed:
            lbl = str(entry.get("label", "")).lower().strip()
            if lbl not in {ELEGIVEL, REVISAO, NAO_ELEGIVEL}:
                entry["label"] = REVISAO
                entry["obs"]   = entry.get("obs", "") + " [label normalizado]"
            else:
                entry["label"] = lbl
        return parsed

    except Exception as exc:
        logger.warning(f"[U&C/LLM] Erro no batch Gemini: {exc!r}. Usando CST fallback.")
        return [
            {"label": REVISAO, "obs": f"Erro LLM — fallback: {str(exc)[:80]}"}
            for _ in items
        ]


# ── Public API ────────────────────────────────────────────────────────────────
def classificar_itens(
    df: pl.DataFrame,
    api_key: str,
    model_name: str = "gemini-2.0-flash",
    batch_size: int = 50,
) -> pl.DataFrame:
    """
    Adds / overwrites ELEGIBILIDADE and OBSERVACOES columns using Gemini LLM classification.

    Required input columns: CFOP (or cd.CFOP_UC), COD_ITEM, DESCR_COMPL
    Optional for fallback:  CST_PIS, CST_COFINS

    Processes items in batches of `batch_size` to minimise API calls.
    Falls back gracefully to CST rules if Gemini is unavailable.
    """
    if df.is_empty():
        return df

    # Resolve column names
    cfop_col  = cd.CFOP_UC if cd.CFOP_UC in df.columns else ("CFOP" if "CFOP" in df.columns else None)
    cod_col   = "COD_ITEM"     if "COD_ITEM"     in df.columns else None
    descr_col = "DESCR_COMPL"  if "DESCR_COMPL"  in df.columns else None
    cst_pis   = cd.CST_PIS     if cd.CST_PIS     in df.columns else None
    cst_cofins= cd.CST_COFINS  if cd.CST_COFINS  in df.columns else None

    if not api_key:
        logger.warning(
            "[U&C/LLM] gemini_api_key não fornecida — usando classificação por CST."
        )
        return _apply_fallback(df, cst_pis, cst_cofins)

    try:
        model = _get_gemini_client(api_key, model_name)
    except ImportError as exc:
        logger.warning(f"[U&C/LLM] {exc} — usando classificação por CST.")
        return _apply_fallback(df, cst_pis, cst_cofins)

    rows = df.to_dicts()
    labels  = []
    observs = []

    n_batches = (len(rows) + batch_size - 1) // batch_size
    logger.info(
        f"[U&C/LLM] Classificando {len(rows)} itens em {n_batches} batch(es) "
        f"(batch_size={batch_size}, model={model_name})."
    )

    for batch_idx in range(n_batches):
        chunk = rows[batch_idx * batch_size : (batch_idx + 1) * batch_size]

        items_payload = [
            {
                "cfop":      row.get(cfop_col)   if cfop_col  else None,
                "cod":       row.get(cod_col)    if cod_col   else None,
                "descr":     row.get(descr_col)  if descr_col else None,
                "cst_pis":   row.get(cst_pis)    if cst_pis   else None,
                "cst_cofins":row.get(cst_cofins) if cst_cofins else None,
            }
            for row in chunk
        ]

        t0 = time.perf_counter()
        results = _call_gemini_batch(model, items_payload)
        elapsed = time.perf_counter() - t0

        logger.info(
            f"[U&C/LLM] Batch {batch_idx + 1}/{n_batches} — "
            f"{len(chunk)} itens em {elapsed:.2f}s."
        )

        for res, src_row in zip(results, chunk):
            # If LLM returned an error label but CST is available, use CST
            if res["label"] == REVISAO and "Erro LLM" in res.get("obs", ""):
                cst_p = src_row.get(cst_pis)   if cst_pis   else None
                cst_c = src_row.get(cst_cofins) if cst_cofins else None
                fb_label, fb_obs = _fallback_row(cst_p, cst_c)
                labels.append(fb_label)
                observs.append(fb_obs)
            else:
                labels.append(res["label"])
                observs.append(res.get("obs", ""))

        # Polite rate-limit pause (Gemini Flash: 60 req/min)
        if batch_idx < n_batches - 1:
            time.sleep(0.5)

    return df.with_columns([
        pl.Series(name=cd.ELEGIBILIDADE, values=labels),
        pl.Series(name=cd.OBSERVACOES,   values=observs),
    ])


def _apply_fallback(
    df: pl.DataFrame,
    cst_pis_col: Optional[str],
    cst_cofins_col: Optional[str],
) -> pl.DataFrame:
    """Applies CST-based eligibility rules without LLM."""
    rows = df.to_dicts()
    labels, observs = [], []
    for row in rows:
        cst_p = row.get(cst_pis_col)   if cst_pis_col   else None
        cst_c = row.get(cst_cofins_col) if cst_cofins_col else None
        lbl, obs = _fallback_row(cst_p, cst_c)
        labels.append(lbl)
        observs.append(obs)
    return df.with_columns([
        pl.Series(name=cd.ELEGIBILIDADE, values=labels),
        pl.Series(name=cd.OBSERVACOES,   values=observs),
    ])
