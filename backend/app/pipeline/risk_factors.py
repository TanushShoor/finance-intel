"""Risk-factor extraction and cross-period comparison (success metric #3).

`extract_risk_factors` maps over the document; `compare_risk_factors` diffs a prior
period's risks against the current period's and labels each new/escalated/unchanged
(plus any removed), matching by meaning rather than exact wording.
"""
from app.ingestion.chunking import chunk_text
from app.schemas.financial import RiskFactorSet, RiskComparison
from app.llm.prompts import RISK_FACTORS_PROMPT, RISK_COMPARE_PROMPT


def _dedupe(risks):
    seen = set()
    out = []
    for r in risks:
        # The model frequently fills `text` but leaves `title` blank; backfill so
        # the risk isn't dropped and the UI has a label.
        if not r.title and r.text:
            r.title = r.text.strip()[:80]
        key = (r.title or r.text).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def extract_risk_factors(text, llm):
    out = []
    for chunk in chunk_text(text):
        try:
            res: RiskFactorSet = llm.generate_structured(
                RiskFactorSet, RISK_FACTORS_PROMPT.format(text=chunk))
        except Exception:  # noqa: BLE001
            continue
        out.extend(res.risk_factors)
    return _dedupe(out)


def _format(risks):
    return "\n".join(f"- [{r.category}] {r.title}: {r.text[:200]}" for r in risks) or "(none)"


def compare_risk_factors(prior, current, llm) -> RiskComparison:
    return llm.generate_structured(
        RiskComparison,
        RISK_COMPARE_PROMPT.format(prior=_format(prior), current=_format(current)))
