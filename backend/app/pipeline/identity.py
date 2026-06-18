"""Lightweight document identification: company, period, doc type."""
from app.schemas.financial import DocumentIdentity
from app.llm.prompts import IDENTITY_PROMPT


def identify_document(text, llm) -> DocumentIdentity:
    return llm.generate_structured(DocumentIdentity, IDENTITY_PROMPT.format(text=text[:6000]))
