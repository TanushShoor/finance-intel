from pydantic import BaseModel
from app.llm.client import GeminiClient


class _Out(BaseModel):
    value: int


class _FakeModels:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = 0

    def generate_content(self, **kwargs):
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        class R: parsed = outcome
        return R()


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
