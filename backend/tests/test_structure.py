import app.ingestion.structure as structure_mod
from app.ingestion.structure import structure_document
from app.schemas.models import (
    ChunkBlocks,
    DocumentBlock,
    DocumentOutline,
    OutlineEntry,
)


def _patch_chunks(monkeypatch, chunks):
    monkeypatch.setattr(structure_mod, "chunk_text", lambda *a, **k: chunks)


def test_assembles_blocks_across_chunks_in_order(monkeypatch, mock_llm):
    _patch_chunks(monkeypatch, ["chunk-1", "chunk-2"])
    mock_llm.queue_response(ChunkBlocks(blocks=[
        DocumentBlock(type="header", number="1", text="Indemnity"),
        DocumentBlock(type="paragraph", text="Supplier shall indemnify."),
    ]))
    mock_llm.queue_response(ChunkBlocks(blocks=[
        DocumentBlock(type="header", number="2", text="Termination"),
        DocumentBlock(type="paragraph", text="Either party may terminate."),
    ]))
    mock_llm.queue_response(DocumentOutline(
        title="MSA",
        outline=[OutlineEntry(number="1", title="Indemnity", level=1),
                 OutlineEntry(number="2", title="Termination", level=1)]))

    doc = structure_document("ignored raw text", llm=mock_llm)

    assert doc.title == "MSA"
    assert [b.text for b in doc.blocks] == [
        "Indemnity", "Supplier shall indemnify.",
        "Termination", "Either party may terminate."]
    assert [o.title for o in doc.outline] == ["Indemnity", "Termination"]


def test_reports_progress_per_chunk(monkeypatch, mock_llm):
    _patch_chunks(monkeypatch, ["first chunk text", "second chunk text"])
    mock_llm.queue_response(ChunkBlocks(blocks=[]))
    mock_llm.queue_response(ChunkBlocks(blocks=[]))
    mock_llm.queue_response(DocumentOutline(title="X", outline=[]))

    seen = []
    structure_document("ignored", llm=mock_llm,
                       on_progress=lambda **kw: seen.append(kw))

    assert [s["current"] for s in seen] == [1, 2]
    assert all(s["total"] == 2 for s in seen)
    assert seen[0]["preview"].startswith("first chunk")


def test_dedups_blocks_repeated_by_chunk_overlap(monkeypatch, mock_llm):
    _patch_chunks(monkeypatch, ["chunk-1", "chunk-2"])
    shared = DocumentBlock(type="paragraph", text="Boundary clause text.")
    mock_llm.queue_response(ChunkBlocks(blocks=[
        DocumentBlock(type="header", number="1", text="Scope"), shared]))
    mock_llm.queue_response(ChunkBlocks(blocks=[
        shared, DocumentBlock(type="paragraph", text="Next clause.")]))
    mock_llm.queue_response(DocumentOutline(title="X", outline=[]))

    doc = structure_document("ignored", llm=mock_llm)

    texts = [b.text for b in doc.blocks]
    assert texts == ["Scope", "Boundary clause text.", "Next clause."]


def test_failed_chunk_is_skipped(monkeypatch):
    _patch_chunks(monkeypatch, ["chunk-1", "chunk-2"])

    class FlakyLLM:
        def __init__(self):
            self.n = 0

        def generate_structured(self, schema, prompt, **kw):
            self.n += 1
            if self.n == 1:
                raise RuntimeError("chunk 1 blew up")
            if self.n == 2:
                return ChunkBlocks(blocks=[DocumentBlock(type="header", text="Survived")])
            return DocumentOutline(title="T", outline=[])

    doc = structure_document("ignored", llm=FlakyLLM())
    assert [b.text for b in doc.blocks] == ["Survived"]


def test_synthesis_failure_falls_back_to_headings(monkeypatch):
    _patch_chunks(monkeypatch, ["only-chunk"])

    class SynthFailsLLM:
        def __init__(self):
            self.n = 0

        def generate_structured(self, schema, prompt, **kw):
            self.n += 1
            if self.n == 1:
                return ChunkBlocks(blocks=[
                    DocumentBlock(type="header", number="1", text="Indemnity"),
                    DocumentBlock(type="paragraph", text="body"),
                    DocumentBlock(type="subheader", number="1.1", text="Carve-outs")])
            raise RuntimeError("synthesis failed")

    doc = structure_document("ignored", llm=SynthFailsLLM())
    # Outline derived from headings/subheaders only, in order, with levels.
    assert [(o.title, o.level) for o in doc.outline] == [
        ("Indemnity", 1), ("Carve-outs", 2)]
    # Body blocks still present.
    assert len(doc.blocks) == 3
