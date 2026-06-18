from typing import Optional
from sqlmodel import SQLModel, Field, Column, JSON


class Contract(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    file_path: str
    format: str
    status: str = "uploaded"          # uploaded|processing|done|failed
    error: Optional[str] = None
    analysis: Optional[dict] = Field(default=None, sa_column=Column(JSON))
