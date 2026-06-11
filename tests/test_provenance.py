"""Tests for AI provenance detection (app/detection/image/provenance.py)."""

import io

import piexif
import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from app.detection.image import provenance
from app.detection.orchestrator import _compute_verdict


def _png_bytes(text_chunks: dict | None = None, size=(640, 480)) -> bytes:
    image = Image.new("RGB", size, (120, 130, 140))
    buf = io.BytesIO()
    pnginfo = None
    if text_chunks:
        pnginfo = PngInfo()
        for key, value in text_chunks.items():
            pnginfo.add_text(key, value)
    image.save(buf, format="PNG", pnginfo=pnginfo)
    return buf.getvalue()


def _jpeg_bytes(software: str | None = None, size=(640, 480)) -> bytes:
    image = Image.new("RGB", size, (120, 130, 140))
    buf = io.BytesIO()
    if software:
        exif_dict = {
            "0th": {piexif.ImageIFD.Software: software.encode()},
            "Exif": {},
            "GPS": {},
            "1st": {},
            "thumbnail": None,
        }
        image.save(buf, format="JPEG", exif=piexif.dump(exif_dict))
    else:
        image.save(buf, format="JPEG")
    return buf.getvalue()


class TestStableDiffusionPngChunks:
    def test_a1111_parameters_chunk_detected(self):
        file_bytes = _png_bytes(
            {"parameters": "a cat in space, masterpiece\nNegative prompt: blurry\nSteps: 20, Sampler: Euler a"}
        )
        result = provenance.analyse(file_bytes)
        assert result["flags"]["sd_generation_parameters"] is True
        assert result["provenance_score"] >= 0.9

    def test_comfyui_workflow_chunk_detected(self):
        file_bytes = _png_bytes({"workflow": '{"nodes": []}', "prompt": '{"3": {"class_type": "KSampler"}}'})
        result = provenance.analyse(file_bytes)
        assert result["flags"]["sd_generation_parameters"] is True
        assert result["provenance_score"] >= 0.9

    def test_novelai_software_chunk_detected(self):
        file_bytes = _png_bytes({"Software": "NovelAI", "Comment": '{"steps": 28}'})
        result = provenance.analyse(file_bytes)
        assert result["flags"]["ai_generator_metadata"] is True
        assert result["provenance_score"] >= 0.9


class TestExifGeneratorMarkers:
    def test_midjourney_in_exif_software(self):
        file_bytes = _jpeg_bytes(software="Midjourney v6")
        result = provenance.analyse(file_bytes)
        assert result["flags"]["ai_generator_metadata"] is True
        assert result["provenance_score"] >= 0.9

    def test_camera_software_not_flagged(self):
        file_bytes = _jpeg_bytes(software="iPhone 15 Pro iOS 17.2")
        result = provenance.analyse(file_bytes)
        assert result["flags"]["ai_generator_metadata"] is False


class TestRawMarkers:
    def test_algorithmic_media_xmp_marker(self):
        # Simulate an XMP packet declaring trainedAlgorithmicMedia, appended
        # the way XMP rides inside real files.
        base = _png_bytes()
        xmp = b'<xmp:DigitalSourceType>http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia</xmp:DigitalSourceType>'
        result = provenance.analyse(base + xmp)
        assert result["flags"]["algorithmic_media_declared"] is True
        assert result["provenance_score"] >= 0.9

    def test_c2pa_marker_alone_is_medium_signal(self):
        base = _jpeg_bytes()
        result = provenance.analyse(base + b"urn:c2pa:manifest")
        assert result["flags"]["c2pa_manifest_present"] is True
        assert result["flags"]["algorithmic_media_declared"] is False
        # C2PA alone is not proof of AI generation
        assert result["provenance_score"] < 0.5


class TestCleanImages:
    def test_clean_png_scores_zero(self):
        result = provenance.analyse(_png_bytes())
        assert result["provenance_score"] == 0.0
        assert result["provenance_flags"] == []

    def test_clean_jpeg_scores_zero(self):
        result = provenance.analyse(_jpeg_bytes())
        assert result["provenance_score"] == 0.0

    def test_garbage_bytes_do_not_crash(self):
        result = provenance.analyse(b"\x00\x01\x02 not an image")
        assert result["provenance_score"] == 0.0


class TestVerdictIntegration:
    def test_definitive_provenance_yields_ai_generated_verdict(self):
        scores = {
            "ela": 0.1,
            "clone_detection": 0.0,
            "metadata": 0.1,
            "ai_generated": 0.0,
            "synthetic": 0.2,
            "provenance": 0.95,
        }
        verdict, confidence, risk_score = _compute_verdict(scores, is_image=True)
        assert verdict == "ai_generated"
        assert confidence >= 0.9
        assert risk_score >= 90

    def test_c2pa_only_does_not_force_ai_verdict(self):
        scores = {
            "ela": 0.1,
            "clone_detection": 0.0,
            "metadata": 0.1,
            "ai_generated": 0.0,
            "synthetic": 0.0,
            "provenance": 0.30,
        }
        verdict, _, _ = _compute_verdict(scores, is_image=True)
        assert verdict in ("authentic", "inconclusive")
        assert verdict != "ai_generated"


@pytest.mark.asyncio
async def test_detect_image_pipeline_flags_sd_png():
    """End-to-end: a Stable Diffusion-style PNG goes through detect_image."""
    from app.detection.orchestrator import detect_image

    file_bytes = _png_bytes({"parameters": "portrait photo, Steps: 30, Sampler: DPM++ 2M"})
    result = await detect_image(file_bytes, ai_models=None)

    assert result["verdict"] == "ai_generated"
    assert result["scores"]["provenance"] >= 0.9
    flag_types = {f["type"] for f in result["flags"]}
    assert "provenance_sd_generation_parameters" in flag_types
