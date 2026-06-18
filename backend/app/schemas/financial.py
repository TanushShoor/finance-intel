from typing import Optional, Literal
from pydantic import BaseModel, Field
from app.schemas.models import StructuredDocument

Sentiment = Literal["confident", "cautious", "neutral", "mixed"]
Hedging = Literal["low", "medium", "high"]
RiskStatus = Literal["new", "escalated", "unchanged", "removed"]

# Canonical metrics drive both extraction (the model maps reported labels onto these)
# and benchmarking (so "net revenue" and "total revenue" align in one column).
CANONICAL_METRICS = [
    "revenue",
    "gross_margin",
    "operating_income",
    "operating_margin",
    "net_income",
    "eps",
    "ebitda",
    "free_cash_flow",
    "capex",
    "total_debt",
    "cash_and_equivalents",
    "guidance_revenue",
]


class DocumentIdentity(BaseModel):
    company: Optional[str] = None
    period: Optional[str] = None          # "Q4 2024", "FY2024"
    doc_type: Optional[str] = None        # earnings release | 10-K | 10-Q | transcript | other


class Metric(BaseModel):
    name: str                             # canonical snake_case (see CANONICAL_METRICS)
    label: str = ""                       # as reported
    period: Optional[str] = None
    value: str = ""                       # as reported, e.g. "$14.3 billion", "39.2%"
    value_numeric: Optional[float] = None  # normalized to `unit` for comparison
    unit: Optional[str] = None            # "USD millions" | "%" | ...
    basis: Optional[str] = None           # "GAAP" | "non-GAAP"
    source: Optional[str] = None          # short quote, for grounding


class MetricSet(BaseModel):
    metrics: list[Metric] = Field(default_factory=list)


class TonePassage(BaseModel):
    text: str = ""
    sentiment: Sentiment = "neutral"
    confidence: int = Field(0, ge=0, le=100)
    hedging: Hedging = "medium"
    rationale: str = ""


class ToneAnalysis(BaseModel):
    overall_sentiment: Sentiment = "neutral"
    confidence_score: int = Field(0, ge=0, le=100)
    hedging_level: Hedging = "medium"
    summary: str = ""
    passages: list[TonePassage] = Field(default_factory=list)


class RiskFactor(BaseModel):
    category: str = ""
    title: str = ""
    text: str = ""
    severity: int = Field(0, ge=0, le=100)


class RiskFactorSet(BaseModel):
    risk_factors: list[RiskFactor] = Field(default_factory=list)


class RiskDelta(BaseModel):
    title: str = ""
    category: str = ""
    status: RiskStatus = "unchanged"
    rationale: str = ""


class RiskComparison(BaseModel):
    deltas: list[RiskDelta] = Field(default_factory=list)


class InvestmentMemo(BaseModel):
    company_overview: str = ""
    financial_summary: str = ""
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    key_risks: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


class BenchmarkCommentary(BaseModel):
    highlights: list[str] = Field(default_factory=list)


class FinancialAnalysis(BaseModel):
    identity: DocumentIdentity = Field(default_factory=DocumentIdentity)
    structure: StructuredDocument
    metrics: list[Metric] = Field(default_factory=list)
    tone: ToneAnalysis = Field(default_factory=ToneAnalysis)
    risk_factors: list[RiskFactor] = Field(default_factory=list)
    memo: InvestmentMemo = Field(default_factory=InvestmentMemo)
