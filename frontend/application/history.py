from frontend.api.client import (
    BackendAPIError,
    BackendClient,
    QARunDetail,
    QARunListItem,
)
from frontend.config import get_settings


class HistoryPageService:
    def __init__(self, client: BackendClient | None = None) -> None:
        settings = get_settings()
        self._client = client or BackendClient(settings.backend_api_url)

    def list_runs(
        self,
        *,
        needs_review: bool | None = None,
        search: str | None = None,
        limit: int = 100,
    ) -> list[QARunListItem]:
        return self._client.list_qa_runs(
            needs_review=needs_review,
            search=search.strip() if search else None,
            limit=limit,
        )

    def get_run(self, run_id: str) -> QARunDetail:
        return self._client.get_qa_run(run_id)

    def export_url(
        self,
        *,
        fmt: str = "jsonl",
        needs_review: bool | None = None,
        search: str | None = None,
    ) -> str:
        return self._client.export_qa_runs_url(
            fmt=fmt,
            needs_review=needs_review,
            search=search.strip() if search else None,
        )


HistoryServiceError = BackendAPIError
