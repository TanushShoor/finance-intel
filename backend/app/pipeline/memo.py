"""Investment-memo generation (success metric #5).

Synthesizes a memo from the ALREADY-EXTRACTED findings (metrics, tone, risks) rather
than the raw document, so the bull/bear cases are grounded in extracted data.
"""
from app.schemas.financial import InvestmentMemo
from app.llm.prompts import MEMO_PROMPT


def _format_findings(identity, metrics, tone, risks) -> str:
    lines = []
    if identity:
        lines.append(f"Company: {identity.company or 'unknown'} | Period: "
                     f"{identity.period or 'n/a'} | Type: {identity.doc_type or 'n/a'}")
    lines.append("\nMETRICS:")
    for m in metrics:
        period = f" ({m.period})" if m.period else ""
        basis = f" [{m.basis}]" if m.basis else ""
        lines.append(f"- {m.name}{period}: {m.value}{basis}")
    if tone:
        lines.append(f"\nTONE: {tone.overall_sentiment} "
                     f"(confidence {tone.confidence_score}, hedging {tone.hedging_level}). "
                     f"{tone.summary}")
    lines.append("\nRISK FACTORS:")
    for r in risks:
        lines.append(f"- [{r.category}] {r.title} (severity {r.severity})")
    return "\n".join(lines)


def generate_memo(identity, metrics, tone, risks, llm) -> InvestmentMemo:
    findings = _format_findings(identity, metrics, tone, risks)
    return llm.generate_structured(InvestmentMemo, MEMO_PROMPT.format(findings=findings))
