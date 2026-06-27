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
