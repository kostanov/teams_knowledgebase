from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.application.audit_runs import AuditRunsService
from backend.persistence.database import get_db
from backend.schemas.audit_runs import AuditRunDetail, AuditRunListItem

router = APIRouter(prefix="/kb", tags=["audit"])
audit_runs_service = AuditRunsService()


@router.get("/audit-runs", response_model=list[AuditRunListItem])
def list_audit_runs(
    action: str | None = Query(default=None, max_length=64),
    status: str | None = Query(default=None, max_length=16),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[AuditRunListItem]:
    return audit_runs_service.list_runs(
        db,
        action=action,
        status=status,
        limit=limit,
    )


@router.get("/audit-runs/{run_id}", response_model=AuditRunDetail)
def get_audit_run(
    run_id: str,
    db: Session = Depends(get_db),
) -> AuditRunDetail:
    detail = audit_runs_service.get_run(db, run_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Audit run not found")
    return detail
