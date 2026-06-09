from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import AuthContext, get_auth_context
from app.schemas.usage import UsageResponse
from app.services import billing_service

router = APIRouter(tags=["usage"])


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    """Get hit count breakdown for the current billing period."""
    stats = await billing_service.get_usage_stats(db, auth.user.id)
    return UsageResponse(**stats)
