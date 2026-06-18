from typing import Protocol
from pydantic import BaseModel, Field


class ParsedDocument(BaseModel):
    blocks: list[str] = Field(default_factory=list)
    page_count: int = 0
    had_text_layer: bool = True
    source: str = ""

    @property
    def full_text(self) -> str:
        return "\n".join(b for b in self.blocks if b)

    def is_degraded(self) -> bool:
        """True when extraction yielded essentially no usable text."""
        return not self.had_text_layer or len(self.full_text.strip()) < 10


class DocumentParser(Protocol):
    def parse(self, path: str) -> ParsedDocument: ...
