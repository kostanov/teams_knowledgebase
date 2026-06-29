import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models import AuditRun
from backend.quality.audit import AuditService
from backend.schemas.audit_runs import AuditRunDetail, AuditRunListItem


class AuditRunsService:
    def __init__(self, *, audit_service: AuditService | None = None) -> None:
        self._audit_service = audit_service or AuditService()

    def list_runs(
        self,
        db: Session,
        *,
        action: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[AuditRunListItem]:
        started = time.perf_counter()
        query = select(AuditRun).order_by(AuditRun.created_at.desc()).limit(limit)
        if action:
            query = query.where(AuditRun.action == action)
        if status:
            query = query.where(AuditRun.status == status)
        runs = db.scalars(query).all()
        items = [
            AuditRunListItem(
                id=run.id,
                action=run.action,
                status=run.status,
                error=run.error,
                duration_ms=run.duration_ms,
                created_at=run.created_at,
            )
            for run in runs
        ]
        duration_ms = int((time.perf_counter() - started) * 1000)
        self._audit_service.log(
            db,
            action="get_audit_runs",
            input_data={"action": action, "status": status, "limit": limit},
            output_data={"count": len(items)},
            status="success",
            duration_ms=duration_ms,
        )
        db.commit()
        return items

    def get_run(self, db: Session, run_id: str) -> AuditRunDetail | None:
        started = time.perf_counter()
        run = db.get(AuditRun, run_id)
        if run is None:
            return None
        detail = AuditRunDetail(
            id=run.id,
            action=run.action,
            status=run.status,
            error=run.error,
            duration_ms=run.duration_ms,
            created_at=run.created_at,
            input=run.input,
            output=run.output,
        )
        duration_ms = int((time.perf_counter() - started) * 1000)
        self._audit_service.log(
            db,
            action="get_audit_run",
            input_data={"id": run_id},
            output_data={"id": run_id},
            status="success",
            duration_ms=duration_ms,
        )
        db.commit()
        return detail
