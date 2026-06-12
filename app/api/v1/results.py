import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import AuthContext, get_auth_context
from app.exceptions import AppError
from app.models.detection_job import DetectionJob
from app.services import result_service

router = APIRouter(tags=["results"])


@router.get("/results")
async def list_results(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """List all detection jobs for the current user."""
    offset = (page - 1) * per_page

    if auth.user.current_org_id:
        scope_filter = DetectionJob.org_id == auth.user.current_org_id
    else:
        scope_filter = DetectionJob.user_id == auth.user.id

    count_q = select(func.count()).select_from(DetectionJob).where(scope_filter)
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        select(DetectionJob)
        .options(selectinload(DetectionJob.result))
        .where(scope_filter)
        .order_by(DetectionJob.queued_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    rows = (await db.execute(q)).scalars().all()

    items = []
    for job in rows:
        item = {
            "job_id": str(job.id),
            "file_name": job.file_name,
            "file_type": job.file_type.value,
            "file_size": job.file_size,
            "status": job.status.value,
            "queued_at": job.queued_at.isoformat() if job.queued_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
        if job.result:
            item["verdict"] = job.result.overall_verdict.value
            item["confidence"] = job.result.confidence
            item["risk_score"] = job.result.risk_score
        items.append(item)

    return {"items": items, "total": total, "page": page, "per_page": per_page}


@router.get("/results/{job_id}")
async def get_result(
    job_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    """Poll for async detection job result."""
    result = await db.execute(
        select(DetectionJob)
        .options(selectinload(DetectionJob.result))
        .where(DetectionJob.id == job_id)
    )
    job = result.scalar_one_or_none()
    if not job:
        raise AppError("NOT_FOUND", "Job not found", 404)

    is_owner = job.user_id == auth.user.id
    is_org_member = auth.user.current_org_id and job.org_id == auth.user.current_org_id
    if not is_owner and not is_org_member:
        raise AppError("NOT_FOUND", "Job not found", 404)

    if job.status.value == "failed":
        return {
            "job_id": str(job.id),
            "status": "failed",
            "error": job.error_msg,
            "file_name": job.file_name,
            "file_type": job.file_type.value,
        }

    return result_service.build_detect_response(job, job.result)
