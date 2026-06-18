from app.pipeline.risk import score_clause, aggregate_risk, ClauseRisk
from app.schemas.models import ExtractedClause, DeviationResult, RiskComponent
from app.clause_types import ClauseType


def test_score_clause_combines_llm_component(mock_llm):
    mock_llm.queue_response(RiskComponent(category="legal", severity=80,
                            rationale="Uncapped liability."))
    clause = ExtractedClause(type=ClauseType.LIMITATION_OF_LIABILITY, present=True,
                             text="Uncapped.", location="9", confidence=0.9)
    dev = DeviationResult(classification="unfavourable", rationale="No cap.",
                          baseline_ref="limitation_of_liability")
    cr = score_clause(clause, dev, llm=mock_llm)
    assert cr.category == "legal"
    assert cr.score == 100


def test_aggregate_uses_weighted_top_scores():
    risks = [
        ClauseRisk(clause_type="indemnity", category="legal", score=90, rationale="x"),
        ClauseRisk(clause_type="payment_terms", category="financial", score=40, rationale="y"),
    ]
    overall, breakdown = aggregate_risk(risks)
    assert breakdown["legal"] == 90
    assert breakdown["financial"] == 40
    assert 40 <= overall <= 90
    assert overall > 65
