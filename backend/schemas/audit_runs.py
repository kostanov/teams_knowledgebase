from datetime import datetime

from pydantic import BaseModel, Field


class AuditRunListItem(BaseModel):
    id: str
    action: str
    status: str
    error: str | None
    duration_ms: int
    created_at: datetime


class AuditRunDetail(AuditRunListItem):
    input: str
    output: str


class AuditRunListParams(BaseModel):
    action: str | None = Field(default=None, max_length=64)
    status: str | None = Field(default=None, max_length=16)
    limit: int = Field(default=100, ge=1, le=500)
