from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    backend_api_url: str = Field(
        default="http://localhost:8000",
        alias="BACKEND_API_URL",
    )
    frontend_host: str = Field(default="0.0.0.0", alias="FRONTEND_HOST")
    frontend_port: int = Field(default=3000, alias="FRONTEND_PORT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
