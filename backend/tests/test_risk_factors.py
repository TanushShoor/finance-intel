import app.pipeline.risk_factors as rf_mod
from app.pipeline.risk_factors import extract_risk_factors, compare_risk_factors, _dedupe
from app.schemas.financial import RiskFactorSet, RiskFactor, RiskComparison, RiskDelta


def test_dedupe_by_title():
    risks = [
        RiskFactor(category="market", title="Demand", severity=50),
        RiskFactor(category="market", title="demand", severity=70),  # case-dup
        RiskFactor(category="legal", title="Litigation", severity=40),
    ]
    out = _dedupe(risks)
    assert [r.title for r in out] == ["Demand", "Litigation"]


def test_dedupe_keeps_empty_title_risks_using_text():
    # The model often puts the risk in `text` and leaves `title` blank; those
    # must be retained (title backfilled), not silently dropped.
    risks = [
        RiskFactor(category="market", title="", text="Intense AI competition.", severity=80),
        RiskFactor(category="operational", title="", text="Single foundry dependence.", severity=90),
    ]
    out = _dedupe(risks)
    assert len(out) == 2
    assert all(r.title for r in out)


def test_extract_merges_chunks(monkeypatch, mock_llm):
    monkeypatch.setattr(rf_mod, "chunk_text", lambda *a, **k: ["c1", "c2"])
    mock_llm.queue_response(RiskFactorSet(risk_factors=[RiskFactor(title="Supply chain")]))
    mock_llm.queue_response(RiskFactorSet(risk_factors=[RiskFactor(title="Export controls")]))
    out = extract_risk_factors("ignored", mock_llm)
    assert {r.title for r in out} == {"Supply chain", "Export controls"}


def test_compare_flags_new_risk(mock_llm):
    # The comparison is an LLM judgement; here we assert the wrapper returns the
    # structured deltas the model produced (a new risk in the current period).
    mock_llm.queue_response(RiskComparison(deltas=[
        RiskDelta(title="AI competition", category="technology", status="new",
                  rationale="Absent in the prior year filing."),
        RiskDelta(title="Demand", category="market", status="unchanged", rationale="Same."),
    ]))
    prior = [RiskFactor(title="Demand")]
    current = [RiskFactor(title="Demand"), RiskFactor(title="AI competition")]
    result = compare_risk_factors(prior, current, mock_llm)
    new = [d for d in result.deltas if d.status == "new"]
    assert [d.title for d in new] == ["AI competition"]
