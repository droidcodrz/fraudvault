import asyncio
import uuid
from datetime import datetime, timezone

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import sync_session_factory
from app.detection.image.ai_detector import load_models
from app.detection.orchestrator import detect
from app.config import get_settings
from app.models.detection_job import DetectionJob, JobStatus
from app.models.detection_result import DetectionResult, Verdict
from app.services import storage_service
from app.workers.celery_app import celery_app

logger = structlog.get_logger()
settings = get_settings()

_ai_models = None


def _get_ai_models():
    global _ai_models
    if _ai_models is None:
        _ai_models = load_models(settings.model_cache_dir)
    return _ai_models


def _mime_for_file_type(file_type: str) -> str:
    mapping = {
        "image": "image/jpeg",
        "pdf": "application/pdf",
    }
    return mapping.get(file_type, "application/octet-stream")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def process_detection_job(self, job_id: str):
    """Process a detection job asynchronously."""
    session = sync_session_factory()
    try:
        job = session.execute(
            select(DetectionJob).where(DetectionJob.id == uuid.UUID(job_id))
        ).scalar_one_or_none()

        if not job:
            return {"error": "Job not found"}

        job.status = JobStatus.processing
        job.started_at = datetime.now(timezone.utc)
        session.commit()

        file_bytes = asyncio.run(storage_service.download_file(job.storage_key))
        mime = _mime_for_file_type(job.file_type.value)
        ai_models = _get_ai_models()
        detection_output = asyncio.run(detect(file_bytes, mime, job.file_name, ai_models))

        heatmap_key = None
        if detection_output.get("heatmap_bytes"):
            heatmap_key = storage_service.build_heatmap_key(job.id)
            asyncio.run(
                storage_service.upload_bytes(heatmap_key, detection_output["heatmap_bytes"], "image/png")
            )

        heatmap_url = None
        if heatmap_key:
            heatmap_url = asyncio.run(storage_service.get_presigned_url(heatmap_key))

        result = DetectionResult(
            job_id=job.id,
            overall_verdict=Verdict(detection_output["verdict"]),
            confidence=detection_output["confidence"],
            risk_score=detection_output["risk_score"],
            flags=detection_output.get("flags", []),
            ela_score=detection_output.get("ela_score"),
            clone_score=detection_output.get("clone_score"),
            metadata_score=detection_output.get("metadata_score"),
            ai_gen_score=detection_output.get("ai_gen_score"),
            font_score=detection_output.get("font_score"),
            ocr_diff_score=detection_output.get("ocr_diff_score"),
            heatmap_url=heatmap_url,
            raw_output=detection_output.get("raw_output", {}),
        )
        session.add(result)
        job.status = JobStatus.completed
        job.completed_at = datetime.now(timezone.utc)
        session.commit()

        logger.info(
            "detection_completed",
            job_id=job_id,
            user_id=str(job.user_id),
            file_type=job.file_type.value,
            duration_ms=detection_output.get("processing_ms"),
            verdict=detection_output["verdict"],
        )

        if job.webhook_url:
            response_payload = {
                "job_id": str(job.id),
                "status": "completed",
                "verdict": detection_output["verdict"],
                "confidence": detection_output["confidence"],
                "risk_score": detection_output["risk_score"],
                "flags": detection_output.get("flags", []),
                "scores": detection_output.get("scores", {}),
                "heatmap_url": heatmap_url,
                "file_name": job.file_name,
                "file_type": job.file_type.value,
            }
            try:
                httpx.post(job.webhook_url, json=response_payload, timeout=10)
            except Exception:
                pass

        return {"job_id": job_id, "status": "completed"}

    except Exception as exc:
        session.rollback()
        try:
            job = session.execute(
                select(DetectionJob).where(DetectionJob.id == uuid.UUID(job_id))
            ).scalar_one_or_none()
            if job:
                if self.request.retries >= self.max_retries:
                    job.status = JobStatus.failed
                    job.error_msg = str(exc)
                    job.completed_at = datetime.now(timezone.utc)
                    session.commit()
                else:
                    raise self.retry(exc=exc)
        except Exception:
            raise self.retry(exc=exc) from exc
        raise
    finally:
        session.close()
