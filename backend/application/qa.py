import time

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.llm.openai_service import LLMService
from backend.quality.audit import AuditService, QualityService
from backend.schemas.ai import AIAnswerRequest, AIAnswerResponse, AISourceQuote
from backend.schemas.qa import AskRequest, AskResponse
from backend.vector.chroma_store import VectorStore


class QAService:
    def __init__(
        self,
        *,
        vector_store: VectorStore | None = None,
        llm_service: LLMService | None = None,
        audit_service: AuditService | None = None,
        quality_service: QualityService | None = None,
    ) -> None:
        self._settings = get_settings()
        self._vector_store = vector_store or VectorStore()
        self._llm_service = llm_service or LLMService()
        self._audit_service = audit_service or AuditService()
        self._quality = quality_service or QualityService()

    def ask(self, db: Session, payload: AskRequest) -> AskResponse:
        started = time.perf_counter()
        input_data = payload.model_dump()

        try:
            query_embedding = self._llm_service.embed_text(payload.question)
        except Exception as error:  # noqa: BLE001
            return self._handle_llm_failure(
                db,
                question=payload.question,
                input_data=input_data,
                started=started,
                error=str(error),
            )

        search_results = self._vector_store.search(
            query_embedding=query_embedding,
            top_k=self._settings.top_k,
        )
        max_similarity = max(
            (item.similarity for item in search_results),
            default=0.0,
        )

        if not search_results or max_similarity < self._settings.similarity_threshold:
            reason = (
                f"Не найдено релевантных фрагментов (max_similarity={max_similarity:.2f})"
            )
            output = self._quality.save_ask_result(
                db,
                question=payload.question,
                answer=self._quality.INSUFFICIENT_DATA_ANSWER,
                sources=[],
                needs_review=True,
                error=reason,
                audit_service=self._audit_service,
                input_data=input_data,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            return AskResponse(**output)

        context = self._build_context(search_results)
        try:
            llm_result, validation_error = self._llm_service.answer_with_retry(
                question=payload.question,
                context=context,
            )
        except Exception as error:  # noqa: BLE001
            return self._handle_llm_failure(
                db,
                question=payload.question,
                input_data=input_data,
                started=started,
                error=str(error),
            )

        if llm_result is None:
            output = self._quality.save_ask_result(
                db,
                question=payload.question,
                answer=self._quality.INSUFFICIENT_DATA_ANSWER,
                sources=[],
                needs_review=True,
                error=validation_error,
                audit_service=self._audit_service,
                input_data=input_data,
                duration_ms=int((time.perf_counter() - started) * 1000),
                status="error",
            )
            return AskResponse(**output)

        sources = self._map_sources(llm_result, search_results)
        answer, sources, needs_review, error = self._quality.enforce_ask_response(
            answer=llm_result.answer,
            sources=sources,
            needs_review=llm_result.needs_review,
            error=validation_error,
            confidence=llm_result.confidence,
        )
        output = self._quality.save_ask_result(
            db,
            question=payload.question,
            answer=answer,
            sources=sources,
            needs_review=needs_review,
            error=error,
            audit_service=self._audit_service,
            input_data=input_data,
            duration_ms=int((time.perf_counter() - started) * 1000),
            status="success" if not error else "error",
        )
        return AskResponse(**output)

    def answer_with_sources(
        self,
        db: Session,
        payload: AIAnswerRequest,
    ) -> AIAnswerResponse:
        started = time.perf_counter()
        input_data = payload.model_dump()
        try:
            result, validation_error = self._llm_service.answer_with_retry(
                question=payload.question,
                context=payload.context,
            )
            if result is None:
                response = AIAnswerResponse(
                    answer=self._quality.INSUFFICIENT_DATA_ANSWER,
                    sources=[],
                    confidence="low",
                    needs_review=True,
                )
                self._audit_service.log(
                    db,
                    action="ai_answer_with_sources",
                    input_data=input_data,
                    output_data=response.model_dump(),
                    status="error",
                    error=validation_error,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
                db.commit()
                return response

            answer, sources, needs_review, error = self._quality.enforce_ask_response(
                answer=result.answer,
                sources=[{"quote": item.quote} for item in result.sources],
                needs_review=result.needs_review,
                error=validation_error,
                confidence=result.confidence,
            )
            response = AIAnswerResponse(
                answer=answer,
                sources=[AISourceQuote(quote=item["quote"]) for item in sources],
                confidence=result.confidence,
                needs_review=needs_review,
            )
            self._audit_service.log(
                db,
                action="ai_answer_with_sources",
                input_data=input_data,
                output_data=response.model_dump(),
                status="success" if not error else "error",
                error=error,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            db.commit()
            return response
        except Exception as error:  # noqa: BLE001
            response = AIAnswerResponse(
                answer=self._quality.LLM_UNAVAILABLE_ANSWER,
                sources=[],
                confidence="low",
                needs_review=True,
            )
            self._audit_service.log(
                db,
                action="ai_answer_with_sources",
                input_data=input_data,
                output_data=response.model_dump(),
                status="error",
                error=str(error),
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            db.commit()
            return response

    def _handle_llm_failure(
        self,
        db: Session,
        *,
        question: str,
        input_data: dict,
        started: float,
        error: str,
    ) -> AskResponse:
        output = self._quality.save_ask_result(
            db,
            question=question,
            answer=self._quality.LLM_UNAVAILABLE_ANSWER,
            sources=[],
            needs_review=True,
            error=error,
            audit_service=self._audit_service,
            input_data=input_data,
            duration_ms=int((time.perf_counter() - started) * 1000),
            status="error",
        )
        return AskResponse(**output)

    @staticmethod
    def _build_context(search_results) -> str:
        parts: list[str] = []
        for index, item in enumerate(search_results, start=1):
            parts.append(
                f"[{index}] document_id={item.document_id}\n{item.snippet_text}"
            )
        return "\n\n".join(parts)

    @staticmethod
    def _map_sources(
        llm_result: AIAnswerResponse,
        search_results,
    ) -> list[dict[str, str]]:
        if not llm_result.sources:
            return []

        document_by_text: dict[str, str] = {}
        for item in search_results:
            document_by_text[item.snippet_text] = item.document_id

        mapped: list[dict[str, str]] = []
        for source in llm_result.sources:
            document_id = ""
            for snippet_text, doc_id in document_by_text.items():
                if source.quote in snippet_text or snippet_text in source.quote:
                    document_id = doc_id
                    break
            if not document_id and search_results:
                document_id = search_results[0].document_id
            mapped.append({"document_id": document_id, "quote": source.quote})
        return mapped
