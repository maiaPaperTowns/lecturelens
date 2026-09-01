"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object. Values come from the environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", extra="ignore", case_sensitive=False, populate_by_name=True
    )

    app_env: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api"

    database_url: str = "postgresql+psycopg2://lenslab:lenslab@localhost:5432/lecturelens"

    max_upload_mb: int = 25
    upload_dir: Path = Path("/data/uploads")
    models_dir: Path = Path("/models")

    # Comma-separated string in the env; use the `cors_origins` property for the parsed list.
    cors_origins_raw: str = Field(
        "http://localhost:5173,http://localhost:3000", validation_alias="CORS_ORIGINS"
    )

    embedding_dim: int = 128
    concept_model_version: str = "auto"
    difficulty_model_version: str = "auto"

    @property
    def cors_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins_raw.split(",") if item.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    settings = Settings()
    try:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Fall back to a local directory when the configured path is not writable
        settings.upload_dir = Path("./data/uploads").resolve()
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings


settings = get_settings()
