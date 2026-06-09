import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.detection_job import DetectionJob, FileType, JobStatus
from app.models.detection_result import DetectionResult, Verdict
from app.services import storage_service


async def save_detection_result(
    db: AsyncSession,
    job: DetectionJob,
    detection_output: dict,
    heatmap_storage_key: str | None = None,
) -> DetectionResult:
    heatmap_url = None
    if heatmap_storage_key:
        heatmap_url = await storage_service.get_presigned_url(heatmap_storage_key)

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
    db.add(result)
    job.status = JobStatus.completed
    await db.flush()
    return result


def build_detect_response(job: DetectionJob, result: DetectionResult | None, detection_output: dict | None = None) -> dict:
    if detection_output:
        return {
            "job_id": str(job.id),
            "status": "completed",
            "verdict": detection_output["verdict"],
            "confidence": detection_output["confidence"],
            "risk_score": detection_output["risk_score"],
            "flags": detection_output.get("flags", []),
            "scores": detection_output.get("scores", {}),
            "heatmap_url": detection_output.get("heatmap_url"),
            "processing_ms": detection_output.get("processing_ms"),
            "file_name": job.file_name,
            "file_type": job.file_type.value,
        }

    if not result:
        return {
            "job_id": str(job.id),
            "status": job.status.value,
            "file_name": job.file_name,
            "file_type": job.file_type.value,
        }

    raw = result.raw_output or {}
    synthetic_score = raw.get("synthetic", {}).get("synthetic_score")
    ai_raw = raw.get("ai", {})
    effective_ai = None
    if result.ai_gen_score is not None or synthetic_score is not None:
        effective_ai = max(result.ai_gen_score or 0.0, synthetic_score or 0.0)

    return {
        "job_id": str(job.id),
        "status": job.status.value,
        "verdict": result.overall_verdict.value,
        "confidence": result.confidence,
        "risk_score": result.risk_score,
        "flags": result.flags,
        "scores": {
            "ela": result.ela_score,
            "clone_detection": result.clone_score,
            "metadata": result.metadata_score,
            "ai_generated": result.ai_gen_score,
            "synthetic": synthetic_score,
            "effective_ai": effective_ai if effective_ai else None,
            "model_used": ai_raw.get("model_used"),
            "font_consistency": result.font_score,
            "ocr_diff": result.ocr_diff_score,
        },
        "heatmap_url": result.heatmap_url,
        "processing_ms": None,
        "file_name": job.file_name,
        "file_type": job.file_type.value,
    }
