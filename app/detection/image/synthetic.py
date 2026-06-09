import io

import numpy as np
import piexif
from PIL import Image

AI_COMMON_DIMENSIONS = {512, 768, 1024, 1280, 1536, 1792, 2048}

FLAG_WEIGHTS = {
    "png_or_webp_no_exif": 0.25,
    "perfect_dimensions": 0.15,
    "no_camera_metadata": 0.20,
    "uniform_noise": 0.15,
}


def _has_exif(file_bytes: bytes) -> bool:
    try:
        image = Image.open(io.BytesIO(file_bytes))
        if image.format not in ("JPEG", "TIFF"):
            return False
        return bool(image.info.get("exif") or image._getexif())
    except Exception:
        return False


def _no_camera_metadata(file_bytes: bytes) -> bool:
    try:
        image = Image.open(io.BytesIO(file_bytes))
        if image.format != "JPEG":
            return False
        exif_bytes = image.info.get("exif")
        if not exif_bytes:
            return True
        exif_dict = piexif.load(exif_bytes)
        zeroth = exif_dict.get("0th", {})
        exif_ifd = exif_dict.get("Exif", {})
        make = zeroth.get(piexif.ImageIFD.Make, b"")
        model = zeroth.get(piexif.ImageIFD.Model, b"")
        dt_orig = exif_ifd.get(piexif.ExifIFD.DateTimeOriginal, b"")
        return not make and not model and not dt_orig
    except Exception:
        return False


def _perfect_ai_dimensions(file_bytes: bytes) -> bool:
    try:
        image = Image.open(io.BytesIO(file_bytes))
        w, h = image.size
        return w in AI_COMMON_DIMENSIONS or h in AI_COMMON_DIMENSIONS
    except Exception:
        return False


def _uniform_noise_score(file_bytes: bytes) -> bool:
    """AI images tend to have unusually low high-frequency noise."""
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("L")
        arr = np.array(image, dtype=np.float32)
        if arr.size < 1000:
            return False
        laplacian = (
            -4 * arr[1:-1, 1:-1]
            + arr[:-2, 1:-1]
            + arr[2:, 1:-1]
            + arr[1:-1, :-2]
            + arr[1:-1, 2:]
        )
        variance = float(np.var(laplacian))
        return variance < 80.0
    except Exception:
        return False


def analyse(file_bytes: bytes) -> dict:
    """Heuristic detection of synthetic/AI-generated image patterns."""
    flags = {
        "png_or_webp_no_exif": False,
        "perfect_dimensions": False,
        "no_camera_metadata": False,
        "uniform_noise": False,
    }

    try:
        image = Image.open(io.BytesIO(file_bytes))
        fmt = (image.format or "").upper()

        if fmt in ("PNG", "WEBP") and not _has_exif(file_bytes):
            flags["png_or_webp_no_exif"] = True

        if _perfect_ai_dimensions(file_bytes):
            flags["perfect_dimensions"] = True

        if _no_camera_metadata(file_bytes):
            flags["no_camera_metadata"] = True

        if _uniform_noise_score(file_bytes):
            flags["uniform_noise"] = True
    except Exception:
        pass

    synthetic_score = min(1.0, sum(FLAG_WEIGHTS[k] for k, v in flags.items() if v))

    return {
        "synthetic_score": synthetic_score,
        "flags": flags,
        "synthetic_flags": [
            {
                "type": f"synthetic_{k}",
                "severity": "high" if FLAG_WEIGHTS.get(k, 0) >= 0.20 else "medium",
                "details": str(v),
            }
            for k, v in flags.items()
            if v
        ],
    }
