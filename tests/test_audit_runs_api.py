from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.persistence.models import AuditRun


def test_list_audit_runs_empty(client) -> None:
    response = client.get("/kb/audit-runs")

    assert response.status_code == 200
    assert response.json() == []


def test_list_audit_runs_returns_items(client, sample_audit_run: AuditRun) -> None:
    response = client.get("/kb/audit-runs")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == sample_audit_run.id
    assert payload[0]["action"] == "ask"
    assert payload[0]["status"] == "success"
    assert payload[0]["duration_ms"] == 42
    assert payload[0]["error"] is None


def test_list_audit_runs_filter_action(client, db: Session) -> None:
    db.add(
        AuditRun(
            action="ask",
            input="{}",
            output="{}",
            status="success",
            duration_ms=1,
        )
    )
    db.add(
        AuditRun(
            action="get_documents",
            input="{}",
            output="{}",
            status="success",
            duration_ms=2,
        )
    )
    db.commit()

    response = client.get("/kb/audit-runs", params={"action": "ask"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["action"] == "ask"


def test_list_audit_runs_filter_status(client, db: Session) -> None:
    db.add(
        AuditRun(
            action="ask",
            input="{}",
            output="{}",
            status="success",
            duration_ms=1,
        )
    )
    db.add(
        AuditRun(
            action="ask",
            input="{}",
            output="{}",
            status="error",
            error="LLM error",
            duration_ms=2,
        )
    )
    db.commit()

    response = client.get("/kb/audit-runs", params={"status": "error"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["status"] == "error"
    assert payload[0]["error"] == "LLM error"


def test_list_audit_runs_writes_audit(
    client,
    db: Session,
    sample_audit_run: AuditRun,
) -> None:
    response = client.get("/kb/audit-runs")

    assert response.status_code == 200
    audits = list(db.scalars(select(AuditRun)).all())
    assert len(audits) == 2
    actions = {audit.action for audit in audits}
    assert "ask" in actions
    assert "get_audit_runs" in actions


def test_get_audit_run_by_id(client, sample_audit_run: AuditRun) -> None:
    response = client.get(f"/kb/audit-runs/{sample_audit_run.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == sample_audit_run.id
    assert payload["action"] == "ask"
    assert payload["input"] == sample_audit_run.input
    assert payload["output"] == sample_audit_run.output
    assert payload["duration_ms"] == 42


def test_get_audit_run_not_found(client) -> None:
    response = client.get("/kb/audit-runs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["detail"] == "Audit run not found"
