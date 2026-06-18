import logging

from app.ingestion.router import parse_document
from app.ingestion.structure import structure_document
from app.pipeline.identity import identify_document
from app.pipeline.metrics import extract_metrics
from app.pipeline.tone import analyze_tone
from app.pipeline.risk_factors import extract_risk_factors
from app.pipeline.memo import generate_memo
from app.schemas.financial import (
    FinancialAnalysis, DocumentIdentity, ToneAnalysis, InvestmentMemo)

logger = logging.getLogger(__name__)


def _safe(fn, default, label):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001 - a single stage must not sink the whole run
        logger.warning("stage %s failed: %s", label, e)
        return default


def run_financial_analysis(file_path: str, llm, on_progress=None) -> FinancialAnalysis:
    parsed = parse_document(file_path)
    text = parsed.full_text

    # The structure stage streams per-chunk progress (drives the chunk animation).
    structure = structure_document(text, llm, on_progress=on_progress)

    def stage(name):
        if on_progress:
            on_progress(stage=name, current=0, total=0, preview="")

    stage("identifying")
    identity = _safe(lambda: identify_document(text, llm), DocumentIdentity(), "identity")
    stage("metrics")
    metrics = _safe(lambda: extract_metrics(text, llm), [], "metrics")
    stage("tone")
    tone = _safe(lambda: analyze_tone(text, llm), ToneAnalysis(), "tone")
    stage("risk_factors")
    risks = _safe(lambda: extract_risk_factors(text, llm), [], "risk_factors")
    stage("memo")
    memo = _safe(lambda: generate_memo(identity, metrics, tone, risks, llm),
                 InvestmentMemo(), "memo")

    return FinancialAnalysis(identity=identity, structure=structure, metrics=metrics,
                             tone=tone, risk_factors=risks, memo=memo)
