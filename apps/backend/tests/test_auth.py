"""Auth API tests."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient) -> None:
    """Test user registration."""
    payload = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "securepass123",
        "full_name": "Test User",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate(client: AsyncClient) -> None:
    """Test duplicate registration is rejected."""
    payload = {
        "email": "dup@example.com",
        "username": "dupuser",
        "password": "securepass123",
    }
    r1 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_register_validation(client: AsyncClient) -> None:
    """Test password length validation."""
    payload = {
        "email": "weak@example.com",
        "username": "weakuser",
        "password": "short",  # too short
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    """Test successful login."""
    # Register
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "username": "loginuser",
            "password": "securepass123",
        },
    )

    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "loginuser", "password": "securepass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    """Test wrong password is rejected."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "wrong@example.com",
            "username": "wronguser",
            "password": "securepass123",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "wronguser", "password": "WRONGPASS"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_unauthorized(client: AsyncClient) -> None:
    """Test /me without token."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_authorized(client: AsyncClient) -> None:
    """Test /me with valid token."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "username": "meuser",
            "password": "securepass123",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "meuser", "password": "securepass123"},
    )
    token = login.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "meuser"


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient) -> None:
    """Test refresh token flow."""
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "refresh@example.com",
            "username": "refreshuser",
            "password": "securepass123",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "refreshuser", "password": "securepass123"},
    )
    refresh = login.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
