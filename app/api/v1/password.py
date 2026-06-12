from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import password_service

router = APIRouter(prefix="/auth", tags=["auth"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    reset = await password_service.create_password_reset(db, body.email)
    await db.commit()
    if reset:
        return {
            "message": "If an account exists with that email, a reset link has been generated.",
            "token": reset.token,
        }
    return {"message": "If an account exists with that email, a reset link has been generated."}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await password_service.confirm_password_reset(db, body.token, body.password)
    await db.commit()
    return {"message": "Password has been reset successfully."}


@router.post("/verify-email")
async def verify_email(
    body: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
):
    await password_service.confirm_email_verification(db, body.token)
    await db.commit()
    return {"message": "Email verified successfully."}


@router.post("/send-verification")
async def send_verification(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.email_verified:
        return {"message": "Email is already verified."}
    verification = await password_service.create_email_verification(db, user.id)
    await db.commit()
    return {"message": "Verification email sent.", "token": verification.token}
