from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.plan import Plan

router = APIRouter(tags=["plans"])


@router.get("/plans")
async def list_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order)
    )
    plans = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "display_name": p.display_name,
            "description": p.description,
            "monthly_price_cents": p.monthly_price_cents,
            "annual_price_cents": p.annual_price_cents,
            "monthly_detection_limit": p.monthly_detection_limit,
            "rate_limit_per_minute": p.rate_limit_per_minute,
            "rate_limit_per_day": p.rate_limit_per_day,
            "max_file_size_mb": p.max_file_size_mb,
            "max_members": p.max_members,
            "max_api_keys": p.max_api_keys,
            "features": p.features,
            "stripe_monthly_price_id": p.stripe_monthly_price_id,
        }
        for p in plans
    ]
