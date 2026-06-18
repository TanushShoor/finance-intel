from app.pipeline.runner import run_pipeline
from app.schemas.models import (StructuredDocument, ClauseExtractionResult, ExtractedClause,
                                 DeviationResult, RiskComponent, ExecutiveSummary)
from app.clause_types import ClauseType, ALL_CLAUSE_TYPES


def test_run_pipeline_produces_full_analysis(mock_llm, tmp_path):
    mock_llm.queue_response(StructuredDocument(title="MSA", nodes=[]))
    mock_llm.queue_response(ClauseExtractionResult(clauses=[
        ExtractedClause(type=t, present=True, text=f"{t.value} text",
                        location="1", confidence=0.9) for t in ALL_CLAUSE_TYPES]))
    for _ in ALL_CLAUSE_TYPES:
        mock_llm.queue_response(DeviationResult(classification="standard",
                                rationale="ok", baseline_ref="x"))
    for _ in ALL_CLAUSE_TYPES:
        mock_llm.queue_response(RiskComponent(category="legal", severity=20, rationale="low"))
    mock_llm.queue_response(ExecutiveSummary(coverage="c", who_carries_risk="w",
                            key_commercial_terms=["t"], top_issues=["a", "b", "c"]))

    fixture = tmp_path / "c.docx"
    import docx as pydocx
    d = pydocx.Document(); d.add_paragraph("Some contract text long enough to parse."); d.save(fixture)

    analysis = run_pipeline(str(fixture), llm=mock_llm)
    assert len(analysis.clauses) == 7
    assert len(analysis.deviations) == 7
    assert analysis.overall_risk_score >= 0
    assert len(analysis.summary.top_issues) == 3
