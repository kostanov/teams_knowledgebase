from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="sqlite:///./data/db/knowledge_base.db",
        alias="DATABASE_URL",
    )
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_answering_model: str = Field(
        default="gpt-4o-mini",
        alias="OPENAI_ANSWERING_MODEL",
    )
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="OPENAI_EMBEDDING_MODEL",
    )
    openai_temperature: float = Field(default=0.0, alias="OPENAI_TEMPERATURE")
    openai_max_tokens: int = Field(default=4096, alias="OPENAI_MAX_TOKENS")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")

    top_k: int = Field(default=5, alias="TOP_K")
    similarity_threshold: float = Field(default=0.5, alias="SIMILARITY_THRESHOLD")

    chroma_collection: str = Field(default="knowledge_base", alias="CHROMA_COLLECTION")
    chroma_persist_directory: str | None = Field(
        default="./data/chroma",
        alias="CHROMA_PERSIST_DIRECTORY",
    )
    chroma_host: str | None = Field(default=None, alias="CHROMA_HOST")
    chroma_port: int | None = Field(default=None, alias="CHROMA_PORT")
    chroma_ssl: bool = Field(default=False, alias="CHROMA_SSL")
    chroma_api_key: str | None = Field(default=None, alias="CHROMA_API_KEY")
    chroma_tenant: str | None = Field(default=None, alias="CHROMA_TENANT")
    chroma_database: str = Field(default="default_database", alias="CHROMA_DATABASE")

    @field_validator(
        "chroma_host",
        "chroma_api_key",
        "chroma_tenant",
        "openai_base_url",
        mode="before",
    )
    @classmethod
    def empty_str_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("chroma_port", mode="before")
    @classmethod
    def empty_port_to_none(cls, value: Any) -> Any:
        if value in ("", None):
            return None
        return value

    title_max_length: int = 500
    text_max_length: int = 100_000
    question_max_length: int = 2_000
    context_max_length: int = 50_000

    @property
    def chroma_persist_path(self) -> Path | None:
        if not self.chroma_persist_directory:
            return None
        path = Path(self.chroma_persist_directory)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    @property
    def database_path(self) -> Path | None:
        if self.database_url.startswith("sqlite:///"):
            db_path = self.database_url.removeprefix("sqlite:///")
            path = Path(db_path)
            if not path.is_absolute():
                path = PROJECT_ROOT / path
            return path
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()
