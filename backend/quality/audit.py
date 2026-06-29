import json
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from backend.persistence.models import AuditRun, QARun


class AuditService:
    def log(
        self,
        db: Session,
        *,
        action: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        status: str,
        error: str | None = None,
        duration_ms: int = 0,
    ) -> AuditRun:
        record = AuditRun(
            action=action,
            input=json.dumps(input_data, ensure_ascii=False),
            output=json.dumps(output_data, ensure_ascii=False),
            status=status,
            error=error,
            duration_ms=duration_ms,
        )
        db.add(record)
        return record


class QualityService:
    INSUFFICIENT_DATA_ANSWER = "Данных недостаточно"
    LLM_UNAVAILABLE_ANSWER = "Сервис LLM временно недоступен, требуется ручная проверка"

    def enforce_ask_response(
        self,
        *,
        answer: str,
        sources: list[dict[str, str]],
        needs_review: bool,
        error: str | None,
        confidence: str | None = None,
    ) -> tuple[str, list[dict[str, str]], bool, str | None]:
        review = needs_review
        reason = error
        result_sources = sources
        result_answer = answer

        if confidence == "low":
            review = True
            reason = reason or "LLM запросила ручную проверку из-за низкой уверенности"

        if not result_sources:
            review = True
            reason = reason or "Источники отсутствуют"
            if not result_answer.strip():
                result_answer = self.INSUFFICIENT_DATA_ANSWER

        if review and not result_answer.strip():
            result_answer = self.INSUFFICIENT_DATA_ANSWER

        return result_answer, result_sources, review, reason

    def save_ask_result(
        self,
        db: Session,
        *,
        question: str,
        answer: str,
        sources: list[dict[str, str]],
        needs_review: bool,
        error: str | None,
        audit_service: AuditService,
        input_data: dict[str, Any],
        duration_ms: int,
        status: str = "success",
    ) -> dict[str, Any]:
        output = {
            "answer": answer,
            "sources": sources,
            "needs_review": needs_review,
        }
        qa_run = QARun(
            question=question,
            answer=answer,
            sources_json=json.dumps(sources, ensure_ascii=False),
            needs_review=needs_review,
            error=error,
        )
        db.add(qa_run)
        audit_service.log(
            db,
            action="ask",
            input_data=input_data,
            output_data=output,
            status=status,
            error=error,
            duration_ms=duration_ms,
        )
        db.commit()
        db.refresh(qa_run)
        return output


def measure_ms(func: Callable[[], Any]) -> tuple[Any, int]:
    started = time.perf_counter()
    result = func()
    duration_ms = int((time.perf_counter() - started) * 1000)
    return result, duration_ms
