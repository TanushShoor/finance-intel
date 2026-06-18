from app.pipeline.summary import generate_summary
from app.pipeline.risk import ClauseRisk
from app.schemas.models import ExecutiveSummary, ExtractedClause
from app.clause_types import ClauseType


def test_generate_summary_passes_findings_and_returns_top3(mock_llm):
    mock_llm.queue_response(ExecutiveSummary(
        coverage="A services agreement.",
        who_carries_risk="The customer carries more risk.",
        key_commercial_terms=["Net 30", "12-month cap"],
        top_issues=["Uncapped indemnity", "Auto-renewal", "Unilateral termination"]))
    clauses = [ExtractedClause(type=ClauseType.INDEMNITY, present=True, text="...",
                               location="8", confidence=0.9)]
    risks = [ClauseRisk(clause_type="indemnity", category="legal", score=90, rationale="x")]
    out = generate_summary(clauses, risks, llm=mock_llm)
    assert len(out.top_issues) == 3
    assert "indemnity" in mock_llm.calls[0]["prompt"].lower()
