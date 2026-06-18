"""Run the full pipeline against synthetic fixtures and score the 5 success metrics.

Usage: ../legalvenv/bin/python eval/run_eval.py
Requires GEMINI_API_KEY in environment / .env.
"""
import json
import os
from app.llm.client import GeminiClient
from app.pipeline.runner import run_pipeline
from app.pipeline.batch import build_batch_comparison
from app.clause_types import ClauseType, ALL_CLAUSE_TYPES

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures", "generated")
KEYS = os.path.join(os.path.dirname(__file__), "..", "fixtures", "answer_keys")


def _key(name):
    return json.load(open(os.path.join(KEYS, name)))


def metric_1_extraction(llm):
    a = run_pipeline(os.path.join(FIX, "all_clauses.docx"), llm)
    present = {c.type.value for c in a.clauses if c.present}
    expected = set(_key("all_clauses.json")["expected_present"])
    missing = expected - present
    return ("Metric 1 — all clause types extracted", not missing,
            f"missing={missing}" if missing else f"all {len(expected)} found")


def metric_2_4_risk_and_flagging(llm):
    a = run_pipeline(os.path.join(FIX, "planted_risk.pdf"), llm)
    expected = set(_key("planted_risk.json")["expected_flagged"])
    flagged = {d["clause_type"] for d in a.deviations
               if d["classification"] in ("unfavourable", "unusual")}
    high_risk = {r.clause_type for r in a.risks if r.score >= 50}
    caught = (flagged | high_risk) & expected
    ok = len(caught) >= max(1, int(0.8 * len(expected)))
    return ("Metric 2&4 — planted risks flagged", ok,
            f"caught {len(caught)}/{len(expected)}: {sorted(caught)}")


def metric_3_summary(llm):
    a = run_pipeline(os.path.join(FIX, "planted_risk.pdf"), llm)
    s = a.summary
    ok = (len(s.top_issues) == 3 and len(s.coverage) > 20
          and len(s.who_carries_risk) > 10 and len(s.key_commercial_terms) >= 1)
    return ("Metric 3 — summary complete & plain", ok,
            f"top_issues={len(s.top_issues)}, coverage_len={len(s.coverage)}")


def metric_5_batch(llm):
    stored = []
    for i, name in enumerate(["contract_a", "contract_b", "contract_c"], start=1):
        a = run_pipeline(os.path.join(FIX, "batch", f"{name}.docx"), llm)
        stored.append({"id": i, "name": name,
                       "analysis": {"clauses": [c.model_dump() for c in a.clauses],
                                    "deviations": a.deviations,
                                    "risks": [r.model_dump() for r in a.risks]}})
    bc = build_batch_comparison(stored, ClauseType.GOVERNING_LAW, llm)
    texts = " ".join(c.text for c in bc.cells).lower()
    expected = [d.lower() for d in _key("batch.json")["expected_differences"]]
    found = [e for e in expected if e in texts or any(e in d.lower() for d in bc.differences)]
    ok = len(found) == len(expected)
    return ("Metric 5 — batch differences surfaced", ok,
            f"found {found} of {expected}")


def main():
    llm = GeminiClient()
    results = [metric_1_extraction(llm), metric_2_4_risk_and_flagging(llm),
               metric_3_summary(llm), metric_5_batch(llm)]
    print("\n=== EVAL RESULTS ===")
    passed = 0
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} — {detail}")
        passed += ok
    print(f"\n{passed}/{len(results)} metric groups passed.")
    raise SystemExit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
