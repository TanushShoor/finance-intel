"""Convert a Pydantic model into a Gemini-compatible response schema.

Pydantic's ``model_json_schema()`` emits constructs the Gemini API rejects:

* ``default`` keys  -> "Default value is not supported in the response schema"
* ``$ref`` / ``$defs`` indirection for nested models and enums
* ``anyOf`` unions of the form ``[T, {"type": "null"}]`` for ``Optional[T]``

``to_gemini_schema`` walks the generated schema and produces an equivalent one
Gemini accepts: refs inlined, defaults/titles dropped, optionals expressed via
``nullable``.
"""

# Keys that are noise (or outright rejected) in a Gemini response schema.
_DROP_KEYS = {
    "default",
    "title",
    "additionalProperties",
    "$defs",
    "$schema",
    "discriminator",
    "examples",
    "const",
}

# Guard against pathological / self-referential schemas. Once a model has been
# inlined this many times along a single branch we stop expanding it.
_MAX_DEPTH = 12


def _resolve(node, defs, depth):
    if isinstance(node, list):
        return [_resolve(v, defs, depth) for v in node]
    if not isinstance(node, dict):
        return node

    if "$ref" in node:
        ref_name = node["$ref"].split("/")[-1]
        if depth >= _MAX_DEPTH:
            return {"type": "object"}
        return _resolve(dict(defs.get(ref_name, {})), defs, depth + 1)

    out: dict = {}
    for key, value in node.items():
        if key in _DROP_KEYS:
            continue
        if key == "anyOf":
            # Optional[T] -> anyOf [T, null]. Collapse to T + nullable flag.
            members = value
            non_null = [m for m in members if m.get("type") != "null"]
            has_null = any(m.get("type") == "null" for m in members)
            if len(non_null) == 1:
                resolved = _resolve(non_null[0], defs, depth)
                if has_null:
                    resolved["nullable"] = True
                out.update(resolved)
            else:
                out["anyOf"] = [_resolve(m, defs, depth) for m in non_null]
                if has_null:
                    out["nullable"] = True
            continue
        if key == "allOf":
            # Pydantic uses allOf to attach a description to a single $ref.
            merged: dict = {}
            for sub in value:
                merged.update(_resolve(sub, defs, depth))
            out.update(merged)
            continue
        out[key] = _resolve(value, defs, depth)
    return out


def to_gemini_schema(model) -> dict:
    """Return a Gemini-safe JSON schema dict for a Pydantic model."""
    raw = model.model_json_schema()
    defs = raw.get("$defs", {})
    return _resolve(raw, defs, 0)
