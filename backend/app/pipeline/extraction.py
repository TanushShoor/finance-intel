from app.schemas.models import ClauseExtractionResult, ExtractedClause
from app.clause_types import ALL_CLAUSE_TYPES
from app.llm.prompts import EXTRACTION_PROMPT


def extract_clauses(text: str, llm) -> list[ExtractedClause]:
    types_str = ", ".join(t.value for t in ALL_CLAUSE_TYPES)
    prompt = EXTRACTION_PROMPT.format(clause_types=types_str, text=text)
    result: ClauseExtractionResult = llm.generate_structured(ClauseExtractionResult, prompt)

    found = {c.type: c for c in result.clauses}
    normalized = []
    for t in ALL_CLAUSE_TYPES:
        if t in found:
            normalized.append(found[t])
        else:
            normalized.append(ExtractedClause(type=t, present=False, text="",
                                              location=None, confidence=0.0))
    return normalized
