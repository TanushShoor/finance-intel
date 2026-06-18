from app.pipeline.comparison import compare_clause
from app.schemas.models import ExtractedClause, DeviationResult
from app.clause_types import ClauseType


def test_compare_present_clause_calls_llm(mock_llm):
    mock_llm.queue_response(DeviationResult(classification="unfavourable",
                            rationale="One-sided.", baseline_ref="indemnity"))
    clause = ExtractedClause(type=ClauseType.INDEMNITY, present=True,
                             text="Customer indemnifies everything.", location="8", confidence=0.9)
    out = compare_clause(clause, {"indemnity": "Mutual..."}, llm=mock_llm)
    assert out.classification == "unfavourable"


def test_compare_absent_clause_skips_llm(mock_llm):
    clause = ExtractedClause(type=ClauseType.TERMINATION, present=False, text="",
                             location=None, confidence=0.0)
    out = compare_clause(clause, {"termination": "..."}, llm=mock_llm)
    assert out is None
    assert mock_llm.calls == []
