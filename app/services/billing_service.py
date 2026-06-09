import time
import uuid
from datetime import datetime, timezone

import stripe
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.api_key import APIKey
from app.models.billing import BillingEvent, HitType
from app.models.user import User, UserPlan
from app.services.key_service import increment_hit_count

settings = get_settings()

PLAN_MONTHLY_LIMITS = {
    UserPlan.free: 50,
    UserPlan.starter: 1000,
    UserPlan.growth: 10000,
    UserPlan.pro: 50000,
    UserPlan.enterprise: None,
}

PLAN_RATE_LIMITS = {
    UserPlan.free: (10, 100),
    UserPlan.starter: (60, 1000),
    UserPlan.growth: (120, 10000),
    UserPlan.pro: (300, 50000),
    UserPlan.enterprise: (None, None),
}


def get_plan_limit(plan: UserPlan) -> int | None:
    return PLAN_MONTHLY_LIMITS.get(plan)


async def get_user_monthly_hits(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.coalesce(func.sum(APIKey.monthly_hit_count), 0)).where(APIKey.user_id == user_id)
    )
    return int(result.scalar() or 0)


async def check_quota(db: AsyncSession, user: User) -> bool:
    limit = get_plan_limit(user.plan)
    if limit is None:
        return True
    hits = await get_user_monthly_hits(db, user.id)
    if user.plan == UserPlan.free and hits >= limit:
        return False
    return True


async def record_hit(
    db: AsyncSession,
    user_id: uuid.UUID,
    api_key_id: uuid.UUID | None,
    job_id: uuid.UUID,
    hit_type: HitType,
) -> BillingEvent:
    stripe_event_id = None
    if settings.stripe_secret_key:
        stripe.api_key = settings.stripe_secret_key
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
        if user.stripe_customer_id:
            try:
                event = stripe.billing.MeterEvent.create(
                    event_name=settings.stripe_meter_event_name,
                    payload={
                        "stripe_customer_id": user.stripe_customer_id,
                        "value": "1",
                    },
                    timestamp=int(time.time()),
                )
                stripe_event_id = event.get("identifier") if isinstance(event, dict) else getattr(event, "identifier", None)
            except Exception:
                pass

    billing_event = BillingEvent(
        user_id=user_id,
        api_key_id=api_key_id,
        job_id=job_id,
        stripe_meter_event_id=stripe_event_id,
        hit_type=hit_type,
    )
    db.add(billing_event)

    if api_key_id:
        await increment_hit_count(db, api_key_id)

    await db.flush()
    return billing_event


async def get_usage_stats(db: AsyncSession, user_id: uuid.UUID) -> dict:
    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 12:
        period_end = period_start.replace(year=now.year + 1, month=1)
    else:
        period_end = period_start.replace(month=now.month + 1)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    keys_result = await db.execute(select(APIKey).where(APIKey.user_id == user_id, APIKey.is_active.is_(True)))
    keys = keys_result.scalars().all()

    total_hits = sum(k.monthly_hit_count for k in keys)
    by_key = [{"key_prefix": k.key_prefix, "hits": k.monthly_hit_count} for k in keys]

    events_result = await db.execute(
        select(BillingEvent.hit_type, func.count(BillingEvent.id))
        .where(BillingEvent.user_id == user_id, BillingEvent.billed_at >= period_start)
        .group_by(BillingEvent.hit_type)
    )
    by_type = {row[0].value: row[1] for row in events_result.all()}

    plan_limit = get_plan_limit(user.plan) or 0
    overage = max(0, total_hits - plan_limit) if plan_limit else 0

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "total_hits": total_hits,
        "by_type": by_type,
        "by_key": by_key,
        "plan_limit": plan_limit if plan_limit else None,
        "overage_hits": overage,
    }
