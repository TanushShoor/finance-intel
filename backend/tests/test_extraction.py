from app.clause_types import ClauseType, ALL_CLAUSE_TYPES


def test_seven_named_clause_types():
    assert len(ALL_CLAUSE_TYPES) == 7
    assert ClauseType.INDEMNITY in ALL_CLAUSE_TYPES
    assert ClauseType.LIMITATION_OF_LIABILITY.value == "limitation_of_liability"


from app.pipeline.extraction import extract_clauses
from app.schemas.models import ClauseExtractionResult, ExtractedClause


def test_extract_normalizes_to_all_seven_types(mock_llm):
    mock_llm.queue_response(ClauseExtractionResult(clauses=[
        ExtractedClause(type=ClauseType.INDEMNITY, present=True, text="...",
                        location="8", confidence=0.9),
        ExtractedClause(type=ClauseType.GOVERNING_LAW, present=True, text="...",
                        location="10", confidence=0.8),
    ]))
    result = extract_clauses("contract text", llm=mock_llm)
    assert len(result) == 7
    by_type = {c.type: c for c in result}
    assert all(t in by_type for t in ALL_CLAUSE_TYPES)
    assert by_type[ClauseType.TERMINATION].present is False
