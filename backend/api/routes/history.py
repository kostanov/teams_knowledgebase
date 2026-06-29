from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.application.history import HistoryService
from backend.persistence.database import get_db
from backend.schemas.history import QARunDetail, QARunListItem

router = APIRouter(prefix="/kb", tags=["history"])
history_service = HistoryService()


@router.get("/qa-runs", response_model=list[QARunListItem])
def list_qa_runs(
    needs_review: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=500),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[QARunListItem]:
    return history_service.list_runs(
        db,
        needs_review=needs_review,
        search=search,
        limit=limit,
    )


@router.get("/qa-runs/export")
def export_qa_runs(
    fmt: str = Query(default="jsonl", pattern="^(jsonl|csv)$"),
    needs_review: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=500),
    limit: int = Query(default=500, ge=1, le=500),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    content_type, filename, stream = history_service.export_runs(
        db,
        fmt=fmt,
        needs_review=needs_review,
        search=search,
        limit=limit,
    )
    return StreamingResponse(
        stream,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/qa-runs/{run_id}", response_model=QARunDetail)
def get_qa_run(
    run_id: str,
    db: Session = Depends(get_db),
) -> QARunDetail:
    detail = history_service.get_run(db, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="QA run not found")
    return detail
