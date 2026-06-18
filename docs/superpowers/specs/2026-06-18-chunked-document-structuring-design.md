# Chunked map-reduce document structuring

**Date:** 2026-06-18
**Status:** Approved for implementation

## Problem

Uploading a 96-page contract (`Nvidia.pdf`, 366,436 chars) fails. After fixing the
Gemini response-schema `default` bug, the `structure_document` step still fails:

```
Gemini call failed after 3 retries: Invalid JSON: EOF while parsing a value
```

Root cause: `structure_document` sends the entire document text in one prompt and
asks Gemini to emit a structured rendering of the whole thing. The **response**
exceeds the model's output-token budget and truncates mid-JSON. (Input ~90k tokens
is within Flash's 1M context — the *output* is the limit.) The step's output was
also unused downstream and unrendered.

## Goal

Replace the single-shot structuring with a chunked map-reduce pipeline that scales
to large documents, and render the result as a navigable document outline on a new
frontend page.

## Key design constraint

Synthesis **must not re-emit the full document body** or it hits the same output
truncation. Split responsibilities:

- **Map** produces the full body; assembled deterministically in code.
- **Synthesis** produces only `title` + a cleaned, de-duplicated **outline** (TOC) —
  bounded output. It operates on the extracted *headings* (compact), not full prose.

## Architecture (backend)

```
raw_text ──chunk_text()──► [chunk₁ … chunkₙ]   (~30k chars each, 1k overlap)
   each chunk ──MAP LLM call──► DocumentBlock[]  (header/subheader/paragraph)
   accumulate + de-dup overlap (in code) ──────► full body: DocumentBlock[]
   headings only ──SYNTHESIS LLM call──────────► title + OutlineEntry[]  (bounded)
   ════════════════════════════════════════════► StructuredDocument
```

For the Nvidia doc: ~13 map calls + 1 synthesis. A 2-page doc: 1 map + 1 synthesis.
Each call's input is bounded by chunk size, which also resolves per-call input size.

## Data model (`app/schemas/models.py`)

Replace the recursive `ClauseNode`-based `StructuredDocument` with flat, block-based
models (Gemini-clean via the existing sanitizer):

```python
class DocumentBlock(BaseModel):       # the body
    type: Literal["header", "subheader", "paragraph"]
    number: Optional[str] = None      # "8.1" if the source has it
    text: str = ""

class OutlineEntry(BaseModel):        # the synthesized TOC
    number: Optional[str] = None
    title: str
    level: int                        # 1 = header, 2 = subheader

class StructuredDocument(BaseModel):
    title: Optional[str] = None
    outline: list[OutlineEntry] = []  # from synthesis
    blocks: list[DocumentBlock] = []  # assembled from map
```

`ClauseNode` is removed (only `StructuredDocument` referenced it).

## New modules / changes

- `app/ingestion/chunking.py` *(new)* — `chunk_text(text, max_chars=30000, overlap=1000)`,
  splitting on paragraph/line boundaries; returns `[text]` unchanged when short.
- `app/ingestion/structure.py` — rewritten: map each chunk → blocks, assemble + de-dup
  overlap, synthesis → outline. **Best-effort**: a failed chunk is skipped; failed
  synthesis falls back to deriving the outline from headings in code. Structuring never
  hard-fails the analysis.
- `app/llm/prompts.py` — replace `STRUCTURE_PROMPT` with `BLOCK_MAP_PROMPT` and
  `OUTLINE_SYNTH_PROMPT`.

## Frontend

- New `pages/Document.tsx` at `/contracts/:id/document`; "Document →" link on the
  Analysis header.
- Layout: large display title, sticky outline sidebar (mono section numbers + clickable
  anchors), body in a ~68ch reading column. `header` (Plex Sans Condensed, large,
  anchored), `subheader` (medium), `paragraph` (Plex Sans, generous leading). Reuses the
  "Tolerance" token system.
- `types.ts` — add the new structure types; add `structure` to `Analysis`.

## Error handling

- A map chunk that raises is logged and skipped; remaining chunks proceed.
- Synthesis failure → outline derived from headings in code.
- `structure` therefore degrades gracefully and cannot fail the overall pipeline.

## Testing (TDD)

- `chunk_text`: long text → bounded overlapping chunks; short text → single chunk;
  boundary handling.
- `structure_document` with `MockLLM`: assembles blocks across chunks in order, de-dups
  overlap, resilient when a chunk map raises, synthesis-fallback path.
- Update `test_structure.py` to the new block shape.

## Out of scope (YAGNI)

- Parallelizing map calls (sequential is fine inside the background task).
- Chunking the extraction/comparison stages — extraction output is tiny (7 clauses), so
  it tolerates the large input. Revisit only if large docs prove too slow there.
