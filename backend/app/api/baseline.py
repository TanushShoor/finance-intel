from fastapi import APIRouter
from app.baseline.loader import load_baseline, save_baseline

router = APIRouter(prefix="/baseline", tags=["baseline"])


@router.get("")
def get_baseline():
    return load_baseline()


@router.put("")
def put_baseline(data: dict[str, str]):
    save_baseline(data)
    return {"status": "ok", "count": len(data)}
