from typing import Literal, Optional
from pydantic import BaseModel, Field


# --- Ingestion / structure ---
BlockType = Literal["header", "subheader", "paragraph"]


class DocumentBlock(BaseModel):
    """One unit of the document body, in reading order."""
    type: BlockType
    number: Optional[str] = Field(None, description="e.g. '8.1' if the source has it")
    text: str = ""


class OutlineEntry(BaseModel):
    """One entry in the synthesized table of contents."""
    number: Optional[str] = None
    title: str
    level: int = Field(1, ge=1, le=2, description="1 = header, 2 = subheader")


class ChunkBlocks(BaseModel):
    """Map-step output: the blocks parsed from a single chunk."""
    blocks: list[DocumentBlock] = Field(default_factory=list)


class DocumentOutline(BaseModel):
    """Synthesis-step output: the cleaned title + table of contents."""
    title: Optional[str] = None
    outline: list[OutlineEntry] = Field(default_factory=list)


class StructuredDocument(BaseModel):
    title: Optional[str] = None
    outline: list[OutlineEntry] = Field(default_factory=list)
    blocks: list[DocumentBlock] = Field(default_factory=list)
