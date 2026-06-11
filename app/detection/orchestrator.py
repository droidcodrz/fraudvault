import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from app.config import get_settings
from app.detection.document import font_check, metadata_check, ocr_diff, page_ela
from app.detection.image import ai_detector, clone, ela, heatmap, metadata, provenance, synthetic

_executor = ThreadPoolExecutor(max_workers=4)

IMAGE_MIMES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
    "image/tiff",
}
PDF_MIME = "application/pdf"


class UnsupportedFileTypeError(Exception):
    def __init__(self, file_type: str):
        self.file_type = file_type
        super().__init__(f"Unsupported file type: {file_type}")


async def _run_in_executor(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, func, *args)


def _build_flags(*flag_lists) -> list[dict]:
    flags = []
    for flag_list in flag_lists:
        if flag_list:
            flags.extend(flag_list)
    return flags


def _get_thresholds() -> dict:
    settings = get_settings()
    return {
        "ai_generated": settings.ai_generated_threshold,
        "ai_inconclusive": settings.ai_inconclusive_threshold,
        "forensic_tampered": settings.forensic_tampered_threshold,
        "forensic_inconclusive": settings.forensic_inconclusive_threshold,
        "forensic_elevated": settings.forensic_elevated_threshold,
    }


def _compute_verdict(scores: dict, is_image: bool, thresholds: dict | None = None) -> tuple[str, float, int]:
    t = thresholds or _get_thresholds()

    ela = scores.get("ela", 0.0) or 0.0
    clone_s = scores.get("clone_detection", 0.0) or 0.0
    meta = scores.get("metadata", 0.0) or 0.0
    ai = scores.get("ai_generated", 0.0) or 0.0
    synth = scores.get("synthetic", 0.0) or 0.0
    prov = scores.get("provenance", 0.0) or 0.0
    font = scores.get("font_consistency", 0.0) or 0.0
    ocr = scores.get("ocr_diff", 0.0) or 0.0

    effective_ai = max(ai, synth, prov)

    forensic_scores = [ela, clone_s, meta]
    forensic_highest = max(forensic_scores)
    forensic_count_elevated = sum(1 for s in forensic_scores if s >= t["forensic_elevated"])

    if is_image and effective_ai >= t["ai_generated"]:
        verdict = "ai_generated"
    elif is_image and effective_ai >= t["ai_inconclusive"]:
        verdict = "inconclusive"
    elif any(s > t["forensic_tampered"] for s in forensic_scores):
        verdict = "tampered"
    elif any(s > t["forensic_tampered"] for s in [font, ocr]):
        verdict = "tampered"
    elif forensic_highest >= t["forensic_inconclusive"]:
        verdict = "inconclusive"
    elif forensic_count_elevated >= 2:
        verdict = "inconclusive"
    else:
        verdict = "authentic"

    confidence = (
        ela * 0.35
        + clone_s * 0.15
        + meta * 0.05
        + ai * 0.25
        + synth * 0.10
        + font * 0.05
        + ocr * 0.05
    )
    # Definitive provenance (generator named itself in metadata) overrides
    # the weighted blend — the file declares its own origin.
    if prov >= 0.9:
        confidence = max(confidence, prov)
    risk_score = int(confidence * 100)

    return verdict, confidence, risk_score


async def detect_image(file_bytes: bytes, ai_models=None) -> dict:
    start = time.perf_counter()

    ela_result, clone_result, meta_result, synth_result, prov_result = await asyncio.gather(
        _run_in_executor(ela.analyse, file_bytes),
        _run_in_executor(clone.analyse, file_bytes),
        _run_in_executor(metadata.analyse, file_bytes),
        _run_in_executor(synthetic.analyse, file_bytes),
        _run_in_executor(provenance.analyse, file_bytes),
    )

    ai_result = await _run_in_executor(ai_detector.analyse, file_bytes, ai_models)
    heatmap_bytes = await _run_in_executor(heatmap.generate, file_bytes, ela_result)

    ai_score = ai_result["ai_gen_score"]
    synth_score = synth_result["synthetic_score"]
    prov_score = prov_result["provenance_score"]
    effective_ai = max(ai_score, synth_score, prov_score)

    scores = {
        "ela": ela_result["ela_score"],
        "clone_detection": clone_result["clone_score"],
        "metadata": meta_result["metadata_score"],
        "ai_generated": ai_score,
        "synthetic": synth_score,
        "provenance": prov_score,
        "effective_ai": effective_ai,
        "model_used": ai_result.get("model_used"),
        "font_consistency": None,
        "ocr_diff": None,
    }

    ai_flags = []
    if effective_ai >= get_settings().ai_inconclusive_threshold:
        ai_flags.append(
            {
                "type": "possible_ai_generated",
                "severity": "high" if effective_ai >= get_settings().ai_generated_threshold else "medium",
                "details": f"effective_ai={effective_ai:.2f}",
            }
        )

    flags = _build_flags(
        [
            {
                "type": "ela_anomaly",
                "severity": "high" if ela_result["ela_score"] > 0.75 else "medium",
                "region": r,
            }
            for r in ela_result.get("anomaly_regions", [])[:5]
        ],
        meta_result.get("metadata_flags", []),
        synth_result.get("synthetic_flags", []),
        prov_result.get("provenance_flags", []),
        ai_flags,
        [{"type": "model_unavailable", "severity": "low"}] if ai_result.get("model_unavailable") else [],
    )

    verdict, confidence, risk_score = _compute_verdict(scores, is_image=True)
    processing_ms = int((time.perf_counter() - start) * 1000)

    return {
        "verdict": verdict,
        "confidence": confidence,
        "risk_score": risk_score,
        "flags": flags,
        "scores": scores,
        "heatmap_bytes": heatmap_bytes,
        "processing_ms": processing_ms,
        "raw_output": {
            "ela": {k: v for k, v in ela_result.items() if k != "ela_array"},
            "clone": clone_result,
            "metadata": meta_result,
            "synthetic": synth_result,
            "provenance": prov_result,
            "ai": ai_result,
        },
        "ela_score": ela_result["ela_score"],
        "clone_score": clone_result["clone_score"],
        "metadata_score": meta_result["metadata_score"],
        "ai_gen_score": ai_score,
        "synthetic_score": synth_score,
        "font_score": None,
        "ocr_diff_score": None,
    }


async def detect_document(file_bytes: bytes) -> dict:
    start = time.perf_counter()

    font_result, meta_result, ocr_result, ela_result = await asyncio.gather(
        _run_in_executor(font_check.analyse, file_bytes),
        _run_in_executor(metadata_check.analyse, file_bytes),
        _run_in_executor(ocr_diff.analyse, file_bytes),
        _run_in_executor(page_ela.analyse, file_bytes),
    )

    scores = {
        "ela": ela_result["ela_score"],
        "clone_detection": None,
        "metadata": meta_result["metadata_score"],
        "ai_generated": None,
        "synthetic": None,
        "effective_ai": None,
        "model_used": None,
        "font_consistency": font_result["font_score"],
        "ocr_diff": ocr_result["ocr_diff_score"],
    }

    flags = _build_flags(
        font_result.get("font_flags", []),
        meta_result.get("metadata_flags", []),
        ocr_result.get("ocr_flags", []),
        ela_result.get("ela_flags", []),
    )

    verdict, confidence, risk_score = _compute_verdict(scores, is_image=False)
    processing_ms = int((time.perf_counter() - start) * 1000)

    return {
        "verdict": verdict,
        "confidence": confidence,
        "risk_score": risk_score,
        "flags": flags,
        "scores": scores,
        "heatmap_bytes": None,
        "processing_ms": processing_ms,
        "raw_output": {
            "font": font_result,
            "metadata": meta_result,
            "ocr": ocr_result,
            "ela": ela_result,
        },
        "ela_score": ela_result["ela_score"],
        "clone_score": None,
        "metadata_score": meta_result["metadata_score"],
        "ai_gen_score": None,
        "synthetic_score": None,
        "font_score": font_result["font_score"],
        "ocr_diff_score": ocr_result["ocr_diff_score"],
    }


async def detect(file_bytes: bytes, file_type: str, file_name: str, ai_models=None) -> dict:
    if file_type in IMAGE_MIMES:
        result = await detect_image(file_bytes, ai_models)
        result["file_type"] = "image"
        return result
    elif file_type == PDF_MIME:
        result = await detect_document(file_bytes)
        result["file_type"] = "pdf"
        return result
    else:
        raise UnsupportedFileTypeError(file_type)
