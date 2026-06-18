"""Competitor benchmarking (success metric #4).

The grid is assembled in code from each company's already-extracted metrics (keeps the
numbers faithful and avoids dict-valued LLM schemas); one LLM call adds comparative
commentary. Repurposes the old cross-document batch-compare slot.
"""
from app.schemas.financial import BenchmarkCommentary, CANONICAL_METRICS
from app.llm.prompts import BENCHMARK_PROMPT


def _company_metrics(analysis: dict) -> dict:
    """Latest value seen per canonical metric for one filing."""
    by = {}
    for m in (analysis or {}).get("metrics", []):
        name = m.get("name")
        if name and name not in by:
            by[name] = m.get("value")
    return by


def _format_grid(cols, rows) -> str:
    lines = ["Company | " + " | ".join(cols)]
    for r in rows:
        lines.append(r["company"] + " | "
                     + " | ".join(str(r["values"].get(c) or "-") for c in cols))
    return "\n".join(lines)


def build_benchmark(stored: list[dict], llm, metric_names=None) -> dict:
    metric_names = metric_names or CANONICAL_METRICS
    rows = []
    for item in stored:
        analysis = item.get("analysis") or {}
        identity = analysis.get("identity") or {}
        company = identity.get("company") or item.get("name")
        by = _company_metrics(analysis)
        rows.append({"company": company, "values": {mn: by.get(mn) for mn in metric_names}})

    # Drop columns no company reported, so the table isn't all blanks.
    cols = [mn for mn in metric_names if any(r["values"].get(mn) for r in rows)]
    rows = [{"company": r["company"], "values": {c: r["values"].get(c) for c in cols}}
            for r in rows]

    highlights = []
    if rows and cols:
        try:
            commentary: BenchmarkCommentary = llm.generate_structured(
                BenchmarkCommentary, BENCHMARK_PROMPT.format(grid=_format_grid(cols, rows)))
            highlights = commentary.highlights
        except Exception:  # noqa: BLE001 - table still useful without commentary
            highlights = []

    return {"metric_names": cols, "rows": rows, "highlights": highlights}
