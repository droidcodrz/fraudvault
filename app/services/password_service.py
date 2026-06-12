import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import AppError
from app.models.password_reset import EmailVerification, PasswordReset
from app.models.user import User
from app.services.auth_service import hash_password


async def create_password_reset(db: AsyncSession, email: str) -> PasswordReset | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return None

    token = secrets.token_urlsafe(48)
    reset = PasswordReset(
        user_id=user.id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(reset)
    await db.flush()
    return reset


async def confirm_password_reset(db: AsyncSession, token: str, new_password: str) -> bool:
    result = await db.execute(
        select(PasswordReset).where(
            PasswordReset.token == token,
            PasswordReset.is_used.is_(False),
        )
    )
    reset = result.scalar_one_or_none()
    if not reset:
        raise AppError("INVALID_TOKEN", "Reset token not found or already used", 404)
    expires = reset.expires_at.replace(tzinfo=timezone.utc) if reset.expires_at.tzinfo is None else reset.expires_at
    if expires < datetime.now(timezone.utc):
        raise AppError("TOKEN_EXPIRED", "Reset token has expired", 410)

    user_result = await db.execute(select(User).where(User.id == reset.user_id))
    user = user_result.scalar_one()
    user.password_hash = hash_password(new_password)
    reset.is_used = True
    await db.flush()
    return True


async def create_email_verification(db: AsyncSession, user_id) -> EmailVerification:
    token = secrets.token_urlsafe(48)
    verification = EmailVerification(
        user_id=user_id,
        token=token,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(verification)
    await db.flush()
    return verification


async def confirm_email_verification(db: AsyncSession, token: str) -> bool:
    result = await db.execute(
        select(EmailVerification).where(
            EmailVerification.token == token,
            EmailVerification.is_used.is_(False),
        )
    )
    verification = result.scalar_one_or_none()
    if not verification:
        raise AppError("INVALID_TOKEN", "Verification token not found", 404)
    expires = verification.expires_at.replace(tzinfo=timezone.utc) if verification.expires_at.tzinfo is None else verification.expires_at
    if expires < datetime.now(timezone.utc):
        raise AppError("TOKEN_EXPIRED", "Verification token has expired", 410)

    user_result = await db.execute(select(User).where(User.id == verification.user_id))
    user = user_result.scalar_one()
    user.email_verified = True
    verification.is_used = True
    await db.flush()
    return True
