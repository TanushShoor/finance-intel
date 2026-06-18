from app.ingestion.chunking import chunk_text


def test_short_text_is_single_chunk():
    text = "A short contract.\n\nWith two paragraphs."
    assert chunk_text(text, max_chars=1000) == [text]


def test_long_text_splits_into_bounded_chunks():
    para = ("This is a clause paragraph that carries some weight. " * 10).strip()
    text = "\n\n".join(para for _ in range(40))  # well over 4k chars
    chunks = chunk_text(text, max_chars=4000, overlap=200)
    assert len(chunks) > 1
    assert all(len(c) <= 4000 for c in chunks), [len(c) for c in chunks]


def test_chunks_cover_all_content():
    paras = [f"Paragraph number {i} with distinctive token Z{i}Z." for i in range(60)]
    text = "\n\n".join(paras)
    chunks = chunk_text(text, max_chars=800, overlap=100)
    joined = "\n\n".join(chunks)
    # Every paragraph's unique marker appears somewhere across the chunks.
    for i in range(60):
        assert f"Z{i}Z" in joined


def test_oversized_single_segment_is_hard_split_without_tiny_duplicate():
    # One paragraph larger than max_chars, with no blank lines to split on.
    text = "x" * 2500
    chunks = chunk_text(text, max_chars=1000, overlap=100)
    assert all(len(c) <= 1000 for c in chunks)
    # No leftover chunk that is merely the overlap tail of the previous one.
    assert not any(len(c) <= 100 for c in chunks), [len(c) for c in chunks]


def test_overlap_repeats_boundary_content():
    paras = [f"Para {i} aaaaaaaaaaaaaaaaaaaa" for i in range(30)]
    text = "\n\n".join(paras)
    chunks = chunk_text(text, max_chars=400, overlap=120)
    # Consecutive chunks share some trailing/leading text (overlap window).
    assert len(chunks) >= 2
    overlaps = [
        bool(set(a[-120:].split()) & set(b[:120].split()))
        for a, b in zip(chunks, chunks[1:])
    ]
    assert any(overlaps)
