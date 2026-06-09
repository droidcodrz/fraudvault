import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import AuthContext, get_auth_context
from app.exceptions import AppError
from app.models.detection_job import DetectionJob
from app.services import result_service

router = APIRouter(tags=["results"])


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
        .where(DetectionJob.id == job_id, DetectionJob.user_id == auth.user.id)
    )
    job = result.scalar_one_or_none()
    if not job:
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
