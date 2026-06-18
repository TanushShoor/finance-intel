import io
from fastapi.testclient import TestClient
import app.api.contracts as contracts_mod
from app.main import create_app
from app.db.engine import init_db, make_engine
from app.pipeline.runner import AnalysisResult
from app.schemas.models import ExecutiveSummary, StructuredDocument


def _fake_analysis():
    return AnalysisResult(structure=StructuredDocument(title="t", nodes=[]),
        clauses=[], deviations=[], risks=[], overall_risk_score=42,
        category_breakdown={"legal": 42},
        summary=ExecutiveSummary(coverage="c", who_carries_risk="w",
                                 key_commercial_terms=["k"], top_issues=["1", "2", "3"]))


def test_upload_analyze_get_flow(tmp_path, monkeypatch):
    init_db(make_engine(f"sqlite:///{tmp_path/'t.db'}"))
    monkeypatch.setattr(contracts_mod, "run_pipeline", lambda path, llm: _fake_analysis())
    monkeypatch.setattr(contracts_mod, "get_llm", lambda: None)
    client = TestClient(create_app())

    files = {"file": ("c.docx", io.BytesIO(b"data"), "application/octet-stream")}
    r = client.post("/contracts", files=files)
    assert r.status_code == 200
    cid = r.json()["id"]

    r = client.post(f"/contracts/{cid}/analyze")
    assert r.status_code == 200

    r = client.get(f"/contracts/{cid}")
    body = r.json()
    assert body["status"] == "done"
    assert body["analysis"]["overall_risk_score"] == 42


def test_get_and_put_baseline(tmp_path):
    from app.main import create_app
    from fastapi.testclient import TestClient
    client = TestClient(create_app())
    r = client.get("/baseline")
    assert r.status_code == 200 and "indemnity" in r.json()
    new = dict(r.json()); new["indemnity"] = "updated baseline text"
    r = client.put("/baseline", json=new)
    assert r.status_code == 200
    assert client.get("/baseline").json()["indemnity"] == "updated baseline text"
