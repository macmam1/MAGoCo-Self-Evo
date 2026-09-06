"""Core configuration for MAGoCo."""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # LLM Gateway settings
    LLM_CACHE_ENABLED: bool = True
    LLM_CACHE_TTL_SECONDS: int = 3600  # 1 hour

    # Capability gate + deferred queue (kill-switch: set false to never defer)
    DEFERRED_QUEUE_ENABLED: bool = True
    # Only defer when gap >= this (conservative: 2 tiers). 1 = aggressive.
    DEFERRED_QUEUE_MIN_GAP: int = 2

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./magoco.db"

    # Security
    VAULT_MASTER_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()