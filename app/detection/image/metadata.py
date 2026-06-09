import hashlib
import io

import piexif
from PIL import Image

EDIT_SOFTWARE = ("photoshop", "gimp", "canva", "snapseed")
BENIGN_SOFTWARE = (
    "iphone",
    "ios",
    "android",
    "google",
    "samsung",
    "huawei",
    "xiaomi",
    "oneplus",
    "camera",
    "apple",
)

FLAG_WEIGHTS = {
    "datetime_mismatch": 0.35,
    "no_exif": 0.20,
    "software_edit": 0.25,
    "thumbnail_mismatch": 0.10,
    "gps_stripped": 0.05,
    "make_model_missing": 0.05,
}


def _get_exif_dict(file_bytes: bytes) -> dict | None:
    try:
        image = Image.open(io.BytesIO(file_bytes))
        if image.format != "JPEG":
            return None
        exif_data = image._getexif()
        if not exif_data:
            return None
        return piexif.load(image.info.get("exif", b"")) if image.info.get("exif") else None
    except Exception:
        return None


def _thumbnail_mismatch(file_bytes: bytes, exif_dict: dict | None) -> bool:
    if not exif_dict or "thumbnail" not in exif_dict:
        return False
    try:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        thumb = exif_dict.get("thumbnail")
        if not thumb:
            return False
        thumb_img = Image.open(io.BytesIO(thumb)).convert("RGB")
        downscaled = image.copy()
        downscaled.thumbnail(thumb_img.size)
        thumb_hash = hashlib.md5(thumb_img.tobytes()).hexdigest()
        down_hash = hashlib.md5(downscaled.tobytes()).hexdigest()
        return thumb_hash != down_hash
    except Exception:
        return False


def _is_suspicious_software(software: str) -> bool:
    software_lower = software.lower()
    if any(benign in software_lower for benign in BENIGN_SOFTWARE):
        return False
    return any(editor in software_lower for editor in EDIT_SOFTWARE)


def _gps_was_stripped(exif_dict: dict) -> bool:
    """Flag only when GPS IFD exists but contains no coordinates (stripped)."""
    gps = exif_dict.get("GPS")
    if gps is None:
        return False
    if not gps:
        return True
    coord_tags = (
        piexif.GPSIFD.GPSLatitude,
        piexif.GPSIFD.GPSLongitude,
        piexif.GPSIFD.GPSLatitudeRef,
        piexif.GPSIFD.GPSLongitudeRef,
    )
    return not any(gps.get(tag) for tag in coord_tags)


def _compute_metadata_score(flags: dict) -> float:
    score = sum(FLAG_WEIGHTS.get(k, 0.1) for k, v in flags.items() if v)
    return min(1.0, score)


def analyse(file_bytes: bytes) -> dict:
    """EXIF metadata anomaly detection with weighted scoring."""
    flags = {
        "no_exif": False,
        "gps_stripped": False,
        "software_edit": False,
        "datetime_mismatch": False,
        "make_model_missing": False,
        "thumbnail_mismatch": False,
    }

    try:
        image = Image.open(io.BytesIO(file_bytes))
        is_jpeg = image.format == "JPEG"
        exif_dict = _get_exif_dict(file_bytes)

        if is_jpeg and not exif_dict:
            flags["no_exif"] = True
        elif exif_dict:
            flags["gps_stripped"] = _gps_was_stripped(exif_dict)

            zeroth = exif_dict.get("0th", {})
            software = zeroth.get(piexif.ImageIFD.Software, b"")
            if isinstance(software, bytes):
                software = software.decode("utf-8", errors="ignore")
            if software and _is_suspicious_software(str(software)):
                flags["software_edit"] = True

            exif_ifd = exif_dict.get("Exif", {})
            dt_orig = exif_ifd.get(piexif.ExifIFD.DateTimeOriginal, b"")
            dt = zeroth.get(piexif.ImageIFD.DateTime, b"")
            if dt_orig and dt and dt_orig != dt:
                flags["datetime_mismatch"] = True

            make = zeroth.get(piexif.ImageIFD.Make, b"")
            model = zeroth.get(piexif.ImageIFD.Model, b"")
            if not make and not model:
                flags["make_model_missing"] = True

            flags["thumbnail_mismatch"] = _thumbnail_mismatch(file_bytes, exif_dict)
    except Exception:
        flags["no_exif"] = True

    metadata_score = _compute_metadata_score(flags)

    return {
        "metadata_score": metadata_score,
        "flags": flags,
        "metadata_flags": [
            {
                "type": k,
                "severity": "high" if FLAG_WEIGHTS.get(k, 0) >= 0.25 else "medium",
                "details": str(v),
            }
            for k, v in flags.items()
            if v
        ],
    }
