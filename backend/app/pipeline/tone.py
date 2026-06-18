"""Management tone analysis (success metric #2).

Bounded single call over the management commentary. Management commentary sits near
the top of releases/transcripts and in the MD&A of filings, so for v0 we analyse a
generous leading window rather than the entire (possibly 100-page) document.
"""
from app.schemas.financial import ToneAnalysis
from app.llm.prompts import TONE_PROMPT

_TONE_WINDOW = 60000  # ~15k tokens


def analyze_tone(text, llm):
    window = text[:_TONE_WINDOW]
    return llm.generate_structured(ToneAnalysis, TONE_PROMPT.format(text=window))
