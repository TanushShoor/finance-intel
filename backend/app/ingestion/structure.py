"""Map-reduce document structuring.

A large contract can't be structured in one LLM call — the JSON response would
exceed the output-token budget and truncate. Instead we chunk the document, parse
each chunk into ordered blocks (the map step), assemble + de-dup the blocks in code
(the body), then make ONE bounded synthesis call over just the headings to produce a
clean title + outline. Both per-chunk failures and synthesis failure degrade
gracefully so structuring never fails the overall analysis.
"""
import logging

from app.ingestion.chunking import chunk_text
from app.schemas.models import (
    ChunkBlocks,
    DocumentBlock,
    DocumentOutline,
    OutlineEntry,
    StructuredDocument,
)
from app.llm.prompts import BLOCK_MAP_PROMPT, OUTLINE_SYNTH_PROMPT

logger = logging.getLogger(__name__)

_HEADING_TYPES = ("header", "subheader")


def _key(b: DocumentBlock):
    return (b.type, b.number, b.text.strip())


def _merge(acc: list[DocumentBlock], new: list[DocumentBlock]) -> None:
    """Append `new`, skipping the leading run that duplicates the tail of `acc`
    (the overlap window shared between consecutive chunks)."""
    span = min(len(acc), len(new))
    skip = 0
    for k in range(span, 0, -1):
        if [_key(b) for b in acc[-k:]] == [_key(b) for b in new[:k]]:
            skip = k
            break
    acc.extend(new[skip:])


def _fallback_outline(blocks: list[DocumentBlock]) -> list[OutlineEntry]:
    return [
        OutlineEntry(number=b.number, title=b.text,
                     level=1 if b.type == "header" else 2)
        for b in blocks
        if b.type in _HEADING_TYPES
    ]


def structure_document(raw_text: str, llm, on_progress=None) -> StructuredDocument:
    blocks: list[DocumentBlock] = []
    chunks = chunk_text(raw_text)
    total = len(chunks)
    for i, chunk in enumerate(chunks):
        if on_progress:
            on_progress(stage="structuring", current=i + 1, total=total,
                        preview=chunk[:140].strip())
        prompt = BLOCK_MAP_PROMPT.format(text=chunk)
        try:
            result: ChunkBlocks = llm.generate_structured(ChunkBlocks, prompt)
        except Exception as e:  # noqa: BLE001 - one bad chunk shouldn't sink the doc
            logger.warning("structure: chunk %d failed: %s", i, e)
            continue
        _merge(blocks, result.blocks)

    headings = [b for b in blocks if b.type in _HEADING_TYPES]
    heading_lines = "\n".join(
        f"{b.number or '-'} {b.text}".strip() for b in headings
    )
    try:
        synth: DocumentOutline = llm.generate_structured(
            DocumentOutline, OUTLINE_SYNTH_PROMPT.format(headings=heading_lines))
        title, outline = synth.title, synth.outline
    except Exception as e:  # noqa: BLE001 - fall back to headings as the outline
        logger.warning("structure: synthesis failed: %s", e)
        title, outline = None, _fallback_outline(blocks)

    return StructuredDocument(title=title, outline=outline, blocks=blocks)
