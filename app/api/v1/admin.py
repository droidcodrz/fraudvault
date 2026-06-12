import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.exceptions import AppError
from app.models.user import User, UserRole
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(user: User):
    if user.role != UserRole.admin:
        raise AppError("FORBIDDEN", "Admin access required", 403)


class UpdatePlanRequest(BaseModel):
    plan: str


@router.get("/stats")
async def get_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    return await admin_service.get_system_stats(db)


@router.get("/users")
async def list_users(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
):
    _require_admin(user)
    return await admin_service.list_users(db, page, per_page, search)


@router.put("/users/{user_id}/plan")
async def update_plan(
    user_id: uuid.UUID,
    body: UpdatePlanRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    ok = await admin_service.update_user_plan(db, user_id, body.plan)
    if not ok:
        raise AppError("NOT_FOUND", "User not found", 404)
    await db.commit()
    return {"status": "updated"}


@router.put("/users/{user_id}/toggle-active")
async def toggle_active(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)
    is_active = await admin_service.toggle_user_active(db, user_id)
    await db.commit()
    return {"is_active": is_active}
