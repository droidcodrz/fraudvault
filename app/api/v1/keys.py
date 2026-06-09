import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import AppError
from app.models.api_key import KeyEnvironment
from app.models.user import User
from app.schemas.key import APIKeyCreate, APIKeyCreateResponse, APIKeyResponse
from app.services import key_service

router = APIRouter(prefix="/keys", tags=["keys"])


@router.post("", response_model=APIKeyCreateResponse, status_code=201)
async def create_key(
    body: APIKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key. The raw key is returned once only."""
    env = KeyEnvironment(body.environment) if body.environment in ("live", "test") else KeyEnvironment.live
    api_key, raw_key = await key_service.create_api_key(db, user.id, body.name, env)
    return APIKeyCreateResponse(
        key=raw_key,
        prefix=api_key.key_prefix,
        id=str(api_key.id),
        name=api_key.name,
    )


@router.get("", response_model=list[APIKeyResponse])
async def list_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active API keys for the current user."""
    keys = await key_service.list_api_keys(db, user.id)
    return [
        APIKeyResponse(
            id=str(k.id),
            prefix=k.key_prefix,
            name=k.name,
            environment=k.environment.value,
            hit_count=k.hit_count,
            last_used_at=k.last_used_at.isoformat() if k.last_used_at else None,
        )
        for k in keys
    ]


@router.delete("/{key_id}", status_code=204)
async def delete_key(
    key_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate an API key."""
    deleted = await key_service.deactivate_api_key(db, user.id, key_id)
    if not deleted:
        raise AppError("NOT_FOUND", "API key not found", 404)
    return Response(status_code=204)
