"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health
from app.core.config import settings

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: startup + shutdown."""
    # Startup
    logger.info(
        "app.starting",
        name=settings.PROJECT_NAME,
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        debug=settings.DEBUG,
    )

    yield

    # Shutdown
    logger.info("app.stopping")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Multi-Agent Go-Coordinator with Self-Evolution",
        version="0.1.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "name": settings.PROJECT_NAME,
            "version": "0.1.0",
            "status": "running",
            "docs": "/docs" if settings.DEBUG else "disabled",
        }

    return app


app = create_app()
