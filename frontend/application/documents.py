from frontend.api.client import (
    BackendAPIError,
    BackendClient,
    DocumentCreate,
    DocumentDetail,
    DocumentListItem,
)
from frontend.config import get_settings


class DocumentsPageService:
    def __init__(self, client: BackendClient | None = None) -> None:
        settings = get_settings()
        self._client = client or BackendClient(settings.backend_api_url)

    def list_documents(self) -> list[DocumentListItem]:
        return self._client.list_documents()

    def get_document(self, document_id: str) -> DocumentDetail:
        return self._client.get_document(document_id)

    def create_document(self, title: str, text: str) -> str:
        return self._client.create_document(
            DocumentCreate(title=title.strip(), text=text.strip())
        )

    @property
    def backend_healthy(self) -> bool:
        return self._client.health()


DocumentsServiceError = BackendAPIError
