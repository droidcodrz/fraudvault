import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import BillingEvent
from app.models.detection_job import DetectionJob, JobStatus
from app.models.organization import Organization
from app.models.user import User, UserPlan, UserRole


async def get_system_stats(db: AsyncSession) -> dict:
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (await db.execute(
        select(func.count(User.id)).where(User.is_active.is_(True))
    )).scalar() or 0

    total_orgs = (await db.execute(select(func.count(Organization.id)))).scalar() or 0

    total_jobs = (await db.execute(select(func.count(DetectionJob.id)))).scalar() or 0
    completed_jobs = (await db.execute(
        select(func.count(DetectionJob.id)).where(DetectionJob.status == JobStatus.completed)
    )).scalar() or 0
    failed_jobs = (await db.execute(
        select(func.count(DetectionJob.id)).where(DetectionJob.status == JobStatus.failed)
    )).scalar() or 0

    now = datetime.now(timezone.utc)
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_events = (await db.execute(
        select(func.count(BillingEvent.id)).where(BillingEvent.billed_at >= period_start)
    )).scalar() or 0

    plan_counts_q = await db.execute(
        select(User.plan, func.count(User.id)).group_by(User.plan)
    )
    plan_distribution = {row[0].value: row[1] for row in plan_counts_q.all()}

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_organizations": total_orgs,
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "monthly_billing_events": monthly_events,
        "plan_distribution": plan_distribution,
    }


async def list_users(
    db: AsyncSession, page: int = 1, per_page: int = 20, search: str | None = None
) -> dict:
    offset = (page - 1) * per_page
    q = select(User)
    count_q = select(func.count()).select_from(User)

    if search:
        pattern = f"%{search}%"
        q = q.where(User.email.ilike(pattern) | User.full_name.ilike(pattern))
        count_q = count_q.where(User.email.ilike(pattern) | User.full_name.ilike(pattern))

    total = (await db.execute(count_q)).scalar() or 0
    users = (await db.execute(
        q.order_by(User.created_at.desc()).offset(offset).limit(per_page)
    )).scalars().all()

    return {
        "items": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "plan": u.plan.value,
                "role": u.role.value,
                "is_active": u.is_active,
                "email_verified": u.email_verified,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
    }


async def update_user_plan(db: AsyncSession, user_id: uuid.UUID, plan: str) -> bool:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False
    user.plan = UserPlan(plan)
    await db.flush()
    return True


async def toggle_user_active(db: AsyncSession, user_id: uuid.UUID) -> bool:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return False
    user.is_active = not user.is_active
    await db.flush()
    return user.is_active
