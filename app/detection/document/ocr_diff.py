import difflib
import io
import re

import pdfplumber
import pytesseract
from PIL import Image

from app.detection.document.pdf_parser import open_pdf, rasterize_page


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def analyse(file_bytes: bytes) -> dict:
    """Compare embedded PDF text against OCR-extracted text."""
    embedded_parts: list[str] = []
    changed_tokens: list[dict] = []

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                embedded_parts.append(text)
    except Exception:
        embedded_parts = [""]

    embedded_text = " ".join(embedded_parts)
    embedded_tokens = _tokenize(embedded_text)

    ocr_parts: list[str] = []
    try:
        doc = open_pdf(file_bytes)
        for page_num in range(len(doc)):
            png_bytes = rasterize_page(doc, page_num, dpi=150)
            image = Image.open(io.BytesIO(png_bytes))
            ocr_text = pytesseract.image_to_string(image)
            ocr_parts.append(ocr_text)
        doc.close()
    except Exception:
        return {
            "ocr_diff_score": 0.0,
            "changed_tokens": [],
            "ocr_unavailable": True,
            "ocr_flags": [{"type": "ocr_unavailable", "severity": "low", "details": "Tesseract not available"}],
        }

    ocr_text = " ".join(ocr_parts)
    ocr_tokens = _tokenize(ocr_text)

    matcher = difflib.SequenceMatcher(None, embedded_tokens, ocr_tokens)
    mismatched = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag in ("replace", "delete"):
            for idx in range(i1, i2):
                if idx < len(embedded_tokens):
                    orig = embedded_tokens[idx]
                    detected = ocr_tokens[j1] if j1 < len(ocr_tokens) else ""
                    ratio = matcher.ratio()
                    if ratio < 0.8 or orig != detected:
                        mismatched.append({"original": orig, "detected": detected, "page": 1})
                        changed_tokens.append(
                            {"original": orig, "detected": detected, "page": 1, "bbox": None}
                        )

    ocr_diff_score = min(1.0, len(mismatched) / max(len(embedded_tokens), 1))

    return {
        "ocr_diff_score": ocr_diff_score,
        "changed_tokens": changed_tokens,
        "ocr_unavailable": False,
        "ocr_flags": [
            {
                "type": "text_mismatch",
                "severity": "high" if ocr_diff_score > 0.5 else "medium",
                "details": f"{len(changed_tokens)} token mismatches detected",
            }
        ]
        if changed_tokens
        else [],
    }
