from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, RegisterRequest, TokenPair, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    user = await auth_service.register_user(db, body.email, body.password, body.full_name)
    access = auth_service.create_access_token(user.id)
    refresh = auth_service.create_refresh_token(user.id)
    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse(id=str(user.id), email=user.email, full_name=user.full_name, plan=user.plan.value, role=user.role.value, email_verified=user.email_verified),
    )


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate and receive JWT tokens."""
    from app.exceptions import AppError

    user = await auth_service.authenticate_user(db, body.email, body.password)
    if not user:
        raise AppError("INVALID_CREDENTIALS", "Invalid email or password", 401)
    access = auth_service.create_access_token(user.id)
    refresh = auth_service.create_refresh_token(user.id)
    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        user=UserResponse(id=str(user.id), email=user.email, full_name=user.full_name, plan=user.plan.value, role=user.role.value, email_verified=user.email_verified),
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh an access token using a refresh token."""
    access = await auth_service.refresh_access_token(db, body.refresh_token)
    payload = auth_service.decode_token(body.refresh_token)
    from sqlalchemy import select
    from app.models.user import User
    import uuid

    result = await db.execute(select(User).where(User.id == uuid.UUID(payload["sub"])))
    user = result.scalar_one()
    return TokenPair(
        access_token=access,
        refresh_token=body.refresh_token,
        user=UserResponse(id=str(user.id), email=user.email, full_name=user.full_name, plan=user.plan.value, role=user.role.value, email_verified=user.email_verified),
    )
