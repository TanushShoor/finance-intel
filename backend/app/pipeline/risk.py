from typing import Optional
from pydantic import BaseModel
from app.schemas.models import ExtractedClause, DeviationResult, RiskComponent, RiskCategory
from app.llm.prompts import RISK_PROMPT

_DEVIATION_WEIGHT = {
    "favourable": 0.7,
    "standard": 1.0,
    "unusual": 1.15,
    "unfavourable": 1.25,
}


class ClauseRisk(BaseModel):
    clause_type: str
    category: RiskCategory
    score: int
    rationale: str


def score_clause(clause: ExtractedClause, deviation: Optional[DeviationResult],
                 llm) -> ClauseRisk:
    classification = deviation.classification if deviation else "standard"
    dev_rationale = deviation.rationale if deviation else "No deviation assessed."
    prompt = RISK_PROMPT.format(clause_type=clause.type.value,
                                classification=classification,
                                clause_text=clause.text,
                                deviation_rationale=dev_rationale)
    comp: RiskComponent = llm.generate_structured(RiskComponent, prompt)
    weighted = comp.severity * _DEVIATION_WEIGHT.get(classification, 1.0)
    score = max(0, min(100, round(weighted)))
    return ClauseRisk(clause_type=clause.type.value, category=comp.category,
                      score=score, rationale=comp.rationale)


def aggregate_risk(risks: list[ClauseRisk]) -> tuple[int, dict[str, int]]:
    """Overall = worst-biased weighted mean; breakdown = max score per category."""
    breakdown: dict[str, int] = {}
    for r in risks:
        breakdown[r.category] = max(breakdown.get(r.category, 0), r.score)
    if not risks:
        return 0, breakdown
    scores = sorted((r.score for r in risks), reverse=True)
    weights = [len(scores) - i for i in range(len(scores))]
    overall = round(sum(s * w for s, w in zip(scores, weights)) / sum(weights))
    return overall, breakdown
