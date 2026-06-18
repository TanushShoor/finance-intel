from app.ingestion.base import ParsedDocument


def test_parsed_document_full_text_joins_blocks():
    doc = ParsedDocument(blocks=["Para one.", "Para two."], page_count=1,
                         had_text_layer=True, source="x.pdf")
    assert doc.full_text == "Para one.\nPara two."
    assert doc.is_degraded() is False


def test_parsed_document_degraded_when_almost_no_text():
    doc = ParsedDocument(blocks=[""], page_count=3, had_text_layer=False, source="x.pdf")
    assert doc.is_degraded() is True


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
