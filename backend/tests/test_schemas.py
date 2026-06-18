from app.schemas.models import (
    ExtractedClause, ClauseExtractionResult, DeviationResult,
    RiskComponent, ExecutiveSummary, ClauseNode,
)
from app.clause_types import ClauseType


def test_extracted_clause_roundtrip():
    c = ExtractedClause(type=ClauseType.INDEMNITY, present=True,
                        text="The Supplier shall indemnify...",
                        location="Section 8.1", confidence=0.9)
    assert c.present and c.confidence == 0.9


def test_missing_clause_allows_empty_text():
    c = ExtractedClause(type=ClauseType.TERMINATION, present=False,
                        text="", location=None, confidence=0.0)
    assert c.present is False


def test_deviation_classification_enum():
    d = DeviationResult(classification="unfavourable", rationale="One-sided.",
                        baseline_ref="indemnity")
    assert d.classification == "unfavourable"
