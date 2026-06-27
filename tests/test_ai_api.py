from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models import AuditRun
from backend.schemas.ai import AIAnswerResponse, AISourceQuote


def test_answer_with_sources_success(client, db: Session) -> None:
    llm_response = AIAnswerResponse(
        answer="Мы работаем по спринтам.",
        sources=[AISourceQuote(quote="Мы работаем по спринтам.")],
        confidence="high",
        needs_review=False,
    )
    with patch(
        "backend.api.routes.ai.qa_service._llm_service.answer_with_retry",
        return_value=(llm_response, None),
    ):
        response = client.post(
            "/ai/answer_with_sources",
            json={
                "question": "Как мы работаем?",
                "context": "Мы работаем по спринтам.",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Мы работаем по спринтам."
    assert payload["confidence"] == "high"
    assert payload["needs_review"] is False
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["quote"] == "Мы работаем по спринтам."

    audits = list(db.scalars(select(AuditRun)).all())
    assert len(audits) == 1
    assert audits[0].action == "ai_answer_with_sources"
    assert audits[0].status == "success"


def test_answer_with_sources_low_confidence_forces_review(client) -> None:
    llm_response = AIAnswerResponse(
        answer="Не уверен.",
        sources=[AISourceQuote(quote="фрагмент")],
        confidence="low",
        needs_review=False,
    )
    with patch(
        "backend.api.routes.ai.qa_service._llm_service.answer_with_retry",
        return_value=(llm_response, None),
    ):
        response = client.post(
            "/ai/answer_with_sources",
            json={"question": "Вопрос?", "context": "фрагмент"},
        )

    assert response.status_code == 200
    assert response.json()["needs_review"] is True


def test_answer_with_sources_invalid_json_from_llm(client, db: Session) -> None:
    with patch(
        "backend.api.routes.ai.qa_service._llm_service.answer_with_retry",
        return_value=(None, "Ошибка валидации JSON от LLM"),
    ):
        response = client.post(
            "/ai/answer_with_sources",
            json={"question": "Вопрос?", "context": "Контекст."},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["needs_review"] is True
    assert payload["sources"] == []

    audits = list(db.scalars(select(AuditRun)).all())
    assert audits[0].status == "error"


def test_answer_with_sources_llm_unavailable(client) -> None:
    with patch(
        "backend.api.routes.ai.qa_service._llm_service.answer_with_retry",
        side_effect=RuntimeError("OpenAI unavailable"),
    ):
        response = client.post(
            "/ai/answer_with_sources",
            json={"question": "Вопрос?", "context": "Контекст."},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["needs_review"] is True
    assert "недоступен" in payload["answer"].lower()


def test_answer_with_sources_validation_error(client) -> None:
    response = client.post(
        "/ai/answer_with_sources",
        json={"question": "", "context": "Контекст."},
    )

    assert response.status_code == 422
