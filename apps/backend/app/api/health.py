"""Health check endpoints."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    environment: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness/readiness probe."""
    return HealthResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        version="0.1.0",
        environment=settings.ENVIRONMENT,
    )


@router.get("/ping")
async def ping() -> dict[str, str]:
    """Simple ping."""
    return {"pong": "true"}
