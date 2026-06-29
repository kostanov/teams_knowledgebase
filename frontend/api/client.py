from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field


class DocumentListItem(BaseModel):
    id: str
    title: str
    created_at: datetime


class DocumentDetail(DocumentListItem):
    text: str


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    text: str = Field(..., min_length=1, max_length=100_000)


class SourceItem(BaseModel):
    document_id: str = ""
    quote: str


class AskResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    needs_review: bool


class QARunListItem(BaseModel):
    id: str
    question: str
    needs_review: bool
    created_at: datetime


class QARunDetail(QARunListItem):
    answer: str
    sources: list[SourceItem]
    error: str | None = None


class AuditRunListItem(BaseModel):
    id: str
    action: str
    status: str
    error: str | None
    duration_ms: int
    created_at: datetime


class AuditRunDetail(AuditRunListItem):
    input: str
    output: str


class BackendAPIError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class BackendClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.request(method, url, json=json, params=params)
        except httpx.RequestError as error:
            raise BackendAPIError(
                f"Backend недоступен: {error}",
            ) from error

        if response.status_code >= 400:
            detail = response.text
            try:
                payload = response.json()
                if isinstance(payload, dict) and "detail" in payload:
                    detail = str(payload["detail"])
            except ValueError:
                pass
            raise BackendAPIError(detail, status_code=response.status_code)

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def list_documents(self) -> list[DocumentListItem]:
        data = self._request("GET", "/kb/documents")
        return [DocumentListItem.model_validate(item) for item in data]

    def get_document(self, document_id: str) -> DocumentDetail:
        data = self._request("GET", f"/kb/documents/{document_id}")
        return DocumentDetail.model_validate(data)

    def create_document(self, payload: DocumentCreate) -> str:
        data = self._request(
            "POST",
            "/kb/documents",
            json=payload.model_dump(),
        )
        return data["document_id"]

    def ask(self, question: str) -> AskResponse:
        data = self._request("POST", "/kb/ask", json={"question": question})
        return AskResponse.model_validate(data)

    def list_qa_runs(
        self,
        *,
        needs_review: bool | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[QARunListItem]:
        params: dict[str, Any] = {"limit": limit}
        if needs_review is not None:
            params["needs_review"] = needs_review
        if search:
            params["search"] = search
        data = self._request("GET", "/kb/qa-runs", params=params)
        return [QARunListItem.model_validate(item) for item in data]

    def get_qa_run(self, run_id: str) -> QARunDetail:
        data = self._request("GET", f"/kb/qa-runs/{run_id}")
        return QARunDetail.model_validate(data)

    def export_qa_runs_url(
        self,
        *,
        fmt: str = "jsonl",
        needs_review: bool | None = None,
        search: str | None = None,
    ) -> str:
        params: dict[str, str] = {"fmt": fmt}
        if needs_review is not None:
            params["needs_review"] = "true" if needs_review else "false"
        if search:
            params["search"] = search
        query = httpx.QueryParams(params)
        return f"{self._base_url}/kb/qa-runs/export?{query}"

    def list_audit_runs(
        self,
        *,
        action: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[AuditRunListItem]:
        params: dict[str, Any] = {"limit": limit}
        if action:
            params["action"] = action
        if status:
            params["status"] = status
        data = self._request("GET", "/kb/audit-runs", params=params)
        return [AuditRunListItem.model_validate(item) for item in data]

    def get_audit_run(self, run_id: str) -> AuditRunDetail:
        data = self._request("GET", f"/kb/audit-runs/{run_id}")
        return AuditRunDetail.model_validate(data)

    def health(self) -> bool:
        try:
            data = self._request("GET", "/health")
            return isinstance(data, dict) and data.get("status") == "ok"
        except BackendAPIError:
            return False
