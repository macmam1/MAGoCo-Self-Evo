"""Token Pydantic schemas."""
from pydantic import BaseModel


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class TokenPayload(BaseModel):
    """JWT token payload (decoded)."""

    sub: str
    type: str
    exp: int
    iat: int
