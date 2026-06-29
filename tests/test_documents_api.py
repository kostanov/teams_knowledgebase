from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models import AuditRun, Document


def test_list_documents_empty(client) -> None:
    response = client.get("/kb/documents")

    assert response.status_code == 200
    assert response.json() == []


def test_list_documents_returns_items(client, sample_document: Document) -> None:
    response = client.get("/kb/documents")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == sample_document.id
    assert payload[0]["title"] == sample_document.title
    assert "created_at" in payload[0]
    assert "text" not in payload[0]


def test_list_documents_writes_audit(
    client, db: Session, sample_document: Document
) -> None:
    response = client.get("/kb/documents")

    assert response.status_code == 200
    audits = list(db.scalars(select(AuditRun)).all())
    assert len(audits) == 1
    assert audits[0].action == "get_documents"
    assert audits[0].status == "success"
    assert '"count": 1' in audits[0].output


def test_get_document_by_id(client, sample_document: Document) -> None:
    response = client.get(f"/kb/documents/{sample_document.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == sample_document.id
    assert payload["title"] == sample_document.title
    assert payload["text"] == sample_document.text
    assert "created_at" in payload


def test_get_document_not_found(client) -> None:
    response = client.get("/kb/documents/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"
