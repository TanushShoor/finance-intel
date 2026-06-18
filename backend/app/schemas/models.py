from typing import Literal, Optional
from pydantic import BaseModel, Field
from app.clause_types import ClauseType

RiskCategory = Literal["financial", "operational", "legal", "reputational"]
Classification = Literal["favourable", "unfavourable", "unusual", "standard"]


# --- Ingestion / structure ---
class ClauseNode(BaseModel):
    number: Optional[str] = Field(None, description="e.g. '8.1' or '(a)'")
    heading: Optional[str] = None
    text: str = ""
    cross_references: list[str] = Field(default_factory=list)
    children: list["ClauseNode"] = Field(default_factory=list)


class StructuredDocument(BaseModel):
    title: Optional[str] = None
    nodes: list[ClauseNode] = Field(default_factory=list)


# --- Extraction ---
class ExtractedClause(BaseModel):
    type: ClauseType
    present: bool
    text: str = ""
    location: Optional[str] = None
    confidence: float = 0.0


class ClauseExtractionResult(BaseModel):
    clauses: list[ExtractedClause]


# --- Comparison ---
class DeviationResult(BaseModel):
    classification: Classification
    rationale: str
    baseline_ref: str


# --- Risk ---
class RiskComponent(BaseModel):
    category: RiskCategory
    severity: int = Field(ge=0, le=100)
    rationale: str


# --- Summary ---
class ExecutiveSummary(BaseModel):
    coverage: str
    who_carries_risk: str
    key_commercial_terms: list[str]
    top_issues: list[str] = Field(description="Top 3 issues to negotiate")


# --- Batch ---
class BatchCell(BaseModel):
    contract_id: int
    contract_name: str
    present: bool
    text: str = ""
    classification: Optional[Classification] = None
    risk_score: Optional[int] = None


class BatchComparison(BaseModel):
    clause_type: ClauseType
    cells: list[BatchCell]
    differences: list[str]


ClauseNode.model_rebuild()
