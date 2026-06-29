from frontend.api.client import AskResponse, BackendAPIError, BackendClient
from frontend.config import get_settings


class QuestionsPageService:
    def __init__(self, client: BackendClient | None = None) -> None:
        settings = get_settings()
        self._client = client or BackendClient(settings.backend_api_url)

    def ask(self, question: str) -> AskResponse:
        return self._client.ask(question.strip())

    def get_document_title(self, document_id: str) -> str:
        try:
            document = self._client.get_document(document_id)
        except BackendAPIError:
            return document_id
        return document.title


QuestionsServiceError = BackendAPIError
