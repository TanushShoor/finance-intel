"""Split a long document into bounded, slightly overlapping chunks.

Each chunk stays under ``max_chars`` so a single LLM call's input is bounded.
Splitting prefers paragraph boundaries (blank lines), then line boundaries, so
clauses are not cut mid-sentence where avoidable. A small ``overlap`` window is
repeated at the start of the next chunk so a clause spanning a boundary is seen
whole by at least one chunk.
"""


def _segments(text: str) -> list[str]:
    """Break text into paragraph-ish units, keeping them under control."""
    parts = text.split("\n\n")
    return [p for p in parts if p != ""]


def chunk_text(text: str, max_chars: int = 30000, overlap: int = 1000) -> list[str]:
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current = ""

    def flush():
        nonlocal current
        if current:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = tail

    for seg in _segments(text):
        # A single oversized segment must be hard-split on its own.
        if len(seg) > max_chars:
            if current:
                chunks.append(current)
                current = ""
            for i in range(0, len(seg), max_chars):
                chunks.append(seg[i : i + max_chars])
            # A hard-split piece's content is already fully captured; don't seed
            # an overlap tail (it would dangle as a duplicate trailing chunk).
            current = ""
            continue

        candidate = f"{current}\n\n{seg}" if current else seg
        if len(candidate) > max_chars:
            flush()
            candidate = f"{current}\n\n{seg}" if current else seg
        current = candidate

    if current:
        chunks.append(current)

    return chunks
