from app.schemas.models import ExecutiveSummary, ExtractedClause
from app.pipeline.risk import ClauseRisk
from app.llm.prompts import SUMMARY_PROMPT


def generate_summary(clauses: list[ExtractedClause], risks: list[ClauseRisk],
                     llm) -> ExecutiveSummary:
    risk_by_type = {r.clause_type: r for r in risks}
    lines = []
    for c in clauses:
        if not c.present:
            lines.append(f"- {c.type.value}: NOT PRESENT")
            continue
        r = risk_by_type.get(c.type.value)
        score = r.score if r else "n/a"
        lines.append(f"- {c.type.value} (risk {score}): {c.text[:300]}")
    findings = "\n".join(lines)
    prompt = SUMMARY_PROMPT.format(findings=findings)
    return llm.generate_structured(ExecutiveSummary, prompt)
