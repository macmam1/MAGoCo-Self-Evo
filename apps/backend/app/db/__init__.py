"""Database connection and session management.

Supports BOTH:
- SQLite (default, zero-dependency — works on any server)
- PostgreSQL (production, via DATABASE_URL env)
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import String

from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {"echo": settings.DEBUG}
if not _is_sqlite:
    _engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
else:
    _engine_kwargs.update(connect_args={"check_same_thread": False})

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass  # models are defined in app/models/*.py