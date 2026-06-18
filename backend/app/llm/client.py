import time
from google import genai
from google.genai import types
from app.config import settings


class GeminiClient:
    def __init__(self, api_key: str | None = None, model: str | None = None,
                 max_retries: int = 3):
        self._client = genai.Client(api_key=api_key or settings.gemini_api_key)
        self.model = model or settings.gemini_model
        self.max_retries = max_retries

    def generate_structured(self, schema, prompt: str, temperature: float = 0.1):
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=temperature,
        )
        last_err = None
        for attempt in range(self.max_retries):
            try:
                resp = self._client.models.generate_content(
                    model=self.model, contents=prompt, config=config)
                parsed = resp.parsed
                if parsed is None:
                    raise ValueError("Gemini returned no parsable structured output")
                return parsed
            except Exception as e:  # noqa: BLE001 - retry transient/parse errors
                last_err = e
                time.sleep(0.5 * (2 ** attempt))
        raise RuntimeError(f"Gemini call failed after {self.max_retries} retries: {last_err}")
