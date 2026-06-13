"""Auth service — business logic for authentication."""
import uuid
from datetime import datetime, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.schemas.token import TokenResponse
from app.schemas.user import UserCreate, UserLogin


class AuthError(Exception):
    """Base auth error."""


class UserAlreadyExistsError(AuthError):
    """User with email/username already exists."""


class InvalidCredentialsError(AuthError):
    """Invalid username/email or password."""


class InactiveUserError(AuthError):
    """User is inactive."""


class InvalidTokenError(AuthError):
    """Invalid or expired token."""


class AuthService:
    """Authentication business logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ===== Register =====
    async def register(self, payload: UserCreate) -> User:
        """Register a new user."""
        # Check existing
        existing = await self.db.execute(
            select(User).where(
                (User.email == payload.email) | (User.username == payload.username)
            )
        )
        if existing.scalar_one_or_none():
            raise UserAlreadyExistsError("Email or username already registered")

        user = User(
            email=payload.email,
            username=payload.username,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=payload.role if payload.role else UserRole.USER,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    # ===== Login =====
    async def login(self, payload: UserLogin) -> tuple[User, TokenResponse]:
        """Authenticate user and return tokens."""
        # Find user by email OR username
        result = await self.db.execute(
            select(User).where(
                (User.email == payload.username_or_email)
                | (User.username == payload.username_or_email)
            )
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(payload.password, user.password_hash):
            raise InvalidCredentialsError("Invalid credentials")

        if not user.is_active:
            raise InactiveUserError("User account is inactive")

        # Update last login
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(user)

        # Generate tokens
        tokens = self._generate_tokens(user)
        return user, tokens

    # ===== Refresh =====
    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Exchange refresh token for new access + refresh tokens."""
        try:
            payload = decode_token(refresh_token)
        except jwt.ExpiredSignatureError as e:
            raise InvalidTokenError("Refresh token expired") from e
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError("Invalid refresh token") from e

        if payload.get("type") != "refresh":
            raise InvalidTokenError("Token is not a refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError("Token missing subject")

        result = await self.db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            raise InvalidTokenError("User not found or inactive")

        return self._generate_tokens(user)

    # ===== Helpers =====
    def _generate_tokens(self, user: User) -> TokenResponse:
        """Generate access + refresh tokens for a user."""
        extra = {"role": user.role.value, "username": user.username}
        access = create_access_token(user.id, extra=extra)
        refresh = create_refresh_token(user.id)
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> User | None:
        """Get user by username."""
        result = await db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()
