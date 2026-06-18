from app.pipeline.batch import build_batch_comparison
from app.schemas.models import BatchComparison
from app.clause_types import ClauseType


def test_build_batch_comparison_assembles_cells(mock_llm):
    mock_llm.queue_response(BatchComparison(clause_type=ClauseType.GOVERNING_LAW, cells=[],
        differences=["A: England", "B: New York", "C: Singapore"]))
    stored = [
        {"id": 1, "name": "A", "analysis": {"clauses": [
            {"type": "governing_law", "present": True, "text": "England and Wales"}],
            "deviations": [], "risks": []}},
        {"id": 2, "name": "B", "analysis": {"clauses": [
            {"type": "governing_law", "present": True, "text": "New York"}],
            "deviations": [], "risks": []}},
    ]
    out = build_batch_comparison(stored, ClauseType.GOVERNING_LAW, llm=mock_llm)
    assert len(out.cells) == 2
    assert out.cells[0].text == "England and Wales"
    assert len(out.differences) == 3


def test_compare_endpoint_rejects_unanalyzed(tmp_path, monkeypatch):
    import app.api.compare as compare_mod
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.db.engine import init_db, make_engine
    from app.db.models import Contract
    from sqlmodel import Session

    engine = init_db(make_engine(f"sqlite:///{tmp_path/'t.db'}"))
    with Session(engine) as s:
        c = Contract(filename="x.docx", file_path="/tmp/x", format="docx", status="uploaded")
        s.add(c); s.commit(); s.refresh(c)
        cid = c.id

    client = TestClient(create_app())
    r = client.post("/compare", json={"contract_ids": [cid], "clause_type": "governing_law"})
    assert r.status_code == 400  # contract not analyzed
