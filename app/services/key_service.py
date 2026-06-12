import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.api_key import APIKey, KeyEnvironment


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key(environment: str = "live") -> tuple[str, str, str]:
    token = secrets.token_urlsafe(32)
    raw_key = f"fv_{environment}_{token}"
    prefix = raw_key[:16]
    key_hash = _hash_key(raw_key)
    return raw_key, prefix, key_hash


async def create_api_key(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str | None,
    environment: KeyEnvironment = KeyEnvironment.live,
    org_id: uuid.UUID | None = None,
) -> tuple[APIKey, str]:
    raw_key, prefix, key_hash = generate_api_key(environment.value)
    api_key = APIKey(
        user_id=user_id,
        org_id=org_id,
        key_prefix=prefix,
        key_hash=key_hash,
        name=name,
        environment=environment,
    )
    db.add(api_key)
    await db.flush()
    return api_key, raw_key


async def validate_api_key(db: AsyncSession, raw_key: str) -> APIKey | None:
    key_hash = _hash_key(raw_key)
    result = await db.execute(
        select(APIKey)
        .options(selectinload(APIKey.user))
        .where(APIKey.key_hash == key_hash, APIKey.is_active.is_(True))
    )
    api_key = result.scalar_one_or_none()
    if api_key:
        api_key.last_used_at = datetime.now(timezone.utc)
        await db.flush()
    return api_key


async def list_api_keys(db: AsyncSession, user_id: uuid.UUID, org_id: uuid.UUID | None = None) -> list[APIKey]:
    if org_id:
        q = select(APIKey).where(APIKey.org_id == org_id, APIKey.is_active.is_(True))
    else:
        q = select(APIKey).where(APIKey.user_id == user_id, APIKey.is_active.is_(True))
    result = await db.execute(q)
    return list(result.scalars().all())


async def deactivate_api_key(db: AsyncSession, user_id: uuid.UUID, key_id: uuid.UUID) -> bool:
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
    )
    api_key = result.scalar_one_or_none()
    if not api_key:
        return False
    api_key.is_active = False
    await db.flush()
    return True


async def increment_hit_count(db: AsyncSession, api_key_id: uuid.UUID) -> None:
    await db.execute(
        update(APIKey)
        .where(APIKey.id == api_key_id)
        .values(
            hit_count=APIKey.hit_count + 1,
            monthly_hit_count=APIKey.monthly_hit_count + 1,
        )
    )
