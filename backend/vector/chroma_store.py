from dataclasses import dataclass

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

from backend.config import Settings, get_settings


@dataclass
class SearchResult:
    snippet_id: str
    document_id: str
    snippet_text: str
    similarity: float


class VectorStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = self._build_client()
        self._collection = self._get_or_create_collection()

    def _build_client(self) -> ClientAPI:
        if self._settings.chroma_host:
            return chromadb.HttpClient(
                host=self._settings.chroma_host,
                port=self._settings.chroma_port or 8000,
                ssl=self._settings.chroma_ssl,
                headers=(
                    {"x-chroma-token": self._settings.chroma_api_key}
                    if self._settings.chroma_api_key
                    else None
                ),
                tenant=self._settings.chroma_tenant or chromadb.DEFAULT_TENANT,
                database=self._settings.chroma_database,
            )
        persist_path = self._settings.chroma_persist_path
        if persist_path is not None:
            persist_path.mkdir(parents=True, exist_ok=True)
            return chromadb.PersistentClient(path=str(persist_path))
        return chromadb.Client()

    def _get_or_create_collection(self) -> Collection:
        return self._client.get_or_create_collection(
            name=self._settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    def index_snippets(
        self,
        *,
        snippet_ids: list[str],
        document_ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
    ) -> None:
        payload = {
            "ids": snippet_ids,
            "embeddings": embeddings,
            "documents": texts,
            "metadatas": [{"document_id": doc_id} for doc_id in document_ids],
        }
        try:
            self._collection.upsert(**payload)
        except chromadb.errors.NotFoundError:
            self._collection = self._get_or_create_collection()
            self._collection.upsert(**payload)

    def delete_snippets(self, snippet_ids: list[str]) -> None:
        if snippet_ids:
            self._collection.delete(ids=snippet_ids)

    def search(
        self,
        *,
        query_embedding: list[float],
        top_k: int,
    ) -> list[SearchResult]:
        try:
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
        except chromadb.errors.NotFoundError:
            self._collection = self._get_or_create_collection()
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        items: list[SearchResult] = []
        for snippet_id, text, metadata, distance in zip(
            ids, documents, metadatas, distances, strict=True
        ):
            document_id = (metadata or {}).get("document_id", "")
            similarity = max(0.0, 1.0 - float(distance))
            items.append(
                SearchResult(
                    snippet_id=snippet_id,
                    document_id=document_id,
                    snippet_text=text or "",
                    similarity=similarity,
                )
            )
        return items

    def reset_collection(self) -> None:
        name = self._settings.chroma_collection
        try:
            self._client.delete_collection(name)
        except Exception:  # noqa: BLE001
            pass
        self._collection = self._get_or_create_collection()
