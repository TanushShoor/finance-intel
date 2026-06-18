from pydantic import BaseModel
from app.ingestion.router import parse_document
from app.ingestion.structure import structure_document
from app.pipeline.extraction import extract_clauses
from app.pipeline.comparison import compare_clause
from app.pipeline.risk import score_clause, aggregate_risk, ClauseRisk
from app.pipeline.summary import generate_summary
from app.baseline.loader import load_baseline
from app.schemas.models import (StructuredDocument, ExtractedClause, DeviationResult,
                                 ExecutiveSummary)


class AnalysisResult(BaseModel):
    structure: StructuredDocument
    clauses: list[ExtractedClause]
    deviations: list[dict]   # {clause_type, classification, rationale} for present clauses
    risks: list[ClauseRisk]
    overall_risk_score: int
    category_breakdown: dict[str, int]
    summary: ExecutiveSummary


def run_pipeline(file_path: str, llm) -> AnalysisResult:
    parsed = parse_document(file_path)
    structure = structure_document(parsed.full_text, llm)
    clauses = extract_clauses(parsed.full_text, llm)

    baseline = load_baseline()
    deviations: list[dict] = []

    # Pass 1: run all comparisons
    dev_map: dict[int, DeviationResult | None] = {}
    for i, clause in enumerate(clauses):
        dev: DeviationResult | None = None
        if clause.present:
            try:
                dev = compare_clause(clause, baseline, llm)
            except Exception:
                dev = None
            if dev:
                deviations.append({"clause_type": clause.type.value,
                                   "classification": dev.classification,
                                   "rationale": dev.rationale})
        dev_map[i] = dev

    # Pass 2: run all risk scoring
    risks: list[ClauseRisk] = []
    for i, clause in enumerate(clauses):
        if clause.present:
            try:
                risks.append(score_clause(clause, dev_map[i], llm))
            except Exception:
                pass

    overall, breakdown = aggregate_risk(risks)
    summary = generate_summary(clauses, risks, llm)
    return AnalysisResult(structure=structure, clauses=clauses, deviations=deviations,
                          risks=risks, overall_risk_score=overall,
                          category_breakdown=breakdown, summary=summary)
