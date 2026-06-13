"""User Pydantic schemas."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


# ===== Base =====
class UserBase(BaseModel):
    """Base user fields."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    full_name: str | None = None


# ===== Create =====
class UserCreate(UserBase):
    """User registration payload."""

    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.USER


# ===== Update =====
class UserUpdate(BaseModel):
    """User update payload (all optional)."""

    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)


# ===== Response =====
class UserResponse(UserBase):
    """User public response (no password)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: datetime | None = None


# ===== Login =====
class UserLogin(BaseModel):
    """User login payload."""

    username_or_email: str
    password: str
