from app.schemas.models import StructuredDocument
from app.llm.prompts import STRUCTURE_PROMPT


def structure_document(raw_text: str, llm) -> StructuredDocument:
    prompt = STRUCTURE_PROMPT.format(text=raw_text)
    return llm.generate_structured(StructuredDocument, prompt)
