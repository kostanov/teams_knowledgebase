import csv
import io
import json
import time
from collections.abc import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models import QARun
from backend.quality.audit import AuditService
from backend.schemas.history import QARunDetail, QARunListItem, SourceItem


class HistoryService:
    def __init__(self, *, audit_service: AuditService | None = None) -> None:
        self._audit_service = audit_service or AuditService()

    def list_runs(
        self,
        db: Session,
        *,
        needs_review: bool | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[QARunListItem]:
        started = time.perf_counter()
        query = select(QARun).order_by(QARun.created_at.desc()).limit(limit)
        if needs_review is not None:
            query = query.where(QARun.needs_review == needs_review)
        if search:
            query = query.where(QARun.question.ilike(f"%{search}%"))
        runs = db.scalars(query).all()
        items = [
            QARunListItem(
                id=run.id,
                question=run.question,
                needs_review=run.needs_review,
                created_at=run.created_at,
            )
            for run in runs
        ]
        duration_ms = int((time.perf_counter() - started) * 1000)
        self._audit_service.log(
            db,
            action="get_qa_history",
            input_data={
                "needs_review": needs_review,
                "search": search,
                "limit": limit,
            },
            output_data={"count": len(items)},
            status="success",
            duration_ms=duration_ms,
        )
        db.commit()
        return items

    def get_run(self, db: Session, run_id: str) -> QARunDetail | None:
        started = time.perf_counter()
        run = db.get(QARun, run_id)
        if run is None:
            return None
        detail = self._to_detail(run)
        duration_ms = int((time.perf_counter() - started) * 1000)
        self._audit_service.log(
            db,
            action="get_qa_run",
            input_data={"id": run_id},
            output_data={"id": run_id},
            status="success",
            duration_ms=duration_ms,
        )
        db.commit()
        return detail

    def export_runs(
        self,
        db: Session,
        *,
        fmt: str,
        needs_review: bool | None = None,
        search: str | None = None,
        limit: int = 500,
    ) -> tuple[str, str, Iterator[str]]:
        started = time.perf_counter()
        query = select(QARun).order_by(QARun.created_at.desc()).limit(limit)
        if needs_review is not None:
            query = query.where(QARun.needs_review == needs_review)
        if search:
            query = query.where(QARun.question.ilike(f"%{search}%"))
        runs = db.scalars(query).all()

        if fmt == "csv":
            content_type = "text/csv; charset=utf-8"
            filename = "qa_history.csv"

            def generate() -> Iterator[str]:
                buffer = io.StringIO()
                writer = csv.writer(buffer)
                writer.writerow(
                    [
                        "id",
                        "created_at",
                        "question",
                        "answer",
                        "sources_json",
                        "needs_review",
                        "error",
                    ]
                )
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)
                for run in runs:
                    writer.writerow(
                        [
                            run.id,
                            run.created_at.isoformat(),
                            run.question,
                            run.answer,
                            run.sources_json,
                            run.needs_review,
                            run.error or "",
                        ]
                    )
                    yield buffer.getvalue()
                    buffer.seek(0)
                    buffer.truncate(0)

        else:
            content_type = "application/x-ndjson; charset=utf-8"
            filename = "qa_history.jsonl"

            def generate() -> Iterator[str]:
                for run in runs:
                    line = json.dumps(
                        {
                            "id": run.id,
                            "created_at": run.created_at.isoformat(),
                            "question": run.question,
                            "answer": run.answer,
                            "sources_json": run.sources_json,
                            "needs_review": run.needs_review,
                            "error": run.error,
                        },
                        ensure_ascii=False,
                    )
                    yield f"{line}\n"

        duration_ms = int((time.perf_counter() - started) * 1000)
        self._audit_service.log(
            db,
            action="export_qa_history",
            input_data={
                "format": fmt,
                "needs_review": needs_review,
                "search": search,
                "limit": limit,
            },
            output_data={"count": len(runs)},
            status="success",
            duration_ms=duration_ms,
        )
        db.commit()
        return content_type, filename, generate()

    @staticmethod
    def _to_detail(run: QARun) -> QARunDetail:
        try:
            raw_sources = json.loads(run.sources_json)
        except json.JSONDecodeError:
            raw_sources = []
        sources = [
            SourceItem(
                document_id=item.get("document_id", ""),
                quote=item.get("quote", ""),
            )
            for item in raw_sources
            if isinstance(item, dict)
        ]
        return QARunDetail(
            id=run.id,
            question=run.question,
            answer=run.answer,
            sources=sources,
            needs_review=run.needs_review,
            error=run.error,
            created_at=run.created_at,
        )
