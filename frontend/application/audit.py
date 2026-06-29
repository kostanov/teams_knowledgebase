from frontend.api.client import (
    AuditRunDetail,
    AuditRunListItem,
    BackendAPIError,
    BackendClient,
)
from frontend.config import get_settings


class AuditPageService:
    def __init__(self, client: BackendClient | None = None) -> None:
        settings = get_settings()
        self._client = client or BackendClient(settings.backend_api_url)

    def list_runs(
        self,
        *,
        action: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[AuditRunListItem]:
        return self._client.list_audit_runs(
            action=action.strip() if action else None,
            status=status.strip() if status else None,
            limit=limit,
        )

    def get_run(self, run_id: str) -> AuditRunDetail:
        return self._client.get_audit_run(run_id)

    def list_actions(self, runs: list[AuditRunListItem]) -> list[str]:
        return sorted({run.action for run in runs})


AuditServiceError = BackendAPIError
