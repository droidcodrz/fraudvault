from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import AppError
from app.models.user import User
from app.schemas.auth import UserResponse
from app.services.auth_service import hash_password, verify_password

router = APIRouter(prefix="/me", tags=["profile"])


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


@router.get("", response_model=UserResponse)
async def get_profile(user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        plan=user.plan.value,
        role=user.role.value,
        email_verified=user.email_verified,
    )


@router.put("", response_model=UserResponse)
async def update_profile(
    body: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.email is not None and body.email != user.email:
        user.email = body.email
        user.email_verified = False
    await db.flush()
    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        plan=user.plan.value,
        role=user.role.value,
        email_verified=user.email_verified,
    )


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, user.password_hash):
        raise AppError("INVALID_PASSWORD", "Current password is incorrect", 400)
    user.password_hash = hash_password(body.new_password)
    await db.flush()
    return {"message": "Password changed successfully"}
