from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.db.engine import get_session
from app.db.models import Contract
from app.pipeline.benchmark import build_benchmark
from app.pipeline.risk_factors import compare_risk_factors
from app.schemas.financial import RiskFactor
from app.api.contracts import get_llm

router = APIRouter(tags=["compare"])


class BenchmarkRequest(BaseModel):
    contract_ids: list[int]
    metric_names: list[str] | None = None


@router.post("/benchmark")
def benchmark(req: BenchmarkRequest, session: Session = Depends(get_session)):
    stored = []
    for cid in req.contract_ids:
        c = session.get(Contract, cid)
        if not c or c.status != "done":
            raise HTTPException(400, f"document {cid} not analyzed")
        stored.append({"id": c.id, "name": c.filename, "analysis": c.analysis})
    return build_benchmark(stored, get_llm(), metric_names=req.metric_names)


class RiskCompareRequest(BaseModel):
    prior_id: int
    current_id: int


def _risks(c: Contract) -> list[RiskFactor]:
    return [RiskFactor(**r) for r in (c.analysis or {}).get("risk_factors", [])]


@router.post("/compare/risk")
def compare_risk(req: RiskCompareRequest, session: Session = Depends(get_session)):
    prior = session.get(Contract, req.prior_id)
    current = session.get(Contract, req.current_id)
    for c in (prior, current):
        if not c or c.status != "done":
            raise HTTPException(400, "both documents must be analyzed")
    result = compare_risk_factors(_risks(prior), _risks(current), get_llm())
    return {
        "prior": {"id": prior.id, "name": prior.filename},
        "current": {"id": current.id, "name": current.filename},
        **result.model_dump(),
    }
