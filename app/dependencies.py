import uuid
from dataclasses import dataclass

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.exceptions import AppError
from app.models.api_key import APIKey
from app.models.user import User
from app.services.auth_service import decode_token
from app.services.key_service import validate_api_key

security = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    user: User
    api_key: APIKey | None = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise AppError("UNAUTHORIZED", "Missing authentication credentials", 401)
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise AppError("INVALID_TOKEN", "Invalid access token", 401)
    user_id = payload.get("sub")
    if not user_id:
        raise AppError("INVALID_TOKEN", "Invalid token payload", 401)
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise AppError("UNAUTHORIZED", "User not found or inactive", 401)
    return user


async def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    if x_api_key:
        api_key = await validate_api_key(db, x_api_key)
        if not api_key:
            raise AppError("INVALID_API_KEY", "Invalid or inactive API key", 401)
        if not api_key.user.is_active:
            raise AppError("UNAUTHORIZED", "User account is inactive", 401)
        return AuthContext(user=api_key.user, api_key=api_key)

    user = await get_current_user(credentials, db)
    return AuthContext(user=user, api_key=None)
