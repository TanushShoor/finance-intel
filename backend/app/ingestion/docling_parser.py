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
