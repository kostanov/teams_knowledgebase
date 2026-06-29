import csv
import io
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models import AuditRun, QARun


def test_list_qa_runs_empty(client) -> None:
    response = client.get("/kb/qa-runs")

    assert response.status_code == 200
    assert response.json() == []


def test_list_qa_runs_returns_items(
    client,
    sample_qa_run: QARun,
    sample_qa_run_review: QARun,
) -> None:
    response = client.get("/kb/qa-runs")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    ids = {item["id"] for item in payload}
    assert sample_qa_run.id in ids
    assert sample_qa_run_review.id in ids
    assert all("question" in item and "needs_review" in item for item in payload)


def test_list_qa_runs_filter_needs_review(
    client,
    sample_qa_run: QARun,
    sample_qa_run_review: QARun,
) -> None:
    response = client.get("/kb/qa-runs", params={"needs_review": True})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == sample_qa_run_review.id
    assert payload[0]["needs_review"] is True


def test_list_qa_runs_search(
    client,
    sample_qa_run: QARun,
    sample_qa_run_review: QARun,
) -> None:
    response = client.get("/kb/qa-runs", params={"search": "работаем"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == sample_qa_run.id


def test_list_qa_runs_writes_audit(
    client,
    db: Session,
    sample_qa_run: QARun,
) -> None:
    response = client.get("/kb/qa-runs")

    assert response.status_code == 200
    audits = list(db.scalars(select(AuditRun)).all())
    assert len(audits) == 1
    assert audits[0].action == "get_qa_history"
    assert audits[0].status == "success"
    assert '"count": 1' in audits[0].output


def test_get_qa_run_by_id(client, sample_qa_run: QARun) -> None:
    response = client.get(f"/kb/qa-runs/{sample_qa_run.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == sample_qa_run.id
    assert payload["question"] == sample_qa_run.question
    assert payload["answer"] == sample_qa_run.answer
    assert payload["needs_review"] is False
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["quote"] == "спринты"
    assert payload["error"] is None


def test_get_qa_run_not_found(client) -> None:
    response = client.get("/kb/qa-runs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["detail"] == "QA run not found"


def test_export_qa_runs_jsonl(
    client,
    sample_qa_run: QARun,
    sample_qa_run_review: QARun,
) -> None:
    response = client.get("/kb/qa-runs/export", params={"fmt": "jsonl"})

    assert response.status_code == 200
    assert "application/x-ndjson" in response.headers["content-type"]
    assert 'filename="qa_history.jsonl"' in response.headers["content-disposition"]

    lines = [line for line in response.text.strip().split("\n") if line]
    assert len(lines) == 2
    records = [json.loads(line) for line in lines]
    ids = {record["id"] for record in records}
    assert sample_qa_run.id in ids
    assert sample_qa_run_review.id in ids


def test_export_qa_runs_csv(
    client,
    sample_qa_run: QARun,
) -> None:
    response = client.get("/kb/qa-runs/export", params={"fmt": "csv"})

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert 'filename="qa_history.csv"' in response.headers["content-disposition"]

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == [
        "id",
        "created_at",
        "question",
        "answer",
        "sources_json",
        "needs_review",
        "error",
    ]
    assert len(rows) == 2
    assert rows[1][0] == sample_qa_run.id
    assert rows[1][2] == sample_qa_run.question
