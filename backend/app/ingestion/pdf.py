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
