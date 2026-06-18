# Pivot: Contract analyzer → AI Financial Document Analyst (v0)

**Date:** 2026-06-18
**Status:** Approved — build end-to-end, cover all 5 success metrics.

## Premise

The codebase is structurally a generic pipeline: **ingest → structure → extract items →
compare across periods/peers → synthesize a narrative**, plus batch-compare across
documents. That is exactly the financial-analyst shape. We swap the *domain layer* and
keep the skeleton (ingestion, `chunking`, `structure`, `llm` client + schema sanitizer,
`progress`, DB, upload/list/get/compare API, routing, design tokens).

## Success-metric → feature mapping

| # | Success metric | Feature | Stage |
|---|---|---|---|
| 1 | All named figures extracted | Metric extraction (chunked, merged) | `pipeline/metrics.py` |
| 2 | Cautious vs confident passage | Tone analysis | `pipeline/tone.py` |
| 3 | New risk flagged yr2 vs yr1 | Risk-factor extraction + cross-period diff | `pipeline/risk_factors.py` + `/compare/risk` |
| 4 | Benchmarking table accurate | Competitor benchmarking (grid from stored metrics + commentary) | `pipeline/benchmark.py` + `/benchmark` |
| 5 | Memo with bull + bear, grounded | Investment memo synthesized from extracted findings | `pipeline/memo.py` |

## Schemas (`app/schemas/financial.py`)

`DocumentIdentity{company,period,doc_type}`, `Metric{name,label,period,value,
value_numeric,unit,basis,source}` + `MetricSet`, `ToneAnalysis{overall_sentiment,
confidence_score,hedging_level,summary,passages[TonePassage]}`,
`RiskFactor{category,title,text,severity}` + `RiskFactorSet`,
`RiskComparison{deltas[RiskDelta{title,category,status,rationale}]}`,
`InvestmentMemo{company_overview,financial_summary,bull_case[],bear_case[],key_risks[],
questions[]}`, `FinancialAnalysis{identity,structure,metrics,tone,risk_factors,memo}`,
`BenchmarkCommentary{highlights[]}`. Canonical metric list drives extraction + grid alignment.

## Pipeline

- `metrics.py` — chunked map over text → merge/dedupe by (name, period). High recall.
- `tone.py` — single bounded call; returns overall tone + the most confident/cautious passages.
- `risk_factors.py` — `extract_risk_factors` (chunked) + `compare_risk_factors(prior, current)` → new/escalated/unchanged/removed.
- `memo.py` — consumes metrics+tone+risks (not raw doc) so bull/bear are grounded.
- `benchmark.py` — assemble company×metric grid in code from stored analyses; one LLM call for commentary (avoids dict-schema issues).
- `identity.py` — company/period/doc_type from the doc head.
- `runner.py` — `run_financial_analysis` → `FinancialAnalysis`; every stage best-effort (one failure can't sink the run). Reports coarse stage labels via `on_progress` (structure still streams chunk progress).

## API / DB

- `Contract` model + `/contracts` endpoints reused (generic "document"); `analysis` JSON now holds `FinancialAnalysis`.
- `/compare` → `/benchmark` (companies × metrics). New `/compare/risk` (two filings' risk factors).
- `DELETE /contracts/{id}` added; UI delete control.
- Startup: mark any `processing`/`uploaded` row `failed` (interrupted) — no more zombies after a restart.
- Remove contract-only modules: `clause_types`, `pipeline/{extraction,comparison,risk,summary,batch}`, `baseline/`, `api/baseline`, contract schemas.

## Frontend

Keep the design system + Document tab. Rebrand → "LEDGER" (financial analyst). Repoint:
- Library → filings register + delete.
- Analysis → **Filing dashboard**: identity header, metrics table (canonical, with YoY/QoQ where periods differ), tone readout (reuse gauge), risk-factor list.
- Summary → **Investment Memo** (overview, financial summary, bull/bear, risks, questions).
- BatchCompare → **Benchmarking** grid + a risk-diff view for two filings.
- Multi-stage progress animation (structuring streams chunks; later stages show labels).

## Out of scope (v0)

Full-text tone over giant 10-Ks (bounded window for v0), strict numeric unit normalization
across all currencies, transcript speaker diarization.
