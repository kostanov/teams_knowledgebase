"""Загрузка и очистка тестовых данных базы знаний."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from sqlalchemy import delete

from backend.persistence.database import SessionLocal, init_db
from backend.persistence.models import AuditRun, Document, QARun, Snippet
from backend.vector.chroma_store import VectorStore

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOCUMENTS_PATH = PROJECT_ROOT / "tests_data" / "kb_documents.jsonl"
DEFAULT_API_BASE_URL = "http://localhost:8000"


def clear_database() -> None:
    """Очищает таблицы documents, snippets, qa_runs и audit_runs."""
    init_db()
    db = SessionLocal()
    try:
        db.execute(delete(Snippet))
        db.execute(delete(Document))
        db.execute(delete(QARun))
        db.execute(delete(AuditRun))
        db.commit()
    finally:
        db.close()


def clear_chroma() -> None:
    """Очищает коллекцию Chroma и создаёт её заново."""
    VectorStore().reset_collection()


def clear_all_data() -> None:
    """Очищает SQL-базу (SQLite / PostgreSQL) и векторное хранилище Chroma."""
    clear_database()
    clear_chroma()


def read_documents(path: Path = DEFAULT_DOCUMENTS_PATH) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Файл не найден: {path}")

    documents: list[dict[str, str]] = []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as error:
                raise ValueError(f"Невалидный JSON в {path}:{line_number}") from error
            title = payload.get("title", "").strip()
            text = payload.get("text", "").strip()
            if not title or not text:
                raise ValueError(
                    f"Пустые title/text в {path}:{line_number}: {payload!r}"
                )
            documents.append({"title": title, "text": text})
    return documents


def post_document(
    *,
    base_url: str,
    title: str,
    text: str,
    timeout: float = 60.0,
) -> dict[str, Any]:
    payload = json.dumps({"title": title, "text": text}, ensure_ascii=False).encode()
    request = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/kb/documents",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode()
    except urllib.error.HTTPError as error:
        details = error.read().decode()
        raise RuntimeError(
            f"Ошибка API {error.code} при добавлении «{title}»: {details}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Не удалось подключиться к API {base_url}. Запущен ли backend?"
        ) from error

    return json.loads(body)


def load_documents_from_api(
    *,
    path: Path = DEFAULT_DOCUMENTS_PATH,
    base_url: str | None = None,
) -> list[dict[str, Any]]:
    """Загружает документы из JSONL через POST /kb/documents."""
    api_base_url = base_url or os.getenv("SEED_API_BASE_URL", DEFAULT_API_BASE_URL)
    results: list[dict[str, Any]] = []

    for document in read_documents(path):
        result = post_document(
            base_url=api_base_url,
            title=document["title"],
            text=document["text"],
        )
        results.append(
            {
                "title": document["title"],
                "document_id": result["document_id"],
                "status": result.get("status", "ok"),
            }
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Очистка и загрузка тестовых данных базы знаний",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="очистить БД и Chroma перед загрузкой",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="только очистить БД и Chroma",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_DOCUMENTS_PATH,
        help="путь к kb_documents.jsonl",
    )
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("SEED_API_BASE_URL", DEFAULT_API_BASE_URL),
        help="базовый URL backend API",
    )
    args = parser.parse_args(argv)

    if args.clear:
        clear_all_data()
        print("База данных и Chroma очищены.")
        return 0

    if args.force:
        clear_all_data()
        print("База данных и Chroma очищены.")

    loaded = load_documents_from_api(path=args.file, base_url=args.api_base_url)
    for item in loaded:
        print(f"✓ {item['title']} → {item['document_id']}")
    print(f"Загружено документов: {len(loaded)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
