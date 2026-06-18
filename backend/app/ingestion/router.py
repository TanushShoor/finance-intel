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
