"""Health check tests."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_root() -> None:
    """Test root endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "MAGoCo-Self-Evo"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health() -> None:
    """Test health endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_ping() -> None:
    """Test ping endpoint."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json() == {"pong": "true"}
