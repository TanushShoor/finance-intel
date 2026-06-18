"""Financial metric extraction (success metric #1).

Maps over the document in chunks (high recall across the whole filing) and merges
the results, de-duplicating by (canonical name, period).
"""
from app.ingestion.chunking import chunk_text
from app.schemas.financial import MetricSet, CANONICAL_METRICS
from app.llm.prompts import METRICS_PROMPT


def _dedupe(metrics):
    seen = {}
    for m in metrics:
        key = (m.name, m.period)
        if key not in seen:
            seen[key] = m
    return list(seen.values())


def extract_metrics(text, llm):
    canon = ", ".join(CANONICAL_METRICS)
    out = []
    for chunk in chunk_text(text):
        try:
            res: MetricSet = llm.generate_structured(
                MetricSet, METRICS_PROMPT.format(canonical=canon, text=chunk))
        except Exception:  # noqa: BLE001 - one bad chunk shouldn't sink extraction
            continue
        out.extend(res.metrics)
    return _dedupe(out)
