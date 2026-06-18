from typing import Optional
from app.schemas.models import ExtractedClause, DeviationResult
from app.llm.prompts import COMPARISON_PROMPT


def compare_clause(clause: ExtractedClause, baseline: dict[str, str],
                   llm) -> Optional[DeviationResult]:
    if not clause.present:
        return None
    prompt = COMPARISON_PROMPT.format(
        clause_type=clause.type.value,
        baseline=baseline.get(clause.type.value, "(no baseline defined)"),
        clause_text=clause.text)
    return llm.generate_structured(DeviationResult, prompt)
