# Contract Analysis Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local contract-analysis platform that ingests PDF/DOCX contracts, extracts named clauses, compares them to a market-standard baseline, scores risk, generates a plain-English executive summary, and compares clauses side-by-side across contracts.

**Architecture:** A linear 6-stage pipeline (ingest → extract → compare → score → summarize → batch-compare). Each stage is a focused module backed by a Gemini structured-output call (via `google-genai`) with a Pydantic response schema. FastAPI exposes upload/analyze/compare endpoints with background processing + polling; SQLite (SQLModel) persists results. Document parsing sits behind a `DocumentParser` interface with pdfplumber/python-docx defaults and a Docling fallback. A React/Vite/TS frontend renders analysis, summary, and batch comparison. An eval harness proves the 5 success metrics.

**Tech Stack:** Python 3.13, FastAPI, uvicorn, google-genai, Pydantic v2, SQLModel, pdfplumber, python-docx, docling, reportlab (fixture PDF generation), pytest, React, Vite, TypeScript, Tailwind.

---

## File Structure

```
legal_docs_project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                # settings (env: GEMINI_API_KEY, model, db path)
│   │   ├── main.py                  # FastAPI app + router wiring + CORS
│   │   ├── clause_types.py          # the 7 named clause-type enum + display names
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── client.py            # Gemini wrapper: generate_structured(schema, prompt)
│   │   │   └── prompts.py           # prompt templates per stage
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── models.py            # all Pydantic response/domain schemas
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # ParsedDocument + DocumentParser protocol
│   │   │   ├── pdf.py               # pdfplumber parser
│   │   │   ├── docx.py              # python-docx parser
│   │   │   ├── docling_parser.py    # Docling fallback parser
│   │   │   ├── router.py            # choose parser + fallback logic
│   │   │   └── structure.py         # Gemini structuring → clause tree
│   │   ├── pipeline/
│   │   │   ├── __init__.py
│   │   │   ├── extraction.py        # stage 2
│   │   │   ├── comparison.py        # stage 3
│   │   │   ├── risk.py              # stage 4 (LLM components + deterministic aggregation)
│   │   │   ├── summary.py           # stage 5
│   │   │   ├── batch.py             # stage 6
│   │   │   └── runner.py            # orchestrates stages 1-5 for one contract
│   │   ├── baseline/
│   │   │   ├── __init__.py
│   │   │   ├── market_standard.json # configurable baseline per clause type
│   │   │   └── loader.py            # load/save baseline
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py            # SQLModel tables
│   │   │   └── engine.py            # engine + session + init
│   │   └── api/
│   │       ├── __init__.py
│   │       ├── contracts.py         # upload, analyze, get, list
│   │       ├── compare.py           # batch compare
│   │       └── baseline.py          # get/put baseline
│   ├── fixtures/
│   │   ├── generate.py              # builds synthetic contracts + answer keys
│   │   ├── generated/               # output (gitignored)
│   │   └── answer_keys/             # expected results JSON
│   ├── eval/
│   │   └── run_eval.py              # scores build against 5 success metrics
│   ├── tests/
│   │   ├── conftest.py              # fixtures: mock Gemini client, tmp db
│   │   ├── test_ingestion.py
│   │   ├── test_structure.py
│   │   ├── test_extraction.py
│   │   ├── test_comparison.py
│   │   ├── test_risk.py
│   │   ├── test_summary.py
│   │   ├── test_batch.py
│   │   ├── test_baseline.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── package.json, vite.config.ts, tsconfig.json, tailwind config
│   └── src/
│       ├── main.tsx, App.tsx, index.css
│       ├── api/client.ts            # typed fetch wrappers
│       ├── types.ts                 # TS mirror of backend schemas
│       ├── components/              # RiskGauge, ClauseCard, DeviationBadge, etc.
│       └── pages/                   # Library, Analysis, Summary, BatchCompare
└── docs/superpowers/...
```

**Gemini model:** default `gemini-2.5-flash`, overridable via `GEMINI_MODEL` env var. The `google-genai` SDK supports passing a Pydantic model as `response_schema` with `response_mime_type="application/json"`; the wrapper returns the validated object.

---

## Phase 0 — Scaffold & Config

### Task 0.1: Backend package + dependencies

**Files:**
- Create: `backend/requirements.txt`, `backend/.env.example`, `backend/app/__init__.py`, `backend/app/config.py`
- Create: empty `__init__.py` in `app/llm`, `app/schemas`, `app/ingestion`, `app/pipeline`, `app/baseline`, `app/db`, `app/api`

- [ ] **Step 1: Write `requirements.txt`**

```
fastapi==0.115.*
uvicorn[standard]==0.32.*
google-genai==1.*
pydantic==2.*
pydantic-settings==2.*
sqlmodel==0.0.22
python-multipart==0.0.*
pdfplumber==0.11.*
python-docx==1.1.*
docling==2.*
reportlab==4.*
pytest==8.*
httpx==0.27.*
```

- [ ] **Step 2: Install into the existing venv**

Run: `legalvenv/bin/pip install -r backend/requirements.txt`
Expected: all install successfully. If `docling` fails on Python 3.13, note it and continue — the fallback is optional and lightweight parsers cover fixtures (record the failure, don't block).

- [ ] **Step 3: Write `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    db_path: str = "contracts.db"
    upload_dir: str = "uploads"


settings = Settings()
```

- [ ] **Step 4: Write `backend/.env.example`**

```
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.5-flash
DB_PATH=contracts.db
UPLOAD_DIR=uploads
```

- [ ] **Step 5: Create the empty `__init__.py` files**

Run: `cd backend && for d in app app/llm app/schemas app/ingestion app/pipeline app/baseline app/db app/api; do touch $d/__init__.py; done`

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/.env.example backend/app
git commit -m "chore: backend scaffold, deps, and config"
```

### Task 0.2: Pytest harness + mock Gemini client

**Files:**
- Create: `backend/tests/conftest.py`, `backend/pytest.ini`

- [ ] **Step 1: Write `backend/pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 2: Write `backend/tests/conftest.py`** (mock LLM that returns canned validated objects per call)

```python
import pytest


class MockLLM:
    """Stand-in for the Gemini client. Pop responses in FIFO order.

    Each queued item is the object generate_structured should return.
    """

    def __init__(self):
        self.queue = []
        self.calls = []

    def queue_response(self, obj):
        self.queue.append(obj)

    def generate_structured(self, schema, prompt, **kwargs):
        self.calls.append({"schema": schema, "prompt": prompt})
        if not self.queue:
            raise AssertionError("MockLLM queue empty; queue a response in the test")
        return self.queue.pop(0)


@pytest.fixture
def mock_llm():
    return MockLLM()
```

- [ ] **Step 3: Verify pytest runs (collects 0 tests, no errors)**

Run: `cd backend && ../legalvenv/bin/pytest -q`
Expected: `no tests ran` with exit code 5 (no tests collected) — confirms harness imports cleanly.

- [ ] **Step 4: Commit**

```bash
git add backend/pytest.ini backend/tests/conftest.py
git commit -m "test: pytest harness and mock Gemini client"
```

---

## Phase 1 — Schemas & LLM Client

### Task 1.1: Clause-type enum

**Files:**
- Create: `backend/app/clause_types.py`
- Test: `backend/tests/test_extraction.py` (start the file)

- [ ] **Step 1: Write failing test**

```python
from app.clause_types import ClauseType, ALL_CLAUSE_TYPES


def test_seven_named_clause_types():
    assert len(ALL_CLAUSE_TYPES) == 7
    assert ClauseType.INDEMNITY in ALL_CLAUSE_TYPES
    assert ClauseType.LIMITATION_OF_LIABILITY.value == "limitation_of_liability"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_extraction.py::test_seven_named_clause_types -v`
Expected: FAIL — `ModuleNotFoundError: app.clause_types`

- [ ] **Step 3: Write `app/clause_types.py`**

```python
from enum import Enum


class ClauseType(str, Enum):
    INDEMNITY = "indemnity"
    LIMITATION_OF_LIABILITY = "limitation_of_liability"
    GOVERNING_LAW = "governing_law"
    TERMINATION = "termination"
    IP_OWNERSHIP = "ip_ownership"
    PAYMENT_TERMS = "payment_terms"
    CONFIDENTIALITY = "confidentiality"


ALL_CLAUSE_TYPES = list(ClauseType)

DISPLAY_NAMES = {
    ClauseType.INDEMNITY: "Indemnity",
    ClauseType.LIMITATION_OF_LIABILITY: "Limitation of Liability",
    ClauseType.GOVERNING_LAW: "Governing Law",
    ClauseType.TERMINATION: "Termination",
    ClauseType.IP_OWNERSHIP: "IP Ownership",
    ClauseType.PAYMENT_TERMS: "Payment Terms",
    ClauseType.CONFIDENTIALITY: "Confidentiality",
}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_extraction.py::test_seven_named_clause_types -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/clause_types.py backend/tests/test_extraction.py
git commit -m "feat: clause-type enum (7 named types)"
```

### Task 1.2: Pydantic schemas

**Files:**
- Create: `backend/app/schemas/models.py`
- Test: `backend/tests/test_schemas.py`

- [ ] **Step 1: Write failing test**

```python
from app.schemas.models import (
    ExtractedClause, ClauseExtractionResult, DeviationResult,
    RiskComponent, ExecutiveSummary, ClauseNode,
)
from app.clause_types import ClauseType


def test_extracted_clause_roundtrip():
    c = ExtractedClause(type=ClauseType.INDEMNITY, present=True,
                        text="The Supplier shall indemnify...",
                        location="Section 8.1", confidence=0.9)
    assert c.present and c.confidence == 0.9


def test_missing_clause_allows_empty_text():
    c = ExtractedClause(type=ClauseType.TERMINATION, present=False,
                        text="", location=None, confidence=0.0)
    assert c.present is False


def test_deviation_classification_enum():
    d = DeviationResult(classification="unfavourable", rationale="One-sided.",
                        baseline_ref="indemnity")
    assert d.classification == "unfavourable"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_schemas.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/schemas/models.py`**

```python
from typing import Literal, Optional
from pydantic import BaseModel, Field
from app.clause_types import ClauseType

RiskCategory = Literal["financial", "operational", "legal", "reputational"]
Classification = Literal["favourable", "unfavourable", "unusual", "standard"]


# --- Ingestion / structure ---
class ClauseNode(BaseModel):
    number: Optional[str] = Field(None, description="e.g. '8.1' or '(a)'")
    heading: Optional[str] = None
    text: str = ""
    cross_references: list[str] = Field(default_factory=list)
    children: list["ClauseNode"] = Field(default_factory=list)


class StructuredDocument(BaseModel):
    title: Optional[str] = None
    nodes: list[ClauseNode] = Field(default_factory=list)


# --- Extraction ---
class ExtractedClause(BaseModel):
    type: ClauseType
    present: bool
    text: str = ""
    location: Optional[str] = None
    confidence: float = 0.0


class ClauseExtractionResult(BaseModel):
    clauses: list[ExtractedClause]


# --- Comparison ---
class DeviationResult(BaseModel):
    classification: Classification
    rationale: str
    baseline_ref: str


# --- Risk ---
class RiskComponent(BaseModel):
    category: RiskCategory
    severity: int = Field(ge=0, le=100)
    rationale: str


# --- Summary ---
class ExecutiveSummary(BaseModel):
    coverage: str
    who_carries_risk: str
    key_commercial_terms: list[str]
    top_issues: list[str] = Field(description="Top 3 issues to negotiate")


# --- Batch ---
class BatchCell(BaseModel):
    contract_id: int
    contract_name: str
    present: bool
    text: str = ""
    classification: Optional[Classification] = None
    risk_score: Optional[int] = None


class BatchComparison(BaseModel):
    clause_type: ClauseType
    cells: list[BatchCell]
    differences: list[str]


ClauseNode.model_rebuild()
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_schemas.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/models.py backend/tests/test_schemas.py
git commit -m "feat: Pydantic schemas for all pipeline stages"
```

### Task 1.3: Gemini client wrapper

**Files:**
- Create: `backend/app/llm/client.py`, `backend/app/llm/prompts.py`
- Test: `backend/tests/test_llm_client.py`

- [ ] **Step 1: Write failing test** (validates the wrapper parses `.parsed` and retries)

```python
from pydantic import BaseModel
from app.llm.client import GeminiClient


class _Out(BaseModel):
    value: int


class _FakeModels:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = 0

    def generate_content(self, **kwargs):
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        class R: parsed = outcome
        return R()


class _FakeSDK:
    def __init__(self, outcomes):
        self.models = _FakeModels(outcomes)


def test_generate_structured_returns_parsed(monkeypatch):
    client = GeminiClient.__new__(GeminiClient)
    client._client = _FakeSDK([_Out(value=42)])
    client.model = "x"
    client.max_retries = 2
    out = client.generate_structured(_Out, "prompt")
    assert out.value == 42


def test_generate_structured_retries_then_succeeds():
    client = GeminiClient.__new__(GeminiClient)
    client._client = _FakeSDK([RuntimeError("transient"), _Out(value=7)])
    client.model = "x"
    client.max_retries = 2
    out = client.generate_structured(_Out, "prompt")
    assert out.value == 7
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_llm_client.py -v`
Expected: FAIL — `ModuleNotFoundError: app.llm.client`

- [ ] **Step 3: Write `app/llm/client.py`**

```python
import time
from google import genai
from google.genai import types
from app.config import settings


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None,
                 max_retries: int = 3):
        self._client = genai.Client(api_key=api_key or settings.gemini_api_key)
        self.model = model or settings.gemini_model
        self.max_retries = max_retries

    def generate_structured(self, schema, prompt: str, temperature: float = 0.1):
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=temperature,
        )
        last_err = None
        for attempt in range(self.max_retries):
            try:
                resp = self._client.models.generate_content(
                    model=self.model, contents=prompt, config=config)
                parsed = resp.parsed
                if parsed is None:
                    raise ValueError("Gemini returned no parsable structured output")
                return parsed
            except Exception as e:  # noqa: BLE001 - retry transient/parse errors
                last_err = e
                time.sleep(0.5 * (2 ** attempt))
        raise RuntimeError(f"Gemini call failed after {self.max_retries} retries: {last_err}")
```

- [ ] **Step 4: Write `app/llm/prompts.py`** (templates; filled in per stage as those tasks land)

```python
STRUCTURE_PROMPT = """You are a legal document parser. Given the raw text of a contract,
reconstruct its clause hierarchy. Identify section numbers (e.g. 1, 1.1, (a)), headings,
the text of each clause, and any cross-references (e.g. "subject to Section 9.2").
Return the nested structure. Raw contract text:

{text}
"""

EXTRACTION_PROMPT = """You are a contract analyst. From the contract below, locate each of these
clause types: {clause_types}. For each, return whether it is present, its verbatim text, its
section location, and your confidence (0-1). If a type is absent, set present=false, text="",
confidence=0. Contract:

{text}
"""

COMPARISON_PROMPT = """You are a senior commercial lawyer. Compare this {clause_type} clause to the
market-standard baseline and classify it as favourable, unfavourable, unusual, or standard
(from the reviewing party's perspective), with a one-sentence rationale.

Market-standard baseline for {clause_type}:
{baseline}

Clause under review:
{clause_text}
"""

RISK_PROMPT = """You are a risk analyst. For this {clause_type} clause (classified as
'{classification}' vs market standard), assign a risk category (financial, operational, legal, or
reputational), a severity 0-100, and a one-sentence rationale.

Clause:
{clause_text}
Deviation rationale: {deviation_rationale}
"""

SUMMARY_PROMPT = """You are explaining a contract to a non-lawyer business owner. In plain English,
write: (1) coverage — what the contract is about; (2) who_carries_risk — which party bears more
risk and why; (3) key_commercial_terms — bullet list of the main commercial terms; (4) top_issues —
the top 3 issues to negotiate. Be concrete and avoid legalese.

Clauses and their risk findings:
{findings}
"""

BATCH_PROMPT = """Compare the following {clause_type} clauses drawn from different contracts.
Summarize the substantive differences a due-diligence reviewer would care about as a bullet list.

{cells}
"""
```

- [ ] **Step 5: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_llm_client.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/llm backend/tests/test_llm_client.py
git commit -m "feat: Gemini structured-output client with retry + prompt templates"
```

---

## Phase 2 — Ingestion

### Task 2.1: ParsedDocument + DocumentParser interface

**Files:**
- Create: `backend/app/ingestion/base.py`
- Test: `backend/tests/test_ingestion.py`

- [ ] **Step 1: Write failing test**

```python
from app.ingestion.base import ParsedDocument


def test_parsed_document_full_text_joins_blocks():
    doc = ParsedDocument(blocks=["Para one.", "Para two."], page_count=1,
                         had_text_layer=True, source="x.pdf")
    assert doc.full_text == "Para one.\nPara two."
    assert doc.is_degraded() is False


def test_parsed_document_degraded_when_almost_no_text():
    doc = ParsedDocument(blocks=[""], page_count=3, had_text_layer=False, source="x.pdf")
    assert doc.is_degraded() is True
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_ingestion.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/ingestion/base.py`**

```python
from typing import Protocol
from pydantic import BaseModel, Field


class ParsedDocument(BaseModel):
    blocks: list[str] = Field(default_factory=list)
    page_count: int = 0
    had_text_layer: bool = True
    source: str = ""

    @property
    def full_text(self) -> str:
        return "\n".join(b for b in self.blocks if b)

    def is_degraded(self) -> bool:
        """True when extraction yielded essentially no usable text."""
        return len(self.full_text.strip()) < 30 or not self.had_text_layer


class DocumentParser(Protocol):
    def parse(self, path: str) -> ParsedDocument: ...
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_ingestion.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/base.py backend/tests/test_ingestion.py
git commit -m "feat: ParsedDocument model and DocumentParser protocol"
```

### Task 2.2: DOCX parser

**Files:**
- Create: `backend/app/ingestion/docx.py`
- Test: add to `backend/tests/test_ingestion.py`

- [ ] **Step 1: Write failing test** (build a docx in-test, parse it)

```python
import docx as pydocx
from app.ingestion.docx import DocxParser


def test_docx_parser_extracts_paragraphs(tmp_path):
    p = tmp_path / "t.docx"
    d = pydocx.Document()
    d.add_paragraph("1. Indemnity")
    d.add_paragraph("The Supplier shall indemnify the Customer.")
    d.save(p)
    out = DocxParser().parse(str(p))
    assert "Indemnity" in out.full_text
    assert out.had_text_layer is True
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_ingestion.py::test_docx_parser_extracts_paragraphs -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/ingestion/docx.py`**

```python
import docx as pydocx
from app.ingestion.base import ParsedDocument


class DocxParser:
    def parse(self, path: str) -> ParsedDocument:
        d = pydocx.Document(path)
        blocks = [p.text.strip() for p in d.paragraphs if p.text and p.text.strip()]
        return ParsedDocument(blocks=blocks, page_count=1,
                              had_text_layer=True, source=path)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_ingestion.py::test_docx_parser_extracts_paragraphs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/docx.py backend/tests/test_ingestion.py
git commit -m "feat: DOCX parser"
```

### Task 2.3: PDF parser

**Files:**
- Create: `backend/app/ingestion/pdf.py`
- Test: add to `backend/tests/test_ingestion.py`

- [ ] **Step 1: Write failing test** (generate a one-page PDF with reportlab, parse it)

```python
from reportlab.pdfgen import canvas
from app.ingestion.pdf import PdfParser


def test_pdf_parser_extracts_text(tmp_path):
    p = tmp_path / "t.pdf"
    c = canvas.Canvas(str(p))
    c.drawString(72, 720, "1. Governing Law")
    c.drawString(72, 700, "This Agreement is governed by the laws of England.")
    c.save()
    out = PdfParser().parse(str(p))
    assert "Governing Law" in out.full_text
    assert out.had_text_layer is True
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_ingestion.py::test_pdf_parser_extracts_text -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/ingestion/pdf.py`**

```python
import pdfplumber
from app.ingestion.base import ParsedDocument


class PdfParser:
    def parse(self, path: str) -> ParsedDocument:
        blocks: list[str] = []
        page_count = 0
        with pdfplumber.open(path) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text() or ""
                for line in text.split("\n"):
                    if line.strip():
                        blocks.append(line.strip())
        had_text = len("".join(blocks).strip()) >= 30
        return ParsedDocument(blocks=blocks, page_count=page_count,
                              had_text_layer=had_text, source=path)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_ingestion.py::test_pdf_parser_extracts_text -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/pdf.py backend/tests/test_ingestion.py
git commit -m "feat: PDF parser (pdfplumber)"
```

### Task 2.4: Docling fallback parser

**Files:**
- Create: `backend/app/ingestion/docling_parser.py`
- Test: add to `backend/tests/test_ingestion.py` (mock docling so tests don't need models)

- [ ] **Step 1: Write failing test** (inject a fake converter to avoid heavy model load)

```python
from app.ingestion.docling_parser import DoclingParser


class _FakeDoc:
    def export_to_markdown(self):
        return "1. Indemnity\nThe Supplier shall indemnify the Customer."


class _FakeResult:
    document = _FakeDoc()


class _FakeConverter:
    def convert(self, path):
        return _FakeResult()


def test_docling_parser_uses_converter(tmp_path):
    p = tmp_path / "scan.pdf"
    p.write_bytes(b"%PDF-1.4")
    out = DoclingParser(converter=_FakeConverter()).parse(str(p))
    assert "Indemnity" in out.full_text
    assert out.had_text_layer is True
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_ingestion.py::test_docling_parser_uses_converter -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/ingestion/docling_parser.py`** (lazy-import docling so the dep is optional)

```python
from app.ingestion.base import ParsedDocument


class DoclingParser:
    def __init__(self, converter=None):
        self._converter = converter

    def _get_converter(self):
        if self._converter is None:
            from docling.document_converter import DocumentConverter
            self._converter = DocumentConverter()
        return self._converter

    def parse(self, path: str) -> ParsedDocument:
        result = self._get_converter().convert(path)
        md = result.document.export_to_markdown()
        blocks = [ln.strip() for ln in md.split("\n") if ln.strip()]
        return ParsedDocument(blocks=blocks, page_count=1,
                              had_text_layer=len("".join(blocks).strip()) >= 30,
                              source=path)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_ingestion.py::test_docling_parser_uses_converter -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/docling_parser.py backend/tests/test_ingestion.py
git commit -m "feat: Docling fallback parser (lazy import)"
```

### Task 2.5: Parser router + fallback logic

**Files:**
- Create: `backend/app/ingestion/router.py`
- Test: add to `backend/tests/test_ingestion.py`

- [ ] **Step 1: Write failing test**

```python
from app.ingestion.base import ParsedDocument
from app.ingestion.router import parse_document


class _StubParser:
    def __init__(self, doc): self.doc = doc
    def parse(self, path): return self.doc


def test_router_falls_back_when_degraded():
    degraded = ParsedDocument(blocks=[""], page_count=2, had_text_layer=False, source="s.pdf")
    good = ParsedDocument(blocks=["Real contract text here, plenty of it."],
                          page_count=2, had_text_layer=True, source="s.pdf")
    out = parse_document("s.pdf", pdf_parser=_StubParser(degraded),
                         docx_parser=_StubParser(degraded),
                         docling_parser=_StubParser(good))
    assert out.full_text.startswith("Real contract")


def test_router_keeps_primary_when_good():
    good = ParsedDocument(blocks=["Plenty of real contract text present here."],
                          page_count=1, had_text_layer=True, source="s.docx")
    sentinel = ParsedDocument(blocks=["FALLBACK"], page_count=1, had_text_layer=True, source="s")
    out = parse_document("s.docx", pdf_parser=_StubParser(good),
                         docx_parser=_StubParser(good),
                         docling_parser=_StubParser(sentinel))
    assert "FALLBACK" not in out.full_text
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_ingestion.py -k router -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/ingestion/router.py`**

```python
import os
from app.ingestion.base import ParsedDocument
from app.ingestion.pdf import PdfParser
from app.ingestion.docx import DocxParser
from app.ingestion.docling_parser import DoclingParser


def parse_document(path: str, pdf_parser=None, docx_parser=None,
                   docling_parser=None) -> ParsedDocument:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        primary = (pdf_parser or PdfParser()).parse(path)
    elif ext in (".docx", ".doc"):
        primary = (docx_parser or DocxParser()).parse(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    if primary.is_degraded():
        return (docling_parser or DoclingParser()).parse(path)
    return primary
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_ingestion.py -k router -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/router.py backend/tests/test_ingestion.py
git commit -m "feat: parser router with Docling fallback on degraded extraction"
```

### Task 2.6: Gemini structuring pass

**Files:**
- Create: `backend/app/ingestion/structure.py`
- Test: `backend/tests/test_structure.py`

- [ ] **Step 1: Write failing test** (uses mock_llm)

```python
from app.ingestion.structure import structure_document
from app.schemas.models import StructuredDocument, ClauseNode


def test_structure_document_calls_llm_and_returns_tree(mock_llm):
    mock_llm.queue_response(StructuredDocument(
        title="MSA",
        nodes=[ClauseNode(number="1", heading="Indemnity", text="...")]))
    out = structure_document("raw contract text", llm=mock_llm)
    assert out.title == "MSA"
    assert out.nodes[0].heading == "Indemnity"
    assert "raw contract text" in mock_llm.calls[0]["prompt"]
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_structure.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/ingestion/structure.py`**

```python
from app.schemas.models import StructuredDocument
from app.llm.prompts import STRUCTURE_PROMPT


def structure_document(raw_text: str, llm) -> StructuredDocument:
    prompt = STRUCTURE_PROMPT.format(text=raw_text)
    return llm.generate_structured(StructuredDocument, prompt)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_structure.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/ingestion/structure.py backend/tests/test_structure.py
git commit -m "feat: Gemini structuring pass into clause tree"
```

---

## Phase 3 — Fixtures

### Task 3.1: Synthetic fixture generator + answer keys

**Files:**
- Create: `backend/fixtures/generate.py`
- Create: `backend/fixtures/answer_keys/` (written by the script)

- [ ] **Step 1: Write `backend/fixtures/generate.py`**

Produces: `all_clauses.docx` (all 7 types, standard wording), `planted_risk.pdf` (deliberately risky), and `batch/contract_a.docx`, `batch/contract_b.docx`, `batch/contract_c.docx` (differing governing-law + liability). Writes one answer-key JSON per fixture.

```python
import json
import os
import docx as pydocx
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "generated")
KEYS = os.path.join(HERE, "answer_keys")

STANDARD_CLAUSES = {
    "indemnity": "8. Indemnity. Each party shall indemnify the other against third-party "
                 "claims arising from its own breach of this Agreement, subject to the "
                 "limitations in Section 9.",
    "limitation_of_liability": "9. Limitation of Liability. Except for breaches of "
                 "confidentiality, each party's aggregate liability shall not exceed the fees "
                 "paid in the preceding 12 months. Neither party is liable for indirect or "
                 "consequential loss.",
    "governing_law": "10. Governing Law. This Agreement is governed by the laws of England "
                 "and Wales.",
    "termination": "11. Termination. Either party may terminate on 30 days' written notice, "
                 "or immediately for material breach not cured within 14 days.",
    "ip_ownership": "12. Intellectual Property. Each party retains ownership of its "
                 "pre-existing IP. Deliverables created for the Customer are assigned to the "
                 "Customer on payment.",
    "payment_terms": "13. Payment. The Customer shall pay undisputed invoices within 30 days "
                 "of receipt. Late amounts accrue interest at 2% per annum.",
    "confidentiality": "14. Confidentiality. Each party shall protect the other's Confidential "
                 "Information and use it only for the purposes of this Agreement, for 3 years "
                 "after termination.",
}

# Deliberately problematic versions (planted risk) + the reason each is risky.
PLANTED = {
    "indemnity": ("8. Indemnity. The Customer shall indemnify, defend and hold harmless the "
                  "Supplier from any and all claims of any kind whatsoever, including the "
                  "Supplier's own negligence, without limitation.",
                  "One-sided, uncapped indemnity covering the other party's own negligence."),
    "limitation_of_liability": ("9. Limitation of Liability. The Supplier's liability is "
                  "excluded entirely and in no event shall the Supplier be liable for any "
                  "amount. The Customer waives all claims.",
                  "Supplier liability fully excluded; customer waives all remedies."),
    "termination": ("11. Termination. The Supplier may terminate at any time for any reason "
                  "with no notice. This Agreement auto-renews for successive 5-year terms "
                  "unless cancelled 180 days in advance.",
                  "Unilateral no-notice termination plus long auto-renewal lock-in."),
    "ip_ownership": ("12. Intellectual Property. All intellectual property created by either "
                  "party, including the Customer's pre-existing IP, is assigned exclusively to "
                  "the Supplier.",
                  "Customer's pre-existing IP assigned away to the Supplier."),
    "payment_terms": ("13. Payment. All fees are due immediately on invoice and are "
                  "non-refundable. The Supplier may increase fees at any time without notice.",
                  "Immediate non-refundable payment with unilateral price increases."),
    "governing_law": ("10. Governing Law. This Agreement is governed by the laws of a "
                  "jurisdiction to be nominated by the Supplier at the time of any dispute.",
                  "Governing law unilaterally chosen by one party at dispute time."),
    "confidentiality": ("14. Confidentiality. The Customer's confidential information may be "
                  "disclosed by the Supplier to any third party at the Supplier's discretion.",
                  "Confidentiality obligation effectively removed for one party."),
}


def _write_docx(path, intro, clauses: dict):
    d = pydocx.Document()
    d.add_paragraph("MASTER SERVICES AGREEMENT")
    d.add_paragraph(intro)
    for text in clauses.values():
        d.add_paragraph(text)
    d.save(path)


def _write_pdf(path, title, clauses: dict):
    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter
    y = height - 72
    c.setFont("Helvetica-Bold", 12); c.drawString(72, y, title); y -= 24
    c.setFont("Helvetica", 9)
    for text in clauses.values():
        for line in _wrap(text, 95):
            if y < 72:
                c.showPage(); c.setFont("Helvetica", 9); y = height - 72
            c.drawString(72, y, line); y -= 13
        y -= 8
    c.save()


def _wrap(text, n):
    words, line, out = text.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > n:
            out.append(line); line = w
        else:
            line = f"{line} {w}".strip()
    if line: out.append(line)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "batch"), exist_ok=True)
    os.makedirs(KEYS, exist_ok=True)

    # Fixture 1: all clause types present (metric 1)
    _write_docx(os.path.join(OUT, "all_clauses.docx"),
                "This agreement contains the standard commercial terms.", STANDARD_CLAUSES)
    json.dump({"expected_present": list(STANDARD_CLAUSES.keys())},
              open(os.path.join(KEYS, "all_clauses.json"), "w"), indent=2)

    # Fixture 2: planted risky clauses (metrics 2 & 4)
    planted_clauses = {k: v[0] for k, v in PLANTED.items()}
    _write_pdf(os.path.join(OUT, "planted_risk.pdf"), "SERVICES AGREEMENT", planted_clauses)
    json.dump({"expected_flagged": list(PLANTED.keys()),
               "reasons": {k: v[1] for k, v in PLANTED.items()}},
              open(os.path.join(KEYS, "planted_risk.json"), "w"), indent=2)

    # Fixture 3: 3-contract batch differing on governing_law + limitation_of_liability (metric 5)
    variants = {
        "contract_a": {**STANDARD_CLAUSES,
            "governing_law": "10. Governing Law. Governed by the laws of England and Wales.",
            "limitation_of_liability": "9. Limitation of Liability. Liability capped at 12 months' fees."},
        "contract_b": {**STANDARD_CLAUSES,
            "governing_law": "10. Governing Law. Governed by the laws of the State of New York.",
            "limitation_of_liability": "9. Limitation of Liability. Liability capped at 3 months' fees."},
        "contract_c": {**STANDARD_CLAUSES,
            "governing_law": "10. Governing Law. Governed by the laws of Singapore.",
            "limitation_of_liability": "9. Limitation of Liability. Liability uncapped."},
    }
    for name, clauses in variants.items():
        _write_docx(os.path.join(OUT, "batch", f"{name}.docx"),
                    "Batch comparison fixture.", clauses)
    json.dump({"clause_type": "governing_law",
               "expected_differences": ["England and Wales", "New York", "Singapore"]},
              open(os.path.join(KEYS, "batch.json"), "w"), indent=2)
    print("Fixtures written to", OUT)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the generator**

Run: `cd backend && ../legalvenv/bin/python fixtures/generate.py`
Expected: prints "Fixtures written to ...", creates `fixtures/generated/all_clauses.docx`, `planted_risk.pdf`, `batch/contract_{a,b,c}.docx`, and three answer-key JSONs.

- [ ] **Step 3: Sanity-test the fixtures parse**

Add to `backend/tests/test_ingestion.py`:

```python
import os
from app.ingestion.router import parse_document

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures", "generated")


def test_fixture_all_clauses_parses():
    out = parse_document(os.path.join(FIX, "all_clauses.docx"))
    assert "Indemnity" in out.full_text and "Confidentiality" in out.full_text


def test_fixture_planted_risk_pdf_parses():
    out = parse_document(os.path.join(FIX, "planted_risk.pdf"))
    assert "indemnify" in out.full_text.lower()
```

Run: `cd backend && ../legalvenv/bin/pytest tests/test_ingestion.py -k fixture -v`
Expected: PASS (2 tests)

- [ ] **Step 4: Commit**

```bash
git add backend/fixtures/generate.py backend/fixtures/answer_keys backend/tests/test_ingestion.py
git commit -m "feat: synthetic contract fixtures + answer keys"
```

---

## Phase 4 — Extraction Stage

### Task 4.1: Clause extraction

**Files:**
- Create: `backend/app/pipeline/extraction.py`
- Test: add to `backend/tests/test_extraction.py`

- [ ] **Step 1: Write failing test** (mock_llm returns extraction result; verify all 7 normalized)

```python
from app.pipeline.extraction import extract_clauses
from app.schemas.models import ClauseExtractionResult, ExtractedClause
from app.clause_types import ClauseType, ALL_CLAUSE_TYPES


def test_extract_normalizes_to_all_seven_types(mock_llm):
    # LLM returns only 2 clauses; extractor must backfill the rest as not-present.
    mock_llm.queue_response(ClauseExtractionResult(clauses=[
        ExtractedClause(type=ClauseType.INDEMNITY, present=True, text="...",
                        location="8", confidence=0.9),
        ExtractedClause(type=ClauseType.GOVERNING_LAW, present=True, text="...",
                        location="10", confidence=0.8),
    ]))
    result = extract_clauses("contract text", llm=mock_llm)
    assert len(result) == 7
    by_type = {c.type: c for c in result}
    assert all(t in by_type for t in ALL_CLAUSE_TYPES)
    assert by_type[ClauseType.TERMINATION].present is False
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_extraction.py::test_extract_normalizes_to_all_seven_types -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/pipeline/extraction.py`**

```python
from app.schemas.models import ClauseExtractionResult, ExtractedClause
from app.clause_types import ALL_CLAUSE_TYPES
from app.llm.prompts import EXTRACTION_PROMPT


def extract_clauses(text: str, llm) -> list[ExtractedClause]:
    types_str = ", ".join(t.value for t in ALL_CLAUSE_TYPES)
    prompt = EXTRACTION_PROMPT.format(clause_types=types_str, text=text)
    result: ClauseExtractionResult = llm.generate_structured(ClauseExtractionResult, prompt)

    found = {c.type: c for c in result.clauses}
    normalized = []
    for t in ALL_CLAUSE_TYPES:
        if t in found:
            normalized.append(found[t])
        else:
            normalized.append(ExtractedClause(type=t, present=False, text="",
                                              location=None, confidence=0.0))
    return normalized
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_extraction.py -v`
Expected: PASS (all tests in file)

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/extraction.py backend/tests/test_extraction.py
git commit -m "feat: clause extraction stage (normalizes to all 7 types)"
```

---

## Phase 5 — Comparison Stage

### Task 5.1: Baseline loader

**Files:**
- Create: `backend/app/baseline/market_standard.json`, `backend/app/baseline/loader.py`
- Test: `backend/tests/test_baseline.py`

- [ ] **Step 1: Write `app/baseline/market_standard.json`**

```json
{
  "indemnity": "Mutual indemnity limited to third-party claims arising from each party's own breach, subject to the liability cap.",
  "limitation_of_liability": "Mutual cap at 12 months' fees; exclusion of indirect/consequential loss; carve-outs for confidentiality and IP.",
  "governing_law": "A neutral, well-established jurisdiction (e.g. England and Wales or Delaware) chosen at signing, not at dispute time.",
  "termination": "Termination for convenience on 30+ days' notice and for uncured material breach; no long auto-renewal lock-in.",
  "ip_ownership": "Each party retains pre-existing IP; deliverables assigned to the customer on payment.",
  "payment_terms": "Net 30 on undisputed invoices; reasonable late interest; no unilateral price increases.",
  "confidentiality": "Mutual confidentiality with defined purpose and a 3-5 year survival period."
}
```

- [ ] **Step 2: Write failing test**

```python
from app.baseline.loader import load_baseline, save_baseline
from app.clause_types import ALL_CLAUSE_TYPES


def test_baseline_has_entry_for_every_clause_type():
    b = load_baseline()
    for t in ALL_CLAUSE_TYPES:
        assert t.value in b and b[t.value]


def test_save_and_reload_baseline(tmp_path):
    path = tmp_path / "b.json"
    save_baseline({"indemnity": "custom"}, path=str(path))
    assert load_baseline(path=str(path))["indemnity"] == "custom"
```

- [ ] **Step 3: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_baseline.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 4: Write `app/baseline/loader.py`**

```python
import json
import os

_DEFAULT = os.path.join(os.path.dirname(__file__), "market_standard.json")


def load_baseline(path: str = _DEFAULT) -> dict[str, str]:
    with open(path) as f:
        return json.load(f)


def save_baseline(data: dict[str, str], path: str = _DEFAULT) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
```

- [ ] **Step 5: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_baseline.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add backend/app/baseline backend/tests/test_baseline.py
git commit -m "feat: configurable market-standard baseline + loader"
```

### Task 5.2: Deviation classifier

**Files:**
- Create: `backend/app/pipeline/comparison.py`
- Test: `backend/tests/test_comparison.py`

- [ ] **Step 1: Write failing test**

```python
from app.pipeline.comparison import compare_clause
from app.schemas.models import ExtractedClause, DeviationResult
from app.clause_types import ClauseType


def test_compare_present_clause_calls_llm(mock_llm):
    mock_llm.queue_response(DeviationResult(classification="unfavourable",
                            rationale="One-sided.", baseline_ref="indemnity"))
    clause = ExtractedClause(type=ClauseType.INDEMNITY, present=True,
                             text="Customer indemnifies everything.", location="8", confidence=0.9)
    out = compare_clause(clause, {"indemnity": "Mutual..."}, llm=mock_llm)
    assert out.classification == "unfavourable"


def test_compare_absent_clause_skips_llm(mock_llm):
    clause = ExtractedClause(type=ClauseType.TERMINATION, present=False, text="",
                             location=None, confidence=0.0)
    out = compare_clause(clause, {"termination": "..."}, llm=mock_llm)
    assert out is None
    assert mock_llm.calls == []
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_comparison.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/pipeline/comparison.py`**

```python
from typing import Optional
from app.schemas.models import ExtractedClause, DeviationResult
from app.llm.prompts import COMPARISON_PROMPT


def compare_clause(clause: ExtractedClause, baseline: dict[str, str],
                   llm) -> Optional[DeviationResult]:
    if not clause.present:
        return None
    prompt = COMPARISON_PROMPT.format(
        clause_type=clause.type.value,
        baseline=baseline.get(clause.type.value, "(no baseline defined)"),
        clause_text=clause.text)
    return llm.generate_structured(DeviationResult, prompt)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_comparison.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/comparison.py backend/tests/test_comparison.py
git commit -m "feat: market-standard deviation classifier"
```

---

## Phase 6 — Risk Scoring

### Task 6.1: Per-clause risk + deterministic aggregation

**Files:**
- Create: `backend/app/pipeline/risk.py`
- Test: `backend/tests/test_risk.py`

- [ ] **Step 1: Write failing test** (LLM gives per-clause components; aggregation is pure math)

```python
from app.pipeline.risk import score_clause, aggregate_risk, ClauseRisk
from app.schemas.models import ExtractedClause, DeviationResult, RiskComponent
from app.clause_types import ClauseType


def test_score_clause_combines_llm_component(mock_llm):
    mock_llm.queue_response(RiskComponent(category="legal", severity=80,
                            rationale="Uncapped liability."))
    clause = ExtractedClause(type=ClauseType.LIMITATION_OF_LIABILITY, present=True,
                             text="Uncapped.", location="9", confidence=0.9)
    dev = DeviationResult(classification="unfavourable", rationale="No cap.",
                          baseline_ref="limitation_of_liability")
    cr = score_clause(clause, dev, llm=mock_llm)
    assert cr.category == "legal"
    # unfavourable deviation multiplies severity by 1.25, capped at 100
    assert cr.score == 100


def test_aggregate_uses_weighted_top_scores():
    risks = [
        ClauseRisk(clause_type="indemnity", category="legal", score=90, rationale="x"),
        ClauseRisk(clause_type="payment_terms", category="financial", score=40, rationale="y"),
    ]
    overall, breakdown = aggregate_risk(risks)
    assert breakdown["legal"] == 90
    assert breakdown["financial"] == 40
    # overall is severity-weighted mean biased to the worst clause; must lie in [40, 90]
    assert 40 <= overall <= 90
    assert overall > 65  # worst-case bias
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_risk.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/pipeline/risk.py`**

```python
from typing import Optional
from pydantic import BaseModel
from app.schemas.models import ExtractedClause, DeviationResult, RiskComponent, RiskCategory
from app.llm.prompts import RISK_PROMPT

# Deviation classification multipliers (deterministic, explainable).
_DEVIATION_WEIGHT = {
    "favourable": 0.7,
    "standard": 1.0,
    "unusual": 1.15,
    "unfavourable": 1.25,
}


class ClauseRisk(BaseModel):
    clause_type: str
    category: RiskCategory
    score: int
    rationale: str


def score_clause(clause: ExtractedClause, deviation: Optional[DeviationResult],
                 llm) -> ClauseRisk:
    classification = deviation.classification if deviation else "standard"
    dev_rationale = deviation.rationale if deviation else "No deviation assessed."
    prompt = RISK_PROMPT.format(clause_type=clause.type.value,
                                classification=classification,
                                clause_text=clause.text,
                                deviation_rationale=dev_rationale)
    comp: RiskComponent = llm.generate_structured(RiskComponent, prompt)
    weighted = comp.severity * _DEVIATION_WEIGHT.get(classification, 1.0)
    score = max(0, min(100, round(weighted)))
    return ClauseRisk(clause_type=clause.type.value, category=comp.category,
                      score=score, rationale=comp.rationale)


def aggregate_risk(risks: list[ClauseRisk]) -> tuple[int, dict[str, int]]:
    """Overall = worst-biased weighted mean; breakdown = max score per category."""
    breakdown: dict[str, int] = {}
    for r in risks:
        breakdown[r.category] = max(breakdown.get(r.category, 0), r.score)
    if not risks:
        return 0, breakdown
    scores = sorted((r.score for r in risks), reverse=True)
    # Weight higher scores more heavily so one severe clause drives the headline.
    weights = [len(scores) - i for i in range(len(scores))]
    overall = round(sum(s * w for s, w in zip(scores, weights)) / sum(weights))
    return overall, breakdown
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_risk.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/risk.py backend/tests/test_risk.py
git commit -m "feat: per-clause risk scoring + deterministic aggregation"
```

---

## Phase 7 — Summary Stage

### Task 7.1: Executive summary generator

**Files:**
- Create: `backend/app/pipeline/summary.py`
- Test: `backend/tests/test_summary.py`

- [ ] **Step 1: Write failing test**

```python
from app.pipeline.summary import generate_summary
from app.pipeline.risk import ClauseRisk
from app.schemas.models import ExecutiveSummary, ExtractedClause
from app.clause_types import ClauseType


def test_generate_summary_passes_findings_and_returns_top3(mock_llm):
    mock_llm.queue_response(ExecutiveSummary(
        coverage="A services agreement.",
        who_carries_risk="The customer carries more risk.",
        key_commercial_terms=["Net 30", "12-month cap"],
        top_issues=["Uncapped indemnity", "Auto-renewal", "Unilateral termination"]))
    clauses = [ExtractedClause(type=ClauseType.INDEMNITY, present=True, text="...",
                               location="8", confidence=0.9)]
    risks = [ClauseRisk(clause_type="indemnity", category="legal", score=90, rationale="x")]
    out = generate_summary(clauses, risks, llm=mock_llm)
    assert len(out.top_issues) == 3
    assert "indemnity" in mock_llm.calls[0]["prompt"].lower()
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_summary.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/pipeline/summary.py`**

```python
from app.schemas.models import ExecutiveSummary, ExtractedClause
from app.pipeline.risk import ClauseRisk
from app.llm.prompts import SUMMARY_PROMPT


def generate_summary(clauses: list[ExtractedClause], risks: list[ClauseRisk],
                     llm) -> ExecutiveSummary:
    risk_by_type = {r.clause_type: r for r in risks}
    lines = []
    for c in clauses:
        if not c.present:
            lines.append(f"- {c.type.value}: NOT PRESENT")
            continue
        r = risk_by_type.get(c.type.value)
        score = r.score if r else "n/a"
        lines.append(f"- {c.type.value} (risk {score}): {c.text[:300]}")
    findings = "\n".join(lines)
    prompt = SUMMARY_PROMPT.format(findings=findings)
    return llm.generate_structured(ExecutiveSummary, prompt)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_summary.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/summary.py backend/tests/test_summary.py
git commit -m "feat: plain-English executive summary stage"
```

---

## Phase 8 — Orchestration, DB & API

### Task 8.1: Pipeline runner (stages 1-5)

**Files:**
- Create: `backend/app/pipeline/runner.py`
- Test: `backend/tests/test_runner.py`

- [ ] **Step 1: Write failing test** (queue one response per LLM call in pipeline order)

```python
from app.pipeline.runner import run_pipeline
from app.schemas.models import (StructuredDocument, ClauseExtractionResult, ExtractedClause,
                                 DeviationResult, RiskComponent, ExecutiveSummary)
from app.clause_types import ClauseType, ALL_CLAUSE_TYPES


def test_run_pipeline_produces_full_analysis(mock_llm, tmp_path):
    # 1 structuring
    mock_llm.queue_response(StructuredDocument(title="MSA", nodes=[]))
    # 2 extraction: mark all 7 present so 7 comparison + 7 risk calls follow
    mock_llm.queue_response(ClauseExtractionResult(clauses=[
        ExtractedClause(type=t, present=True, text=f"{t.value} text",
                        location="1", confidence=0.9) for t in ALL_CLAUSE_TYPES]))
    # 3 comparison x7
    for _ in ALL_CLAUSE_TYPES:
        mock_llm.queue_response(DeviationResult(classification="standard",
                                rationale="ok", baseline_ref="x"))
    # 4 risk x7
    for _ in ALL_CLAUSE_TYPES:
        mock_llm.queue_response(RiskComponent(category="legal", severity=20, rationale="low"))
    # 5 summary
    mock_llm.queue_response(ExecutiveSummary(coverage="c", who_carries_risk="w",
                            key_commercial_terms=["t"], top_issues=["a", "b", "c"]))

    fixture = tmp_path / "c.docx"
    import docx as pydocx
    d = pydocx.Document(); d.add_paragraph("Some contract text long enough to parse."); d.save(fixture)

    analysis = run_pipeline(str(fixture), llm=mock_llm)
    assert len(analysis.clauses) == 7
    assert len(analysis.deviations) == 7
    assert analysis.overall_risk_score >= 0
    assert len(analysis.summary.top_issues) == 3
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_runner.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/pipeline/runner.py`**

```python
from pydantic import BaseModel
from app.ingestion.router import parse_document
from app.ingestion.structure import structure_document
from app.pipeline.extraction import extract_clauses
from app.pipeline.comparison import compare_clause
from app.pipeline.risk import score_clause, aggregate_risk, ClauseRisk
from app.pipeline.summary import generate_summary
from app.baseline.loader import load_baseline
from app.schemas.models import (StructuredDocument, ExtractedClause, DeviationResult,
                                 ExecutiveSummary)


class AnalysisResult(BaseModel):
    structure: StructuredDocument
    clauses: list[ExtractedClause]
    deviations: list[dict]   # {clause_type, classification, rationale} for present clauses
    risks: list[ClauseRisk]
    overall_risk_score: int
    category_breakdown: dict[str, int]
    summary: ExecutiveSummary


def run_pipeline(file_path: str, llm) -> AnalysisResult:
    parsed = parse_document(file_path)
    structure = structure_document(parsed.full_text, llm)
    clauses = extract_clauses(parsed.full_text, llm)

    baseline = load_baseline()
    deviations: list[dict] = []
    risks: list[ClauseRisk] = []
    for clause in clauses:
        dev: DeviationResult | None = None
        if clause.present:
            try:
                dev = compare_clause(clause, baseline, llm)
            except Exception as e:  # per-clause isolation
                dev = None
            if dev:
                deviations.append({"clause_type": clause.type.value,
                                   "classification": dev.classification,
                                   "rationale": dev.rationale})
            try:
                risks.append(score_clause(clause, dev, llm))
            except Exception:
                pass

    overall, breakdown = aggregate_risk(risks)
    summary = generate_summary(clauses, risks, llm)
    return AnalysisResult(structure=structure, clauses=clauses, deviations=deviations,
                          risks=risks, overall_risk_score=overall,
                          category_breakdown=breakdown, summary=summary)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_runner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/pipeline/runner.py backend/tests/test_runner.py
git commit -m "feat: pipeline runner orchestrating stages 1-5 with per-clause isolation"
```

### Task 8.2: DB models + engine

**Files:**
- Create: `backend/app/db/models.py`, `backend/app/db/engine.py`
- Test: `backend/tests/test_db.py`

> **Design note (deviation from spec §5):** the spec sketched normalized tables (Clause, Deviation, RiskScore, Analysis). For this PoC we store the full analysis as a JSON column on the `Contract` row instead. Every consumer — the `GET /contracts/{id}` response, the batch-compare assembler, and the frontend — already reads the analysis as one nested object, so the JSON blob removes join/serialization overhead with no loss of capability. Normalizing later is a clean migration if needed.

- [ ] **Step 1: Write failing test**

```python
from sqlmodel import Session
from app.db.engine import make_engine, init_db
from app.db.models import Contract


def test_contract_persists(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path/'t.db'}")
    init_db(engine)
    with Session(engine) as s:
        c = Contract(filename="x.pdf", file_path="/tmp/x.pdf", format="pdf", status="uploaded")
        s.add(c); s.commit(); s.refresh(c)
        assert c.id is not None and c.status == "uploaded"
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/db/models.py`**

```python
from typing import Optional
from sqlmodel import SQLModel, Field, Column, JSON


class Contract(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    file_path: str
    format: str
    status: str = "uploaded"          # uploaded|processing|done|failed
    error: Optional[str] = None
    analysis: Optional[dict] = Field(default=None, sa_column=Column(JSON))
```

- [ ] **Step 4: Write `app/db/engine.py`**

```python
from sqlmodel import SQLModel, create_engine, Session
from app.config import settings

_engine = None


def make_engine(url: str | None = None):
    return create_engine(url or f"sqlite:///{settings.db_path}",
                         connect_args={"check_same_thread": False})


def init_db(engine=None):
    global _engine
    # Idempotent: an explicit engine (tests) always wins; the FastAPI startup
    # call (engine=None) must NOT clobber an already-configured engine.
    if engine is not None:
        _engine = engine
    elif _engine is None:
        _engine = make_engine()
    SQLModel.metadata.create_all(_engine)
    return _engine


def get_session():
    global _engine
    if _engine is None:
        init_db()
    with Session(_engine) as session:
        yield session
```

- [ ] **Step 5: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_db.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/db backend/tests/test_db.py
git commit -m "feat: SQLite models and engine"
```

### Task 8.3: FastAPI app + contract endpoints (upload/analyze/get/list)

**Files:**
- Create: `backend/app/main.py`, `backend/app/api/contracts.py`
- Test: `backend/tests/test_api.py`

- [ ] **Step 1: Write failing test** (TestClient; monkeypatch the runner so no real LLM)

```python
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
    assert r.status_code == 200  # background task runs synchronously under TestClient

    r = client.get(f"/contracts/{cid}")
    body = r.json()
    assert body["status"] == "done"
    assert body["analysis"]["overall_risk_score"] == 42
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/api/contracts.py`**

```python
import os
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends, HTTPException
from sqlmodel import Session, select
from app.db.engine import get_session
from app.db.models import Contract
from app.pipeline.runner import run_pipeline
from app.config import settings


def get_llm():
    from app.llm.client import GeminiClient
    return GeminiClient()


router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("")
def upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
    os.makedirs(settings.upload_dir, exist_ok=True)
    dest = os.path.join(settings.upload_dir, file.filename)
    with open(dest, "wb") as f:
        f.write(file.file.read())
    fmt = os.path.splitext(file.filename)[1].lstrip(".").lower()
    c = Contract(filename=file.filename, file_path=dest, format=fmt, status="uploaded")
    session.add(c); session.commit(); session.refresh(c)
    return {"id": c.id, "filename": c.filename, "status": c.status}


def _run_analysis(contract_id: int):
    from app.db.engine import _engine
    with Session(_engine) as session:
        c = session.get(Contract, contract_id)
        c.status = "processing"; session.add(c); session.commit()
        try:
            result = run_pipeline(c.file_path, get_llm())
            c.analysis = result.model_dump()
            c.status = "done"
        except Exception as e:  # noqa: BLE001
            c.status = "failed"; c.error = str(e)
        session.add(c); session.commit()


@router.post("/{contract_id}/analyze")
def analyze(contract_id: int, background: BackgroundTasks,
            session: Session = Depends(get_session)):
    c = session.get(Contract, contract_id)
    if not c:
        raise HTTPException(404, "contract not found")
    background.add_task(_run_analysis, contract_id)
    return {"id": contract_id, "status": "processing"}


@router.get("/{contract_id}")
def get_contract(contract_id: int, session: Session = Depends(get_session)):
    c = session.get(Contract, contract_id)
    if not c:
        raise HTTPException(404, "contract not found")
    return {"id": c.id, "filename": c.filename, "status": c.status,
            "error": c.error, "analysis": c.analysis}


@router.get("")
def list_contracts(session: Session = Depends(get_session)):
    rows = session.exec(select(Contract)).all()
    return [{"id": c.id, "filename": c.filename, "status": c.status,
             "overall_risk_score": (c.analysis or {}).get("overall_risk_score")} for c in rows]
```

- [ ] **Step 4: Write `app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.engine import init_db
from app.api import contracts


def create_app() -> FastAPI:
    app = FastAPI(title="Contract Analysis Platform")
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                       allow_methods=["*"], allow_headers=["*"])

    @app.on_event("startup")
    def _startup():
        init_db()

    app.include_router(contracts.router)
    return app


app = create_app()
```

- [ ] **Step 5: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/app/api/contracts.py backend/tests/test_api.py
git commit -m "feat: FastAPI app with upload/analyze/get/list endpoints"
```

### Task 8.4: Baseline endpoints

**Files:**
- Create: `backend/app/api/baseline.py`
- Modify: `backend/app/main.py` (include router)
- Test: add to `backend/tests/test_api.py`

- [ ] **Step 1: Write failing test**

```python
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
```

(Note: this test writes to the real `market_standard.json`. The endpoint accepts an optional path; in the test, set env `BASELINE_PATH` via monkeypatch if isolation is needed. For the demo, mutating the default file is acceptable; restore with `git checkout` after.)

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_api.py -k baseline -v`
Expected: FAIL — 404 (route not registered)

- [ ] **Step 3: Write `app/api/baseline.py`**

```python
from fastapi import APIRouter
from app.baseline.loader import load_baseline, save_baseline

router = APIRouter(prefix="/baseline", tags=["baseline"])


@router.get("")
def get_baseline():
    return load_baseline()


@router.put("")
def put_baseline(data: dict[str, str]):
    save_baseline(data)
    return {"status": "ok", "count": len(data)}
```

- [ ] **Step 4: Register the router in `app/main.py`**

```python
from app.api import contracts, baseline
# ... inside create_app, after contracts:
    app.include_router(baseline.router)
```

- [ ] **Step 5: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_api.py -k baseline -v`
Then restore the file: `git checkout backend/app/baseline/market_standard.json`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/baseline.py backend/app/main.py backend/tests/test_api.py
git commit -m "feat: baseline get/put endpoints"
```

---

## Phase 9 — Batch Comparison

### Task 9.1: Batch comparison stage + endpoint

**Files:**
- Create: `backend/app/pipeline/batch.py`, `backend/app/api/compare.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_batch.py`

- [ ] **Step 1: Write failing test** (pure assembly from stored analyses + LLM diff)

```python
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
```

- [ ] **Step 2: Run to verify fails**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_batch.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write `app/pipeline/batch.py`**

```python
from app.schemas.models import BatchComparison, BatchCell
from app.clause_types import ClauseType
from app.llm.prompts import BATCH_PROMPT


def build_batch_comparison(stored: list[dict], clause_type: ClauseType, llm) -> BatchComparison:
    cells: list[BatchCell] = []
    for item in stored:
        analysis = item.get("analysis") or {}
        clause = next((c for c in analysis.get("clauses", [])
                       if c["type"] == clause_type.value), None)
        dev = next((d for d in analysis.get("deviations", [])
                    if d["clause_type"] == clause_type.value), None)
        risk = next((r for r in analysis.get("risks", [])
                     if r["clause_type"] == clause_type.value), None)
        cells.append(BatchCell(
            contract_id=item["id"], contract_name=item["name"],
            present=bool(clause and clause.get("present")),
            text=(clause or {}).get("text", ""),
            classification=(dev or {}).get("classification"),
            risk_score=(risk or {}).get("score")))

    cell_text = "\n\n".join(f"{c.contract_name}: {c.text or '(not present)'}" for c in cells)
    prompt = BATCH_PROMPT.format(clause_type=clause_type.value, cells=cell_text)
    diff: BatchComparison = llm.generate_structured(BatchComparison, prompt)
    return BatchComparison(clause_type=clause_type, cells=cells,
                           differences=diff.differences)
```

- [ ] **Step 4: Write `app/api/compare.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.db.engine import get_session
from app.db.models import Contract
from app.clause_types import ClauseType
from app.pipeline.batch import build_batch_comparison
from app.api.contracts import get_llm

router = APIRouter(prefix="/compare", tags=["compare"])


class CompareRequest(BaseModel):
    contract_ids: list[int]
    clause_type: ClauseType


@router.post("")
def compare(req: CompareRequest, session: Session = Depends(get_session)):
    stored = []
    for cid in req.contract_ids:
        c = session.get(Contract, cid)
        if not c or c.status != "done":
            raise HTTPException(400, f"contract {cid} not analyzed")
        stored.append({"id": c.id, "name": c.filename, "analysis": c.analysis})
    result = build_batch_comparison(stored, req.clause_type, get_llm())
    return result.model_dump()
```

- [ ] **Step 5: Register router in `app/main.py`** (`from app.api import contracts, baseline, compare` and `app.include_router(compare.router)`)

- [ ] **Step 6: Run to verify pass**

Run: `cd backend && ../legalvenv/bin/pytest tests/test_batch.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/pipeline/batch.py backend/app/api/compare.py backend/app/main.py backend/tests/test_batch.py
git commit -m "feat: cross-contract batch clause comparison"
```

---

## Phase 10 — Frontend

### Task 10.1: Vite + React + TS + Tailwind scaffold

**Files:**
- Create: `frontend/` via Vite
- Test: build succeeds

- [ ] **Step 1: Scaffold**

Run: `npm create vite@latest frontend -- --template react-ts && cd frontend && npm install`
Expected: project created, deps installed.

- [ ] **Step 2: Add Tailwind**

Run: `cd frontend && npm install -D tailwindcss@3 postcss autoprefixer && npx tailwindcss init -p`
Then set `content: ["./index.html","./src/**/*.{ts,tsx}"]` in `tailwind.config.js` and put the three `@tailwind` directives in `src/index.css`.

- [ ] **Step 3: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds with no type errors.

- [ ] **Step 4: Commit**

```bash
git add frontend
git commit -m "chore: frontend scaffold (Vite + React + TS + Tailwind)"
```

### Task 10.2: API client + types

**Files:**
- Create: `frontend/src/types.ts`, `frontend/src/api/client.ts`

- [ ] **Step 1: Write `frontend/src/types.ts`** (mirror backend response shapes)

```typescript
export type ClauseType =
  | "indemnity" | "limitation_of_liability" | "governing_law" | "termination"
  | "ip_ownership" | "payment_terms" | "confidentiality";

export interface ExtractedClause {
  type: ClauseType; present: boolean; text: string;
  location: string | null; confidence: number;
}
export interface Deviation {
  clause_type: ClauseType; classification: string; rationale: string;
}
export interface ClauseRisk {
  clause_type: ClauseType; category: string; score: number; rationale: string;
}
export interface ExecutiveSummary {
  coverage: string; who_carries_risk: string;
  key_commercial_terms: string[]; top_issues: string[];
}
export interface Analysis {
  clauses: ExtractedClause[]; deviations: Deviation[]; risks: ClauseRisk[];
  overall_risk_score: number; category_breakdown: Record<string, number>;
  summary: ExecutiveSummary;
}
export interface ContractDetail {
  id: number; filename: string; status: string;
  error: string | null; analysis: Analysis | null;
}
```

- [ ] **Step 2: Write `frontend/src/api/client.ts`**

```typescript
const BASE = "http://localhost:8000";

export async function uploadContract(file: File) {
  const fd = new FormData(); fd.append("file", file);
  const r = await fetch(`${BASE}/contracts`, { method: "POST", body: fd });
  return r.json() as Promise<{ id: number; filename: string; status: string }>;
}
export async function analyzeContract(id: number) {
  await fetch(`${BASE}/contracts/${id}/analyze`, { method: "POST" });
}
export async function getContract(id: number) {
  const r = await fetch(`${BASE}/contracts/${id}`);
  return r.json();
}
export async function listContracts() {
  const r = await fetch(`${BASE}/contracts`);
  return r.json();
}
export async function compareClause(contract_ids: number[], clause_type: string) {
  const r = await fetch(`${BASE}/compare`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ contract_ids, clause_type }) });
  return r.json();
}
export async function getBaseline() { return (await fetch(`${BASE}/baseline`)).json(); }
```

- [ ] **Step 3: Verify typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/client.ts
git commit -m "feat: frontend API client and types"
```

### Task 10.3: Components — RiskGauge, DeviationBadge, ClauseCard

**Files:**
- Create: `frontend/src/components/RiskGauge.tsx`, `DeviationBadge.tsx`, `ClauseCard.tsx`

- [ ] **Step 1: Write `RiskGauge.tsx`**

```tsx
export function RiskGauge({ score }: { score: number }) {
  const color = score >= 67 ? "text-red-600" : score >= 34 ? "text-amber-500" : "text-green-600";
  const label = score >= 67 ? "High" : score >= 34 ? "Medium" : "Low";
  return (
    <div className="flex flex-col items-center p-4 rounded-xl border">
      <div className={`text-5xl font-bold ${color}`}>{score}</div>
      <div className="text-sm text-gray-500">Overall risk · {label}</div>
    </div>
  );
}
```

- [ ] **Step 2: Write `DeviationBadge.tsx`**

```tsx
const STYLES: Record<string, string> = {
  favourable: "bg-green-100 text-green-800",
  standard: "bg-gray-100 text-gray-700",
  unusual: "bg-amber-100 text-amber-800",
  unfavourable: "bg-red-100 text-red-800",
};
export function DeviationBadge({ classification }: { classification?: string }) {
  if (!classification) return null;
  return <span className={`px-2 py-0.5 rounded text-xs font-medium ${STYLES[classification] ?? ""}`}>
    {classification}</span>;
}
```

- [ ] **Step 3: Write `ClauseCard.tsx`**

```tsx
import { ExtractedClause, Deviation, ClauseRisk } from "../types";
import { DeviationBadge } from "./DeviationBadge";

export function ClauseCard({ clause, deviation, risk }:
  { clause: ExtractedClause; deviation?: Deviation; risk?: ClauseRisk }) {
  if (!clause.present)
    return <div className="p-3 rounded border text-gray-400">
      {clause.type} — not present</div>;
  return (
    <div className="p-4 rounded-xl border space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold capitalize">{clause.type.replace(/_/g, " ")}</h3>
        <div className="flex items-center gap-2">
          <DeviationBadge classification={deviation?.classification} />
          {risk && <span className="text-sm font-bold">{risk.score}</span>}
        </div>
      </div>
      <p className="text-sm text-gray-700">{clause.text}</p>
      {deviation && <p className="text-xs text-gray-500 italic">{deviation.rationale}</p>}
    </div>
  );
}
```

- [ ] **Step 4: Verify typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components
git commit -m "feat: RiskGauge, DeviationBadge, ClauseCard components"
```

### Task 10.4: Pages — Library, Analysis, Summary, BatchCompare + routing

**Files:**
- Create: `frontend/src/pages/Library.tsx`, `Analysis.tsx`, `Summary.tsx`, `BatchCompare.tsx`
- Modify: `frontend/src/App.tsx`, install `react-router-dom`

- [ ] **Step 1: Install router**

Run: `cd frontend && npm install react-router-dom`

- [ ] **Step 2: Write `Library.tsx`** (upload + poll status + list)

```tsx
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { uploadContract, analyzeContract, listContracts, getContract } from "../api/client";

export function Library() {
  const [rows, setRows] = useState<any[]>([]);
  const refresh = () => listContracts().then(setRows);
  useEffect(() => { refresh(); const t = setInterval(refresh, 2000); return () => clearInterval(t); }, []);

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return;
    const { id } = await uploadContract(file);
    await analyzeContract(id); refresh();
  }
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Contract Library</h1>
      <input type="file" accept=".pdf,.docx" onChange={onUpload} />
      <ul className="divide-y border rounded-xl">
        {rows.map(r => (
          <li key={r.id} className="flex justify-between p-3">
            <Link className="text-blue-600" to={`/contracts/${r.id}`}>{r.filename}</Link>
            <span className="text-sm text-gray-500">{r.status}
              {r.overall_risk_score != null && ` · risk ${r.overall_risk_score}`}</span>
          </li>
        ))}
      </ul>
      <Link to="/compare" className="inline-block text-blue-600">→ Batch compare</Link>
    </div>
  );
}
```

- [ ] **Step 3: Write `Analysis.tsx`** (poll until done, render gauge + clause cards + link to summary)

```tsx
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getContract } from "../api/client";
import { ContractDetail } from "../types";
import { RiskGauge } from "../components/RiskGauge";
import { ClauseCard } from "../components/ClauseCard";

export function Analysis() {
  const { id } = useParams();
  const [c, setC] = useState<ContractDetail | null>(null);
  useEffect(() => {
    const poll = () => getContract(Number(id)).then(setC);
    poll(); const t = setInterval(poll, 2000); return () => clearInterval(t);
  }, [id]);
  if (!c) return <div className="p-6">Loading…</div>;
  if (c.status !== "done") return <div className="p-6">Status: {c.status} {c.error}</div>;
  const a = c.analysis!;
  const devBy = Object.fromEntries(a.deviations.map(d => [d.clause_type, d]));
  const riskBy = Object.fromEntries(a.risks.map(r => [r.clause_type, r]));
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{c.filename}</h1>
        <Link className="text-blue-600" to={`/contracts/${id}/summary`}>Executive summary →</Link>
      </div>
      <RiskGauge score={a.overall_risk_score} />
      <div className="grid grid-cols-2 gap-2 text-sm">
        {Object.entries(a.category_breakdown).map(([k, v]) =>
          <div key={k} className="flex justify-between border rounded px-3 py-1">
            <span className="capitalize">{k}</span><span className="font-bold">{v}</span></div>)}
      </div>
      <div className="space-y-3">
        {a.clauses.map(cl => <ClauseCard key={cl.type} clause={cl}
          deviation={devBy[cl.type]} risk={riskBy[cl.type]} />)}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Write `Summary.tsx`**

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getContract } from "../api/client";
import { ContractDetail } from "../types";

export function Summary() {
  const { id } = useParams();
  const [c, setC] = useState<ContractDetail | null>(null);
  useEffect(() => { getContract(Number(id)).then(setC); }, [id]);
  const s = c?.analysis?.summary;
  if (!s) return <div className="p-6">No summary yet.</div>;
  return (
    <div className="max-w-2xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Executive Summary</h1>
      <section><h2 className="font-semibold">What it covers</h2><p>{s.coverage}</p></section>
      <section><h2 className="font-semibold">Who carries the risk</h2><p>{s.who_carries_risk}</p></section>
      <section><h2 className="font-semibold">Key commercial terms</h2>
        <ul className="list-disc ml-5">{s.key_commercial_terms.map((t, i) => <li key={i}>{t}</li>)}</ul></section>
      <section><h2 className="font-semibold">Top 3 issues to negotiate</h2>
        <ol className="list-decimal ml-5">{s.top_issues.map((t, i) => <li key={i}>{t}</li>)}</ol></section>
    </div>
  );
}
```

- [ ] **Step 5: Write `BatchCompare.tsx`** (pick contracts + clause type, render side-by-side columns)

```tsx
import { useEffect, useState } from "react";
import { listContracts, compareClause } from "../api/client";

const CLAUSE_TYPES = ["indemnity","limitation_of_liability","governing_law","termination",
  "ip_ownership","payment_terms","confidentiality"];

export function BatchCompare() {
  const [rows, setRows] = useState<any[]>([]);
  const [picked, setPicked] = useState<number[]>([]);
  const [clause, setClause] = useState(CLAUSE_TYPES[2]);
  const [result, setResult] = useState<any>(null);
  useEffect(() => { listContracts().then(rs => setRows(rs.filter((r:any)=>r.status==="done"))); }, []);

  const toggle = (id: number) =>
    setPicked(p => p.includes(id) ? p.filter(x => x !== id) : [...p, id]);

  async function run() { setResult(await compareClause(picked, clause)); }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-bold">Batch Clause Comparison</h1>
      <div className="flex flex-wrap gap-2">
        {rows.map(r => <button key={r.id} onClick={() => toggle(r.id)}
          className={`px-3 py-1 rounded border ${picked.includes(r.id) ? "bg-blue-600 text-white" : ""}`}>
          {r.filename}</button>)}
      </div>
      <select value={clause} onChange={e => setClause(e.target.value)} className="border rounded p-2">
        {CLAUSE_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g," ")}</option>)}
      </select>
      <button onClick={run} disabled={picked.length < 2}
        className="ml-2 px-4 py-2 rounded bg-blue-600 text-white disabled:opacity-40">Compare</button>

      {result && <>
        <div className="grid gap-3" style={{ gridTemplateColumns: `repeat(${result.cells.length}, 1fr)` }}>
          {result.cells.map((c: any) => (
            <div key={c.contract_id} className="border rounded-xl p-3 space-y-1">
              <div className="font-semibold">{c.contract_name}</div>
              <div className="text-xs text-gray-500">{c.classification ?? "—"}{c.risk_score != null && ` · risk ${c.risk_score}`}</div>
              <p className="text-sm">{c.text || "(not present)"}</p>
            </div>))}
        </div>
        <div><h2 className="font-semibold">Key differences</h2>
          <ul className="list-disc ml-5">{result.differences.map((d: string, i: number) => <li key={i}>{d}</li>)}</ul>
        </div>
      </>}
    </div>
  );
}
```

- [ ] **Step 6: Wire routes in `App.tsx`**

```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Library } from "./pages/Library";
import { Analysis } from "./pages/Analysis";
import { Summary } from "./pages/Summary";
import { BatchCompare } from "./pages/BatchCompare";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Library />} />
        <Route path="/contracts/:id" element={<Analysis />} />
        <Route path="/contracts/:id/summary" element={<Summary />} />
        <Route path="/compare" element={<BatchCompare />} />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 7: Verify build**

Run: `cd frontend && npm run build`
Expected: build succeeds, no type errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/src
git commit -m "feat: Library, Analysis, Summary, BatchCompare pages + routing"
```

---

## Phase 11 — Eval Harness (proves the 5 success metrics)

### Task 11.1: Eval script

**Files:**
- Create: `backend/eval/run_eval.py`

- [ ] **Step 1: Write `backend/eval/run_eval.py`** (runs real Gemini against fixtures; asserts each metric)

```python
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
    ok = len(caught) >= max(1, int(0.8 * len(expected)))  # >=80% of planted clauses
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
```

- [ ] **Step 2: Run the eval (requires a real `GEMINI_API_KEY`)**

Run: `cd backend && ../legalvenv/bin/python eval/run_eval.py`
Expected: prints PASS for all 4 metric groups (5 metrics; 2&4 share a fixture). If any FAIL, tune the relevant prompt in `app/llm/prompts.py` and re-run — do NOT relax the eval thresholds to force a pass.

- [ ] **Step 3: Commit**

```bash
git add backend/eval/run_eval.py
git commit -m "feat: eval harness scoring the 5 success metrics"
```

### Task 11.2: README with run instructions

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`** covering: prerequisites, `pip install -r backend/requirements.txt`, set `GEMINI_API_KEY` in `backend/.env`, generate fixtures, run backend (`uvicorn app.main:app --reload` from `backend/`), run frontend (`npm run dev` from `frontend/`), run tests (`pytest`), run eval. Document the parser-fallback behavior and how to edit the baseline.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with setup, run, and eval instructions"
```

---

## Final Verification

- [ ] **Run the full unit suite (mocked LLM, deterministic)**

Run: `cd backend && ../legalvenv/bin/pytest -v`
Expected: all tests PASS.

- [ ] **Run the eval against real Gemini**

Run: `cd backend && ../legalvenv/bin/python eval/run_eval.py`
Expected: 4/4 metric groups PASS (covers all 5 success metrics).

- [ ] **Manual smoke test**

Start backend + frontend, upload `all_clauses.docx`, confirm analysis renders with all 7 clause cards, view the summary, then batch-compare the 3 `batch/` contracts on governing law.
