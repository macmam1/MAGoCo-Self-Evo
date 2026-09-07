"""Application settings (Pydantic v2)."""
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All app settings, loaded from .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ===== General =====
    PROJECT_NAME: str = "MAGoCo-Self-Evo"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # ===== Server =====
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:8000"]
    )

    # ===== Database =====
    # Default: SQLite (zero-dependency, works on ANY server).
    # For production: set DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
    DATABASE_URL: str = "sqlite+aiosqlite:///./magoco.db"

    # ===== Redis (optional) =====
    # Used for queue/cache. Falls back to in-memory when empty.
    REDIS_URL: str = ""
    REDIS_CELERY_URL: str = ""

    # ===== Auth =====
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ===== LLM Providers =====
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""
    HUGGINGFACE_HUB_TOKEN: str = ""
    OLLAMA_BASE_URL: str = "http://ollama:11434"

    # ===== Scheduler (kill-switchable background + cron tasks) =====
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_TICK_SECONDS: float = 30.0

    # ===== Storage =====
    STORAGE_BACKEND: Literal["local", "hf_datasets", "s3", "gcs"] = "local"
    STORAGE_LOCAL_PATH: str = "/app/storage"
    HF_STORAGE_REPO: str = ""
    S3_BUCKET: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_ENDPOINT: str = ""
    GCS_BUCKET: str = ""

    # ===== External Services =====
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""


settings = Settings()
