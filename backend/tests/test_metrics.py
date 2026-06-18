import app.pipeline.metrics as metrics_mod
from app.pipeline.metrics import extract_metrics, _dedupe
from app.schemas.financial import MetricSet, Metric


def test_dedupe_keeps_first_per_name_and_period():
    ms = [
        Metric(name="revenue", value="$14.3B", period="Q4 2024"),
        Metric(name="revenue", value="$14.3 billion", period="Q4 2024"),  # dup key
        Metric(name="revenue", value="$53.1B", period="FY2024"),          # diff period
        Metric(name="eps", value="$0.13", period="Q4 2024"),
    ]
    out = _dedupe(ms)
    assert len(out) == 3
    assert out[0].value == "$14.3B"  # first wins


def test_extract_merges_across_chunks(monkeypatch, mock_llm):
    monkeypatch.setattr(metrics_mod, "chunk_text", lambda *a, **k: ["c1", "c2"])
    mock_llm.queue_response(MetricSet(metrics=[Metric(name="revenue", value="$14.3B")]))
    mock_llm.queue_response(MetricSet(metrics=[Metric(name="eps", value="$0.13")]))
    out = extract_metrics("ignored", mock_llm)
    assert sorted(m.name for m in out) == ["eps", "revenue"]


def test_extract_survives_a_bad_chunk(monkeypatch):
    monkeypatch.setattr(metrics_mod, "chunk_text", lambda *a, **k: ["c1", "c2"])

    class FlakyLLM:
        def __init__(self): self.n = 0
        def generate_structured(self, schema, prompt, **kw):
            self.n += 1
            if self.n == 1:
                raise RuntimeError("boom")
            return MetricSet(metrics=[Metric(name="revenue", value="$14.3B")])

    out = extract_metrics("ignored", FlakyLLM())
    assert [m.name for m in out] == ["revenue"]
