from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    text: str = Field(..., min_length=1, max_length=100_000)


class DocumentCreateResponse(BaseModel):
    status: str = "ok"
    document_id: str


class DocumentListItem(BaseModel):
    id: str
    title: str
    created_at: datetime


class DocumentDetail(DocumentListItem):
    text: str
