from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.db.engine import get_session
from app.db.models import Contract
from app.clause_types import ClauseType
from app.pipeline.batch import build_batch_comparison
from app.api.contracts import get_llm

router = APIRouter(prefix="/compare", tags=["compare"])


class CompareRequest(BaseModel):
    contract_ids: list[int]
    clause_type: ClauseType


@router.post("")
def compare(req: CompareRequest, session: Session = Depends(get_session)):
    stored = []
    for cid in req.contract_ids:
        c = session.get(Contract, cid)
        if not c or c.status != "done":
            raise HTTPException(400, f"contract {cid} not analyzed")
        stored.append({"id": c.id, "name": c.filename, "analysis": c.analysis})
    result = build_batch_comparison(stored, req.clause_type, get_llm())
    return result.model_dump()
