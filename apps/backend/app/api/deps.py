"""API dependencies."""
import uuid
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db import get_db
from app.models.user import User, UserRole
from app.services.auth import AuthService

# HTTPBearer for JWT in Authorization header
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject",
        )

    user = await AuthService.get_by_id(db, uuid.UUID(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    return user


async def get_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Resolve human (JWT) or agent (mag_ key) to an identity dict.

    Returns {"kind": "human"|"agent", "id": str, "name": str, "scopes": [...]}.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    if token.startswith("mag_"):
        from magoco_core.agents.identities import get_identity_store
        ident = get_identity_store().verify(token)
        if not ident:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or revoked agent key",
            )
        return {"kind": "agent", "id": ident["id"], "name": ident["name"],
                "scopes": ident["scopes"]}
    # Human path: valid access JWT required.
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from e
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from e
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")
    user = await AuthService.get_by_id(db, uuid.UUID(payload.get("sub")))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User unavailable")
    return {"kind": "human", "id": str(user.id), "name": user.username, "scopes": ["*"]}


async def get_optional_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> Optional[dict]:
    """Best-effort identity: human/agent dict, or None when anonymous.

    Never raises — for endpoints that attribute when possible but stay open.
    """
    if credentials is None:
        return None
    token = credentials.credentials
    if token.startswith("mag_"):
        try:
            from magoco_core.agents.identities import get_identity_store
            ident = get_identity_store().verify(token)
            if ident:
                return {"kind": "agent", "id": ident["id"], "name": ident["name"],
                        "scopes": ident["scopes"]}
        except Exception:
            pass
        return None
    try:
        payload = decode_token(token)
        if payload.get("type") == "access" and payload.get("sub"):
            return {"kind": "human", "id": payload["sub"], "name": "",
                    "scopes": ["*"]}
    except Exception:
        pass
    return None


def require_role(*allowed_roles: UserRole):

    async def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role} not allowed. Need: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return _check_role
