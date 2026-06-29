import os
import tempfile
from collections.abc import Generator
from pathlib import Path

_test_db_dir = Path(tempfile.mkdtemp(prefix="kb_pytest_"))
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_dir / 'test.db'}"
os.environ.setdefault("OPENAI_API_KEY", "test-key-for-pytest")
os.environ.setdefault("CHROMA_PERSIST_DIRECTORY", "")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.main import app
from backend.persistence.database import Base, SessionLocal, engine
from backend.persistence.models import AuditRun, Document, QARun, Snippet

get_settings.cache_clear()

Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def clean_database() -> Generator[None]:
    with SessionLocal() as session:
        session.execute(delete(Snippet))
        session.execute(delete(Document))
        session.execute(delete(QARun))
        session.execute(delete(AuditRun))
        session.commit()
    yield


@pytest.fixture
def db() -> Generator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client() -> Generator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_document(db: Session) -> Document:
    document = Document(title="Тестовый документ", text="Текст документа для pytest.")
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@pytest.fixture
def sample_qa_run(db: Session, sample_document: Document) -> QARun:
    run = QARun(
        question="Как мы работаем?",
        answer="Работаем по спринтам.",
        sources_json=(
            f'[{{"document_id": "{sample_document.id}", "quote": "спринты"}}]'
        ),
        needs_review=False,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@pytest.fixture
def sample_qa_run_review(db: Session) -> QARun:
    run = QARun(
        question="Сколько человек в команде?",
        answer="Данных недостаточно",
        sources_json="[]",
        needs_review=True,
        error="Источники отсутствуют",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@pytest.fixture
def sample_audit_run(db: Session) -> AuditRun:
    record = AuditRun(
        action="ask",
        input='{"question": "тест"}',
        output='{"answer": "ответ", "needs_review": false}',
        status="success",
        duration_ms=42,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
