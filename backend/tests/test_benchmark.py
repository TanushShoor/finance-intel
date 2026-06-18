from app.pipeline.benchmark import build_benchmark
from app.schemas.financial import BenchmarkCommentary


def _stored(name, company, metrics):
    return {"id": 1, "name": name,
            "analysis": {"identity": {"company": company}, "metrics": metrics}}


def test_grid_uses_company_name_and_aligns_metrics(mock_llm):
    mock_llm.queue_response(BenchmarkCommentary(highlights=["NVDA leads on revenue."]))
    stored = [
        _stored("intel.pdf", "Intel", [{"name": "revenue", "value": "$14.3B"}]),
        _stored("nvda.pdf", "NVIDIA", [{"name": "revenue", "value": "$35.1B"},
                                       {"name": "eps", "value": "$0.78"}]),
    ]
    out = build_benchmark(stored, mock_llm)
    assert "revenue" in out["metric_names"] and "eps" in out["metric_names"]
    intel = next(r for r in out["rows"] if r["company"] == "Intel")
    nvda = next(r for r in out["rows"] if r["company"] == "NVIDIA")
    assert intel["values"]["revenue"] == "$14.3B"
    assert intel["values"]["eps"] is None       # Intel didn't report it
    assert nvda["values"]["eps"] == "$0.78"
    assert out["highlights"] == ["NVDA leads on revenue."]


def test_empty_columns_are_pruned(mock_llm):
    mock_llm.queue_response(BenchmarkCommentary(highlights=[]))
    stored = [_stored("a.pdf", "A", [{"name": "revenue", "value": "$1B"}])]
    out = build_benchmark(stored, mock_llm)
    # Only the one reported metric survives, not the whole canonical list.
    assert out["metric_names"] == ["revenue"]


def test_falls_back_to_filename_when_no_company(mock_llm):
    mock_llm.queue_response(BenchmarkCommentary(highlights=[]))
    stored = [{"id": 1, "name": "mystery.pdf",
               "analysis": {"metrics": [{"name": "revenue", "value": "$2B"}]}}]
    out = build_benchmark(stored, mock_llm)
    assert out["rows"][0]["company"] == "mystery.pdf"
