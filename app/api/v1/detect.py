import uuid

import structlog
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import AuthContext, get_auth_context
from app.detection.orchestrator import UnsupportedFileTypeError, detect
from app.exceptions import AppError
from app.models.billing import HitType
from app.models.detection_job import DetectionJob, FileType, JobStatus
from app.services import billing_service, result_service, storage_service

router = APIRouter(tags=["detect"])
logger = structlog.get_logger()

ALLOWED_TYPES = {
    "image/jpeg": (FileType.image, 20 * 1024 * 1024),
    "image/png": (FileType.image, 20 * 1024 * 1024),
    "image/webp": (FileType.image, 20 * 1024 * 1024),
    "image/heic": (FileType.image, 20 * 1024 * 1024),
    "image/heif": (FileType.image, 20 * 1024 * 1024),
    "image/tiff": (FileType.image, 20 * 1024 * 1024),
    "application/pdf": (FileType.pdf, 50 * 1024 * 1024),
}

HIT_TYPE_MAP = {
    FileType.image: HitType.image_detect,
    FileType.pdf: HitType.pdf_detect,
    FileType.video: HitType.video_detect,
}


@router.post("/detect")
async def detect_file(
    request: Request,
    file: UploadFile = File(...),
    async_mode: bool = Form(True),
    webhook_url: str | None = Form(None),
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file for forgery detection."""
    content_type = file.content_type or ""
    if content_type not in ALLOWED_TYPES:
        raise AppError(
            "INVALID_FILE_TYPE",
            f"Unsupported file type: {content_type}. Accepted: jpg, png, webp, pdf, heic, tiff",
            400,
        )

    file_type, max_size = ALLOWED_TYPES[content_type]
    content = await file.read()
    if len(content) > max_size:
        raise AppError("FILE_TOO_LARGE", f"File exceeds maximum size of {max_size // (1024*1024)}MB", 400)

    if not await billing_service.check_quota(db, auth.user):
        raise AppError("QUOTA_EXCEEDED", "Monthly quota exceeded for your plan", 402)

    job_id = uuid.uuid4()
    storage_key = storage_service.build_upload_key(auth.user.id, job_id, file.filename or "upload")
    await storage_service.upload_bytes(storage_key, content, content_type)

    job = DetectionJob(
        id=job_id,
        user_id=auth.user.id,
        api_key_id=auth.api_key.id if auth.api_key else None,
        file_name=file.filename or "upload",
        file_type=file_type,
        file_size=len(content),
        storage_key=storage_key,
        status=JobStatus.queued,
        webhook_url=webhook_url,
    )
    db.add(job)
    await db.flush()

    hit_type = HIT_TYPE_MAP[file_type]
    if auth.api_key:
        await billing_service.record_hit(db, auth.user.id, auth.api_key.id, job.id, hit_type)

    if async_mode:
        from app.workers.detection_worker import process_detection_job

        process_detection_job.delay(str(job.id))
        return JSONResponse(
            status_code=202,
            content={
                "job_id": str(job.id),
                "status": "queued",
                "poll_url": f"/v1/results/{job.id}",
            },
        )

    ai_models = getattr(request.app.state, "ai_models", None) or getattr(request.app.state, "ai_model", None)
    try:
        detection_output = await detect(content, content_type, file.filename or "upload", ai_models)
    except UnsupportedFileTypeError as e:
        raise AppError("INVALID_FILE_TYPE", str(e), 400) from e

    heatmap_key = None
    if detection_output.get("heatmap_bytes"):
        heatmap_key = storage_service.build_heatmap_key(job.id)
        await storage_service.upload_bytes(heatmap_key, detection_output["heatmap_bytes"], "image/png")
        detection_output["heatmap_url"] = await storage_service.get_presigned_url(heatmap_key)

    result = await result_service.save_detection_result(db, job, detection_output, heatmap_key)

    logger.info(
        "detection_completed",
        job_id=str(job.id),
        user_id=str(auth.user.id),
        file_type=file_type.value,
        duration_ms=detection_output.get("processing_ms"),
        verdict=detection_output["verdict"],
    )

    return result_service.build_detect_response(job, result, detection_output)
