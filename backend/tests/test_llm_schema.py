"""Tests for the Gemini response-schema sanitizer.

Gemini's response_schema rejects JSON-Schema produced by Pydantic when it
contains `default` keys, `$ref`/`$defs` indirection, or `anyOf` null unions.
`to_gemini_schema` must produce an equivalent schema Gemini accepts.
"""
from typing import Optional
from pydantic import BaseModel, Field

from app.llm.schema import to_gemini_schema
from app.schemas.models import StructuredDocument
from app.schemas.financial import ToneAnalysis


def _walk(node):
    """Yield every dict node in a nested schema."""
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


class _Defaulted(BaseModel):
    text: str = ""
    confidence: float = 0.0
    location: Optional[str] = None
    note: Optional[str] = Field(None, description="optional note")


def test_strips_default_keys():
    schema = to_gemini_schema(_Defaulted)
    assert all("default" not in node for node in _walk(schema)), schema


def test_optional_becomes_nullable_without_anyof_null():
    schema = to_gemini_schema(_Defaulted)
    # No leftover `anyOf` carrying a {"type": "null"} member.
    for node in _walk(schema):
        if "anyOf" in node:
            assert not any(m.get("type") == "null" for m in node["anyOf"]), schema
    loc = schema["properties"]["location"]
    assert loc.get("nullable") is True, loc


def test_inlines_refs_for_nested_models():
    # ToneAnalysis wraps a list of TonePassage (a nested model).
    schema = to_gemini_schema(ToneAnalysis)
    assert all("$ref" not in node for node in _walk(schema)), schema
    assert "$defs" not in schema


def test_preserves_enum_values():
    # ToneAnalysis uses Literal enums (sentiment, hedging).
    schema = to_gemini_schema(ToneAnalysis)
    enums = [node["enum"] for node in _walk(schema) if "enum" in node]
    assert enums, "expected the sentiment/hedging enums to survive inlining"


def test_structured_document_is_gemini_clean():
    # The first pipeline call. Must have no defaults and no recursion/refs.
    schema = to_gemini_schema(StructuredDocument)
    nodes = list(_walk(schema))
    assert all("default" not in n for n in nodes), schema
    assert all("$ref" not in n for n in nodes), schema
