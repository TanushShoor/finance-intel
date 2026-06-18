from pydantic import BaseModel
from app.llm.client import GeminiClient


class _Out(BaseModel):
    value: int


class _Resp:
    def __init__(self, parsed=None, text=None):
        self.parsed = parsed
        self.text = text


class _FakeModels:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = 0
        self.kwargs = []

    def generate_content(self, **kwargs):
        self.kwargs.append(kwargs)
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        # A bare model is treated as the SDK's already-parsed result.
        return outcome if isinstance(outcome, _Resp) else _Resp(parsed=outcome)


class _FakeSDK:
    def __init__(self, outcomes):
        self.models = _FakeModels(outcomes)


def test_generate_structured_returns_parsed(monkeypatch):
    client = GeminiClient.__new__(GeminiClient)
    client._client = _FakeSDK([_Out(value=42)])
    client.model = "x"
    client.max_retries = 2
    out = client.generate_structured(_Out, "prompt")
    assert out.value == 42


def test_generate_structured_retries_then_succeeds():
    client = GeminiClient.__new__(GeminiClient)
    client._client = _FakeSDK([RuntimeError("transient"), _Out(value=7)])
    client.model = "x"
    client.max_retries = 2
    out = client.generate_structured(_Out, "prompt")
    assert out.value == 7


def test_passes_sanitized_schema_without_defaults():
    class _WithDefault(BaseModel):
        value: int = 0

    client = GeminiClient.__new__(GeminiClient)
    client._client = _FakeSDK([_WithDefault(value=1)])
    client.model = "x"
    client.max_retries = 1
    client.generate_structured(_WithDefault, "prompt")
    schema = client._client.models.kwargs[0]["config"].response_schema
    assert isinstance(schema, dict)
    assert "default" not in schema.get("properties", {}).get("value", {})


def test_coerces_dict_parsed_into_model():
    client = GeminiClient.__new__(GeminiClient)
    client._client = _FakeSDK([_Resp(parsed={"value": 5})])
    client.model = "x"
    client.max_retries = 1
    out = client.generate_structured(_Out, "prompt")
    assert isinstance(out, _Out) and out.value == 5


def test_falls_back_to_text_when_parsed_is_none():
    client = GeminiClient.__new__(GeminiClient)
    client._client = _FakeSDK([_Resp(parsed=None, text='{"value": 9}')])
    client.model = "x"
    client.max_retries = 1
    out = client.generate_structured(_Out, "prompt")
    assert isinstance(out, _Out) and out.value == 9
