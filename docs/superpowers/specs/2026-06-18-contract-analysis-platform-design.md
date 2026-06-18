# Contract Analysis Platform — Design Spec

**Date:** 2026-06-18
**Status:** Approved design, pending implementation plan
**Scope:** Portfolio / demo proof-of-concept (runs locally, optimized to prove 5 success metrics, no auth)

## 1. Problem & Goal

Contract review is expensive, slow, and error-prone at scale. This tool surfaces the ~10% of a
contract that needs a human legal decision and handles the other ~90% automatically.

It ingests a contract, extracts named clauses, compares them to a configurable market-standard
baseline, scores risk, and produces a plain-English executive summary. It also compares the same
clause side-by-side across multiple contracts for due-diligence.

### Success metrics (the build is judged against these)
1. Clause extraction correctly identifies all named clause types in a test contract.
2. Risk flagging identifies the intentionally problematic clauses planted in a test document.
3. Plain-English summary is accurate and comprehensible to a non-lawyer.
4. Market-standard comparison flags the same clauses a trained legal reviewer would flag.
5. Batch comparison correctly surfaces differences across 3 test contracts on the same clause.

## 2. Tech Stack

- **Backend:** FastAPI · `google-genai` SDK · Pydantic v2 · SQLite (via SQLModel) · `uvicorn`
- **Document parsing:** `pdfplumber` (PDF), `python-docx` (DOCX) as lightweight default;
  **Docling as automatic fallback** for scanned/no-text-layer PDFs or degraded extraction
- **AI:** Gemini via `google-genai` SDK using **structured output** (response schema = Pydantic models)
- **Frontend:** React + Vite + TypeScript + Tailwind
- **Storage:** SQLite for analyses; local `uploads/` folder for raw files
- **Python:** 3.13 (existing `legalvenv`)

The whole pipeline is LLM-driven structured extraction + reasoning. No agentic framework — a linear
pipeline of focused, individually-testable Gemini calls (chosen over a single mega-prompt for
accuracy/testability, and over ADK for reproducibility).

## 3. Architecture — 6-Stage Pipeline

```
Upload (PDF/DOCX)
  → 1. Ingestion      parse text + layout (lightweight → Docling fallback), then a Gemini
                      structuring pass builds a clause tree: sections, numbering, hierarchy,
                      cross-references
  → 2. Extraction     identify the 7 named clause types → typed clause objects (text + location
                      + confidence); missing types explicitly marked "not present"
  → 3. Comparison     each extracted clause vs. configurable market-standard baseline
                      → favourable / unfavourable / unusual + rationale
  → 4. Risk scoring   per-clause score 0–100 + category (financial / operational / legal /
                      reputational); aggregated to an overall contract risk score
  → 5. Summary        1-page plain-English executive summary + top 3 issues to negotiate
  → 6. Batch compare  same clause type side-by-side across N stored contracts (on-demand)
```

The 7 named clause types: **indemnity, limitation of liability, governing law, termination,
IP ownership, payment terms, confidentiality.**

## 4. Backend Modules

Each module has one clear purpose, a well-defined interface, and is independently testable.

- `llm/` — Gemini client wrapper, per-task Pydantic schemas, prompt templates, retry/backoff.
  **Mockable** so the pipeline can be unit-tested deterministically without API calls.
- `ingestion/`
  - `base.py` — `DocumentParser` protocol returning a normalized `ParsedDocument` (blocks + text + metadata)
  - `pdf.py` — pdfplumber parser
  - `docx.py` — python-docx parser
  - `docling_parser.py` — Docling-backed parser (fallback)
  - `router.py` — picks parser; falls back to Docling when a PDF has no text layer or extraction is degraded
  - `structure.py` — Gemini structuring pass → clause tree (sections, numbering, hierarchy, cross-refs)
- `extraction/` — clause extraction → typed `ExtractedClause` objects
- `comparison/` — deviation classifier against baseline
- `risk/` — per-clause scoring + overall aggregation (deterministic math over LLM-assigned components)
- `summary/` — executive summary generator
- `batch/` — cross-contract clause comparison
- `baseline/` — `market_standard.json` (configurable standard position per clause type) + loader
- `db/` — SQLModel models (Contract, Clause, Deviation, RiskScore, Analysis), SQLite engine
- `api/` — FastAPI routers
- `eval/` — harness scoring the build against the 5 success metrics
- `fixtures/` — synthetic contracts + generator script + expected-answer keys

## 5. Data Model (SQLite via SQLModel)

- **Contract** — id, filename, file_path, format, status (`uploaded`/`processing`/`done`/`failed`),
  created_at, structured_tree (JSON), error (nullable)
- **Clause** — id, contract_id, type, text, location (section ref), confidence, present (bool)
- **Deviation** — id, clause_id, classification (favourable/unfavourable/unusual), rationale,
  baseline_ref
- **RiskScore** — id, clause_id, score (0–100), category, rationale
- **Analysis** — id, contract_id, overall_risk_score, category_breakdown (JSON), summary (JSON:
  coverage / who-carries-risk / key-terms / top-3-issues)

## 6. API

Background processing + polling (keeps the UI responsive during multi-second Gemini runs).

- `POST /contracts` — upload PDF/DOCX → `{id}`
- `POST /contracts/{id}/analyze` — kick off pipeline as a background task
- `GET /contracts/{id}` — status + full analysis (clauses, deviations, risk, summary)
- `GET /contracts/{id}/summary` — executive summary only
- `GET /contracts` — list contracts/analyses (library view)
- `POST /compare` — `{contract_ids: [...], clause_type}` → side-by-side comparison
- `GET /baseline` / `PUT /baseline` — view/edit the market-standard baseline

## 7. Frontend Views

1. **Upload & library** — drag-drop upload, live processing status, list of past analyses
2. **Analysis view** — overall risk gauge + category breakdown; per-clause cards (text, deviation
   flag with color, risk score, plain-English rationale); clause-tree navigation
3. **Executive summary** — the 1-pager (coverage, who carries risk, key commercial terms, top 3 issues)
4. **Batch comparison** — pick a clause type + contracts → side-by-side columns with deviations/risk

## 8. Risk Scoring Model

Per clause, Gemini assigns: a category (financial/operational/legal/reputational), a severity
(0–100), and a rationale, informed by the deviation classification. Overall contract score =
deterministic weighted aggregation in `risk/` (e.g., severity-weighted, with unfavourable/unusual
deviations weighted higher), so the headline number is reproducible and explainable rather than a
second opaque LLM guess. Category breakdown = max/aggregate score per category.

## 9. Error Handling

- **Per-clause isolation** — one failed clause does not abort the whole run; it's recorded with an error.
- **Structured-output validation** — responses validated against Pydantic schemas; retry with backoff on
  malformed output or transient API errors.
- **Missing clauses** — clause types not found are explicitly marked `present=false`, never silently dropped.
- **Parser fallback** — no-text-layer/degraded PDF triggers Docling automatically; total parse failure
  marks the contract `failed` with a readable error.
- **Background job failures** — captured on the Contract row (`status=failed`, `error=...`) and surfaced in the UI.

## 10. Test Fixtures (synthetic, generated)

A generator script produces, with matching expected-answer keys:
- **`all_clauses.docx`** — contains all 7 named clause types (proves metric 1).
- **`planted_risk.pdf`** — deliberately problematic clauses (e.g., unlimited liability, one-sided
  indemnity, auto-renewal, IP assignment to counterparty) (proves metrics 2 & 4).
- **`batch/contract_a|b|c`** — 3 contracts differing on a target clause (e.g., governing law /
  liability cap) (proves metric 5).

Fixtures are generated as clean digital documents with literal section numbering, so the lightweight
parsers suffice for the demo; the Docling fallback covers real/scanned docs added later.

## 11. Testing Strategy

- **Eval harness (`eval/`)** — runs the full pipeline on fixtures and asserts each success metric:
  all 7 types extracted; every planted risky clause flagged; deviation flags match the answer key;
  batch compare surfaces the seeded differences; a readability heuristic on the summary.
- **Unit tests (pytest)** — parsers (against fixture files), risk-aggregation math, baseline loader,
  schema validation. **Gemini mocked** for determinism in unit tests; the eval harness exercises the
  real model.

## 12. Out of Scope (YAGNI)

Authentication, multi-tenancy, cloud deployment, Postgres, real-time collaboration, contract editing /
redlining, e-signature, non-English contracts. The parser interface, baseline config, and modular
pipeline leave clean seams to add these later.

## 13. Implementation Order (high level)

1. Project scaffold (backend + frontend), config, Gemini client + schemas
2. Ingestion (parsers + interface + fallback + structuring)
3. Fixture generator + answer keys
4. Extraction → Comparison → Risk → Summary stages
5. API + background processing + DB
6. Batch comparison
7. Frontend views
8. Eval harness proving all 5 metrics
