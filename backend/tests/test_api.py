import io
from fastapi.testclient import TestClient
import app.api.contracts as contracts_mod
from app.main import create_app
from app.db.engine import init_db, make_engine
from app.schemas.models import StructuredDocument
from app.schemas.financial import (
    FinancialAnalysis, DocumentIdentity, Metric, ToneAnalysis, RiskFactor, InvestmentMemo)


def _fake_analysis():
    return FinancialAnalysis(
        identity=DocumentIdentity(company="Intel", period="Q4 2024", doc_type="earnings release"),
        structure=StructuredDocument(title="Intel Q4", blocks=[]),
        metrics=[Metric(name="revenue", value="$14.3B", period="Q4 2024")],
        tone=ToneAnalysis(overall_sentiment="cautious", confidence_score=40),
        risk_factors=[RiskFactor(category="market", title="Demand", severity=60)],
        memo=InvestmentMemo(company_overview="Intel.", bull_case=["a"], bear_case=["b"]))


def test_upload_analyze_get_flow(tmp_path, monkeypatch):
    init_db(make_engine(f"sqlite:///{tmp_path/'t.db'}"))
    monkeypatch.setattr(contracts_mod, "run_financial_analysis",
                        lambda path, llm, on_progress=None: _fake_analysis())
    monkeypatch.setattr(contracts_mod, "get_llm", lambda: None)
    client = TestClient(create_app())

    files = {"file": ("intel.pdf", io.BytesIO(b"data"), "application/octet-stream")}
    r = client.post("/contracts", files=files)
    assert r.status_code == 200
    cid = r.json()["id"]

    r = client.post(f"/contracts/{cid}/analyze")
    assert r.status_code == 200

    r = client.get(f"/contracts/{cid}")
    body = r.json()
    assert body["status"] == "done"
    assert body["analysis"]["identity"]["company"] == "Intel"
    assert body["analysis"]["metrics"][0]["name"] == "revenue"
    assert body["analysis"]["memo"]["bull_case"] == ["a"]


def test_list_includes_identity(tmp_path, monkeypatch):
    init_db(make_engine(f"sqlite:///{tmp_path/'t.db'}"))
    monkeypatch.setattr(contracts_mod, "run_financial_analysis",
                        lambda path, llm, on_progress=None: _fake_analysis())
    monkeypatch.setattr(contracts_mod, "get_llm", lambda: None)
    client = TestClient(create_app())

    cid = client.post("/contracts", files={
        "file": ("intel.pdf", io.BytesIO(b"data"), "application/octet-stream")}).json()["id"]
    client.post(f"/contracts/{cid}/analyze")

    row = next(r for r in client.get("/contracts").json() if r["id"] == cid)
    assert row["company"] == "Intel" and row["doc_type"] == "earnings release"


def test_delete_contract(tmp_path):
    init_db(make_engine(f"sqlite:///{tmp_path/'t.db'}"))
    client = TestClient(create_app())
    cid = client.post("/contracts", files={
        "file": ("x.pdf", io.BytesIO(b"data"), "application/octet-stream")}).json()["id"]
    assert client.delete(f"/contracts/{cid}").status_code == 200
    assert client.get(f"/contracts/{cid}").status_code == 404
