"""AI provenance detection from embedded metadata — no ML required.

Most AI image generators leave identifiable traces in the file itself:
- Stable Diffusion WebUI (AUTOMATIC1111) writes the full prompt into a PNG
  tEXt chunk named "parameters"; ComfyUI writes "prompt"/"workflow" JSON.
- NovelAI sets the PNG "Software" text chunk.
- DALL-E 3 / ChatGPT, Adobe Firefly, and Leica cameras embed C2PA
  (Content Credentials) JUMBF manifests.
- IPTC-compliant tools mark XMP DigitalSourceType as
  "trainedAlgorithmicMedia" for AI-generated content.
- Some pipelines leave the generator name in EXIF Software / XMP CreatorTool.

A positive provenance hit is near-definitive (the generator told us itself),
so these flags carry much higher weight than statistical heuristics. Absence
of provenance proves nothing — metadata is trivially stripped.
"""

import io

import piexif
from PIL import Image

# Generator names that may appear in EXIF Software, XMP CreatorTool,
# or PNG text chunks. Lowercase substrings.
AI_GENERATOR_MARKERS = (
    "midjourney",
    "dall-e",
    "dall·e",
    "dalle",
    "stable diffusion",
    "stablediffusion",
    "stable-diffusion",
    "novelai",
    "comfyui",
    "automatic1111",
    "invokeai",
    "adobe firefly",
    "leonardo.ai",
    "ideogram",
    "recraft",
    "flux.1",
    "black forest labs",
    "bing image creator",
    "craiyon",
    "nightcafe",
    "playground ai",
    "starryai",
    "dreamstudio",
)

# PNG text-chunk keys written by generation UIs. Values are JSON or
# prompt text; the key alone is a strong signal.
SD_PNG_TEXT_KEYS = (
    "parameters",       # AUTOMATIC1111 WebUI
    "prompt",           # ComfyUI
    "workflow",         # ComfyUI
    "sd-metadata",      # InvokeAI (legacy)
    "invokeai_metadata",
    "generation_data",
    "dream",            # InvokeAI (legacy)
)

# IPTC digital source type values for synthetic media (appear in XMP).
ALGORITHMIC_MEDIA_MARKERS = (
    b"trainedalgorithmicmedia",
    b"compositewithtrainedalgorithmicmedia",
    b"algorithmicmedia",
)

# C2PA / Content Credentials manifest markers (JUMBF boxes).
C2PA_MARKERS = (b"c2pa", b"urn:c2pa", b"contentauth", b"jumdc2pa")

FLAG_WEIGHTS = {
    "ai_generator_metadata": 0.95,   # generator named itself in metadata
    "sd_generation_parameters": 0.95,  # prompt/workflow embedded in PNG
    "algorithmic_media_declared": 0.95,  # IPTC/XMP declares AI source
    "c2pa_manifest_present": 0.30,   # provenance manifest, origin unclear
}


def _check_png_text_chunks(image: Image.Image) -> tuple[bool, bool, list[str]]:
    """Returns (sd_params_found, generator_named, details)."""
    sd_params = False
    generator_named = False
    details: list[str] = []

    text_items: dict = {}
    text_items.update(getattr(image, "text", {}) or {})
    for key, value in (image.info or {}).items():
        if isinstance(value, str):
            text_items.setdefault(key, value)

    for key, value in text_items.items():
        key_l = str(key).lower()
        value_l = str(value).lower()
        if key_l in SD_PNG_TEXT_KEYS:
            sd_params = True
            details.append(f"png_chunk:{key_l}")
        for marker in AI_GENERATOR_MARKERS:
            if marker in value_l or marker in key_l:
                generator_named = True
                details.append(f"png_chunk_value:{key_l}={marker}")
                break

    return sd_params, generator_named, details


def _check_exif_software(file_bytes: bytes, image: Image.Image) -> tuple[bool, list[str]]:
    """Check EXIF Software / Make fields for generator names."""
    try:
        exif_bytes = image.info.get("exif")
        if not exif_bytes:
            return False, []
        exif_dict = piexif.load(exif_bytes)
        zeroth = exif_dict.get("0th", {})
        fields = []
        for tag in (piexif.ImageIFD.Software, piexif.ImageIFD.Make, piexif.ImageIFD.Model):
            raw = zeroth.get(tag, b"")
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="ignore")
            if raw:
                fields.append(str(raw).lower())
        for field in fields:
            for marker in AI_GENERATOR_MARKERS:
                if marker in field:
                    return True, [f"exif_software:{marker}"]
    except Exception:
        pass
    return False, []


def _check_raw_markers(file_bytes: bytes) -> tuple[bool, bool, list[str]]:
    """Scan raw bytes for XMP algorithmic-media declarations and C2PA boxes.

    XMP packets and JUMBF boxes can sit anywhere in the file, so a substring
    scan of the raw bytes is the simplest reliable check.
    """
    lowered = file_bytes.lower()
    details: list[str] = []

    algorithmic = False
    for marker in ALGORITHMIC_MEDIA_MARKERS:
        if marker in lowered:
            algorithmic = True
            details.append(f"xmp:{marker.decode()}")
            break

    c2pa = False
    for marker in C2PA_MARKERS:
        if marker in lowered:
            c2pa = True
            details.append(f"c2pa:{marker.decode()}")
            break

    return algorithmic, c2pa, details


def analyse(file_bytes: bytes) -> dict:
    """Detect AI-generation provenance embedded in image metadata."""
    flags = {
        "ai_generator_metadata": False,
        "sd_generation_parameters": False,
        "algorithmic_media_declared": False,
        "c2pa_manifest_present": False,
    }
    details: list[str] = []

    try:
        image = Image.open(io.BytesIO(file_bytes))

        sd_params, generator_named, png_details = _check_png_text_chunks(image)
        flags["sd_generation_parameters"] = sd_params
        details.extend(png_details)

        exif_hit, exif_details = _check_exif_software(file_bytes, image)
        if generator_named or exif_hit:
            flags["ai_generator_metadata"] = True
        details.extend(exif_details)
    except Exception:
        pass

    try:
        algorithmic, c2pa, raw_details = _check_raw_markers(file_bytes)
        flags["algorithmic_media_declared"] = algorithmic
        # A C2PA manifest alone is not proof of AI generation — cameras and
        # editors also embed Content Credentials to assert authenticity.
        # Only flag it as a standalone signal when nothing stronger fired.
        flags["c2pa_manifest_present"] = c2pa
        details.extend(raw_details)
    except Exception:
        pass

    triggered = [FLAG_WEIGHTS[k] for k, v in flags.items() if v]
    provenance_score = max(triggered) if triggered else 0.0

    return {
        "provenance_score": provenance_score,
        "flags": flags,
        "details": details,
        "provenance_flags": [
            {
                "type": f"provenance_{k}",
                "severity": "high" if FLAG_WEIGHTS.get(k, 0) >= 0.9 else "medium",
                "details": "; ".join(d for d in details if d) or str(v),
            }
            for k, v in flags.items()
            if v
        ],
    }
