import json
from typing import Any

from openai import OpenAI

from backend.config import Settings, get_settings
from backend.schemas.ai import AIAnswerResponse

SYSTEM_PROMPT = """Ты — ассистент, который отвечает ТОЛЬКО на основе предоставленного контекста.
Если ответа нет в контексте — установи needs_review=true и напиши "Данных недостаточно".
Если needs_review=false — поле sources должно содержать минимум 1 цитату из контекста.
Верни ответ строго в формате JSON."""

RETRY_PROMPT_SUFFIX = (
    "\n\nВАЖНО: верни ТОЛЬКО валидный JSON без markdown и пояснений."
)

ANSWER_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"quote": {"type": "string"}},
                "required": ["quote"],
                "additionalProperties": False,
            },
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "needs_review": {"type": "boolean"},
    },
    "required": ["answer", "sources", "confidence", "needs_review"],
    "additionalProperties": False,
}


class LLMService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        client_kwargs: dict[str, Any] = {"api_key": self._settings.openai_api_key}
        if self._settings.openai_base_url:
            client_kwargs["base_url"] = self._settings.openai_base_url
        self._client = OpenAI(**client_kwargs)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(
            model=self._settings.openai_embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def answer_with_context(
        self,
        *,
        question: str,
        context: str,
        retry: bool = False,
    ) -> AIAnswerResponse:
        user_content = (
            f"Контекст:\n{context}\n\nВопрос:\n{question}"
            f"{RETRY_PROMPT_SUFFIX if retry else ''}"
        )
        response = self._client.chat.completions.create(
            model=self._settings.openai_answering_model,
            temperature=self._settings.openai_temperature,
            max_tokens=self._settings.openai_max_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "answer_with_sources",
                    "strict": True,
                    "schema": ANSWER_JSON_SCHEMA,
                },
            },
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        payload = json.loads(raw)
        return AIAnswerResponse.model_validate(payload)

    def answer_with_retry(
        self,
        *,
        question: str,
        context: str,
    ) -> tuple[AIAnswerResponse | None, str | None]:
        try:
            return self.answer_with_context(question=question, context=context), None
        except Exception as first_error:  # noqa: BLE001
            try:
                return (
                    self.answer_with_context(
                        question=question,
                        context=context,
                        retry=True,
                    ),
                    None,
                )
            except Exception as second_error:  # noqa: BLE001
                return None, (
                    f"Ошибка валидации JSON от LLM: {second_error}; "
                    f"первая попытка: {first_error}"
                )
