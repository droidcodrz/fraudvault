import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import AppError
from app.models.api_key import APIKey, KeyEnvironment
from app.models.user import User, UserPlan
from app.schemas.key import APIKeyCreate, APIKeyCreateResponse, APIKeyResponse
from app.services import key_service

router = APIRouter(prefix="/keys", tags=["keys"])

PLAN_MAX_API_KEYS = {
    UserPlan.free: 2,
    UserPlan.starter: 5,
    UserPlan.growth: 10,
    UserPlan.pro: 25,
    UserPlan.enterprise: None,
}


@router.post("", response_model=APIKeyCreateResponse, status_code=201)
async def create_key(
    body: APIKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new API key. The raw key is returned once only."""
    max_keys = PLAN_MAX_API_KEYS.get(user.plan, PLAN_MAX_API_KEYS[UserPlan.free])
    if max_keys is not None:
        count_q = select(func.count()).select_from(APIKey).where(
            APIKey.user_id == user.id, APIKey.is_active.is_(True)
        )
        current_count = (await db.execute(count_q)).scalar() or 0
        if current_count >= max_keys:
            raise AppError("LIMIT_REACHED", f"Your plan allows a maximum of {max_keys} API keys", 403)

    env = KeyEnvironment(body.environment) if body.environment in ("live", "test") else KeyEnvironment.live
    api_key, raw_key = await key_service.create_api_key(db, user.id, body.name, env, org_id=user.current_org_id)
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
    keys = await key_service.list_api_keys(db, user.id, org_id=user.current_org_id)
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
