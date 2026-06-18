# Contract Analysis Platform

A portfolio proof-of-concept that automates contract review. Upload a PDF or DOCX contract and the platform extracts seven named clause types, compares each clause against a configurable market-standard baseline, scores risk per clause and overall, generates a plain-English executive summary, and lets you compare a specific clause across multiple contracts side-by-side.

Backend: FastAPI + Google Gemini (`google-genai`, structured output) + SQLite. Frontend: React / Vite / TypeScript / Tailwind CSS. Document parsing: pdfplumber (PDF) and python-docx (DOCX) with a Docling fallback for scanned PDFs.

---

## Architecture

The pipeline runs in six stages:

1. **Ingest** — parse PDF or DOCX into text blocks.
2. **Extract** — Gemini structured-output call: for each of the 7 clause types, decide `present/absent` and return the verbatim text.
3. **Compare** — Gemini call: compare each extracted clause against the market-standard baseline position and classify as `standard`, `favourable`, `unfavourable`, or `unusual`, with a plain-English rationale.
4. **Risk score** — deterministic aggregation: per-clause score (0–100) derived from the deviation classification; overall score and category breakdown computed arithmetically from clause scores.
5. **Summarise** — Gemini call: produce a structured executive summary (`coverage`, `who_carries_risk`, `key_commercial_terms`, `top_issues`).
6. **Batch compare** — Gemini call across ≥ 2 stored contract analyses: extract the text of one clause type from each contract and return a comparison table plus a list of plain-English differences.

Each LLM stage sends a Pydantic schema as the response schema so Gemini returns validated JSON directly.

---

## Prerequisites

- **Python 3.13** — a virtualenv `legalvenv/` is already created at the repo root.
- **Node 20** — for the React frontend.
- **Google Gemini API key** — free tier is sufficient for development.

---

## Setup

### 1. Backend dependencies

```bash
legalvenv/bin/pip install -r backend/requirements.txt
```

### 2. Configure the API key

```bash
cp backend/.env.example backend/.env
# Then open backend/.env and set:
# GEMINI_API_KEY=your-key-here
```

`GEMINI_MODEL` defaults to `gemini-2.5-flash` if not set.

### 3. Generate synthetic fixtures (needed for the eval harness)

```bash
cd backend && ../legalvenv/bin/python fixtures/generate.py
```

### 4. Frontend dependencies

```bash
cd frontend && npm install
```

---

## Running

### Backend

```bash
cd backend
../legalvenv/bin/uvicorn app.main:app --reload
```

Serves at **http://localhost:8000**. Interactive API docs at **http://localhost:8000/docs**.

### Frontend

```bash
cd frontend
npm run dev
```

Serves at **http://localhost:5173**. The frontend expects the backend at `localhost:8000`; CORS is pre-configured.

---

## Usage

1. Open **http://localhost:5173** and go to the **Library** page.
2. Upload a PDF or DOCX contract. Analysis starts automatically in the background.
3. Once complete, open the contract to see:
   - **Risk gauge** — overall risk score (0–100).
   - **Category breakdown** — per-clause scores.
   - **Clause cards** — each clause with its extracted text and deviation badge (`standard` / `favourable` / `unfavourable` / `unusual`).
4. Navigate to the **Summary** tab to read the plain-English executive summary.
5. Use **Batch Compare**: select ≥ 2 analyzed contracts and a clause type to see a side-by-side comparison table and a list of key differences.

---

## Testing

### Unit tests (no API key required — Gemini is mocked)

```bash
cd backend && ../legalvenv/bin/pytest
```

### Eval harness (real Gemini — requires `GEMINI_API_KEY` in `backend/.env`)

Runs the full pipeline against synthetic fixtures and scores all 5 success metrics:

```bash
cd backend && ../legalvenv/bin/python eval/run_eval.py
```

Exit code 0 = all metric groups passed; 1 = one or more failed.

---

## Configuring the market-standard baseline

The baseline defines the "fair / market-standard" position for each of the 7 clause types. Deviations from it drive the risk scoring.

**Edit directly:**

```bash
# backend/app/baseline/market_standard.json
# One key per clause type, value is the standard-position description string.
```

**Via the API:**

```
GET  /baseline        # returns all positions
PUT  /baseline        # body: { "clause_type": "...", "standard_position": "..." }
```

---

## Document parsing and the Docling fallback

- **PDF** — pdfplumber extracts text page-by-page.
- **DOCX** — python-docx extracts paragraph text.
- **Scanned PDF fallback** — if pdfplumber yields fewer than 30 characters (no text layer), the ingestion router automatically retries with Docling (`docling.document_converter.DocumentConverter`), which handles OCR and complex layouts. Docling is an optional heavy dependency; a helpful error is raised if it is not installed.

---

## Project layout

```
legal_docs_project/
├── legalvenv/                  # Python 3.13 virtualenv
├── backend/
│   ├── app/
│   │   ├── ingestion/          # pdf.py, docx.py, docling_parser.py, router.py, structure.py
│   │   ├── pipeline/           # extraction.py, comparison.py, risk.py, summary.py, runner.py, batch.py
│   │   ├── baseline/           # loader.py, market_standard.json
│   │   ├── db/                 # engine.py, models.py
│   │   ├── api/                # contracts.py, baseline.py, compare.py
│   │   ├── llm/                # client.py, prompts.py
│   │   ├── schemas/            # models.py
│   │   ├── clause_types.py
│   │   ├── config.py
│   │   └── main.py
│   ├── fixtures/
│   │   ├── generate.py
│   │   ├── generated/          # all_clauses.docx, planted_risk.pdf, batch/
│   │   └── answer_keys/        # all_clauses.json, planted_risk.json, batch.json
│   ├── eval/
│   │   └── run_eval.py         # 5-metric eval harness
│   ├── tests/                  # unit tests (mocked Gemini)
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/                # API client
│       ├── components/         # RiskGauge, ClauseCard, DeviationBadge
│       └── pages/              # Library, Analysis, Summary, BatchCompare
└── docs/
    └── superpowers/
        ├── specs/
        └── plans/
```
