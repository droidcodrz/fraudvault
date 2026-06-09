import pytest

from app.detection.image import ela
from app.detection.image.metadata import FLAG_WEIGHTS, _compute_metadata_score, _is_suspicious_software
from app.detection.orchestrator import _compute_verdict


def test_ela_returns_score(clean_jpeg_bytes):
    result = ela.analyse(clean_jpeg_bytes)
    assert "ela_score" in result
    assert 0.0 <= result["ela_score"] <= 1.0
    assert "anomaly_regions" in result


def test_ela_tampered_higher_than_clean(clean_jpeg_bytes, tampered_jpeg_bytes):
    clean = ela.analyse(clean_jpeg_bytes)
    tampered = ela.analyse(tampered_jpeg_bytes)
    assert tampered["ela_score"] >= clean["ela_score"]


def test_verdict_authentic():
    scores = {
        "ela": 0.1,
        "clone_detection": 0.05,
        "metadata": 0.1,
        "ai_generated": 0.05,
        "font_consistency": 0.0,
        "ocr_diff": 0.0,
    }
    verdict, confidence, risk = _compute_verdict(scores, is_image=True)
    assert verdict == "authentic"
    assert risk < 45


def test_verdict_tampered():
    scores = {
        "ela": 0.9,
        "clone_detection": 0.1,
        "metadata": 0.2,
        "ai_generated": 0.1,
        "font_consistency": 0.0,
        "ocr_diff": 0.0,
    }
    verdict, _, _ = _compute_verdict(scores, is_image=True)
    assert verdict == "tampered"


def test_verdict_ai_generated():
    scores = {
        "ela": 0.3,
        "clone_detection": 0.1,
        "metadata": 0.2,
        "ai_generated": 0.9,
        "font_consistency": 0.0,
        "ocr_diff": 0.0,
    }
    verdict, _, _ = _compute_verdict(scores, is_image=True)
    assert verdict == "ai_generated"


def test_verdict_ai_above_threshold():
    """Aggressive mode: AI score >= 0.40 triggers ai_generated."""
    scores = {
        "ela": 0.26,
        "clone_detection": 0.0,
        "metadata": 0.20,
        "ai_generated": 0.55,
        "synthetic": 0.0,
        "font_consistency": 0.0,
        "ocr_diff": 0.0,
    }
    verdict, _, _ = _compute_verdict(scores, is_image=True)
    assert verdict == "ai_generated"


def test_verdict_synthetic_boost_ai_generated():
    """Synthetic heuristics can push effective_ai over the threshold."""
    scores = {
        "ela": 0.10,
        "clone_detection": 0.0,
        "metadata": 0.10,
        "ai_generated": 0.20,
        "synthetic": 0.45,
        "font_consistency": 0.0,
        "ocr_diff": 0.0,
    }
    verdict, _, _ = _compute_verdict(scores, is_image=True)
    assert verdict == "ai_generated"


def test_verdict_ai_borderline_inconclusive():
    """Borderline effective_ai (0.30-0.39) returns inconclusive."""
    scores = {
        "ela": 0.10,
        "clone_detection": 0.0,
        "metadata": 0.10,
        "ai_generated": 0.15,
        "synthetic": 0.35,
        "font_consistency": 0.0,
        "ocr_diff": 0.0,
    }
    verdict, _, _ = _compute_verdict(scores, is_image=True)
    assert verdict == "inconclusive"


def test_verdict_aadhar_like_may_flag_ai():
    """Phone ID photos with moderate AI scores may be flagged in aggressive mode."""
    scores = {
        "ela": 0.26,
        "clone_detection": 0.0,
        "metadata": 0.20,
        "ai_generated": 0.55,
        "synthetic": 0.0,
        "font_consistency": 0.0,
        "ocr_diff": 0.0,
    }
    verdict, confidence, risk = _compute_verdict(scores, is_image=True)
    assert verdict == "ai_generated"
    assert risk > 10


def test_verdict_two_moderate_forensic_signals_inconclusive():
    scores = {
        "ela": 0.50,
        "clone_detection": 0.0,
        "metadata": 0.48,
        "ai_generated": 0.1,
        "font_consistency": 0.0,
        "ocr_diff": 0.0,
    }
    verdict, _, _ = _compute_verdict(scores, is_image=True)
    assert verdict == "inconclusive"


def test_metadata_weighted_scoring_phone_flags():
    flags = {
        "no_exif": False,
        "gps_stripped": True,
        "software_edit": False,
        "datetime_mismatch": False,
        "make_model_missing": True,
        "thumbnail_mismatch": True,
    }
    score = _compute_metadata_score(flags)
    expected = FLAG_WEIGHTS["gps_stripped"] + FLAG_WEIGHTS["make_model_missing"] + FLAG_WEIGHTS["thumbnail_mismatch"]
    assert score == expected
    assert score < 0.45


def test_metadata_weighted_scoring_old_equal_weight_would_fail():
    flags = {
        "no_exif": False,
        "gps_stripped": True,
        "software_edit": True,
        "datetime_mismatch": False,
        "make_model_missing": True,
        "thumbnail_mismatch": True,
    }
    score = _compute_metadata_score(flags)
    old_equal_weight = 4 / 6
    assert score < old_equal_weight


def test_metadata_datetime_mismatch_elevated():
    flags = {
        "no_exif": False,
        "gps_stripped": False,
        "software_edit": False,
        "datetime_mismatch": True,
        "make_model_missing": False,
        "thumbnail_mismatch": False,
    }
    score = _compute_metadata_score(flags)
    assert score == FLAG_WEIGHTS["datetime_mismatch"]
    assert score < 0.55


def test_software_allowlist_ignores_phone_camera():
    assert _is_suspicious_software("iPhone 15 Pro") is False
    assert _is_suspicious_software("Google Camera") is False
    assert _is_suspicious_software("Adobe Photoshop CC") is True
