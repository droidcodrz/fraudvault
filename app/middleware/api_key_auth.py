from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.database import async_session_factory
from app.services.key_service import validate_api_key
from app.dependencies import AuthContext
from app.services.auth_service import decode_token
from sqlalchemy import select
from app.models.user import User
import uuid


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Attach auth context to request state when JWT or API key is present."""

    async def dispatch(self, request: Request, call_next):
        api_key_header = request.headers.get("X-API-Key")
        auth_header = request.headers.get("Authorization")

        async with async_session_factory() as db:
            try:
                if api_key_header:
                    api_key = await validate_api_key(db, api_key_header)
                    if api_key:
                        request.state.auth_context = AuthContext(user=api_key.user, api_key=api_key)
                elif auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ", 1)[1]
                    payload = decode_token(token)
                    if payload.get("type") == "access" and payload.get("sub"):
                        result = await db.execute(
                            select(User).where(User.id == uuid.UUID(payload["sub"]))
                        )
                        user = result.scalar_one_or_none()
                        if user and user.is_active:
                            request.state.auth_context = AuthContext(user=user, api_key=None)
                await db.commit()
            except Exception:
                await db.rollback()

        return await call_next(request)
