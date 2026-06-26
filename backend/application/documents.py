import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.application.chunking import chunk_text
from backend.llm.openai_service import LLMService
from backend.persistence.models import Document, Snippet
from backend.quality.audit import AuditService
from backend.schemas.documents import DocumentCreate, DocumentListItem
from backend.vector.chroma_store import VectorStore


class DocumentService:
    def __init__(
        self,
        *,
        vector_store: VectorStore | None = None,
        llm_service: LLMService | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self._vector_store = vector_store or VectorStore()
        self._llm_service = llm_service or LLMService()
        self._audit_service = audit_service or AuditService()

    def list_documents(self, db: Session) -> list[DocumentListItem]:
        started = time.perf_counter()
        documents = db.scalars(
            select(Document).order_by(Document.created_at.desc())
        ).all()
        items = [
            DocumentListItem(
                id=doc.id,
                title=doc.title,
                created_at=doc.created_at,
            )
            for doc in documents
        ]
        duration_ms = int((time.perf_counter() - started) * 1000)
        self._audit_service.log(
            db,
            action="get_documents",
            input_data={},
            output_data={"count": len(items)},
            status="success",
            duration_ms=duration_ms,
        )
        db.commit()
        return items

    def get_document(self, db: Session, document_id: str) -> Document | None:
        return db.get(Document, document_id)

    def add_document(
        self,
        db: Session,
        payload: DocumentCreate,
    ) -> str:
        started = time.perf_counter()
        try:
            document = Document(title=payload.title, text=payload.text)
            db.add(document)
            db.flush()

            chunks = chunk_text(payload.text)
            snippets: list[Snippet] = []
            for chunk in chunks:
                snippet = Snippet(document_id=document.id, snippet_text=chunk)
                db.add(snippet)
                snippets.append(snippet)
            db.flush()

            if snippets:
                embeddings = self._llm_service.embed_texts(
                    [snippet.snippet_text for snippet in snippets]
                )
                self._vector_store.index_snippets(
                    snippet_ids=[snippet.id for snippet in snippets],
                    document_ids=[document.id for _ in snippets],
                    texts=[snippet.snippet_text for snippet in snippets],
                    embeddings=embeddings,
                )

            duration_ms = int((time.perf_counter() - started) * 1000)
            output = {"status": "ok", "document_id": document.id}
            self._audit_service.log(
                db,
                action="add_document",
                input_data=payload.model_dump(),
                output_data=output,
                status="success",
                duration_ms=duration_ms,
            )
            db.commit()
            return document.id
        except Exception as error:  # noqa: BLE001
            db.rollback()
            duration_ms = int((time.perf_counter() - started) * 1000)
            self._audit_service.log(
                db,
                action="add_document",
                input_data=payload.model_dump(),
                output_data={},
                status="error",
                error=str(error),
                duration_ms=duration_ms,
            )
            db.commit()
            raise
