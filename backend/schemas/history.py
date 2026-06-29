from datetime import datetime

from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    document_id: str = ""
    quote: str


class QARunListItem(BaseModel):
    id: str
    question: str
    needs_review: bool
    created_at: datetime


class QARunDetail(QARunListItem):
    answer: str
    sources: list[SourceItem]
    error: str | None = None


class QARunListParams(BaseModel):
    needs_review: bool | None = None
    search: str | None = Field(default=None, max_length=500)
    limit: int = Field(default=100, ge=1, le=500)
