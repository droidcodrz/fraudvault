import io
import re

import pdfplumber


def _normalize_font(fontname: str) -> str:
    if not fontname:
        return "unknown"
    return re.sub(r"^[A-Z]{6}\+", "", fontname).split("-")[0].strip()


def analyse(file_bytes: bytes) -> dict:
    """Font inconsistency analysis using pdfplumber."""
    fonts_by_page: list[set[str]] = []
    all_fonts: set[str] = set()
    suspicious_regions: list[dict] = []

    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_fonts: set[str] = set()
            chars = page.chars or []
            font_sizes: dict[str, set[float]] = {}

            for char in chars:
                font = _normalize_font(char.get("fontname", ""))
                size = round(char.get("size", 0), 1)
                page_fonts.add(font)
                all_fonts.add(font)
                font_sizes.setdefault(font, set()).add(size)

            fonts_by_page.append(page_fonts)

            if len(page_fonts) > 2:
                suspicious_regions.append(
                    {
                        "page": page_num + 1,
                        "fonts": list(page_fonts),
                        "details": f"{len(page_fonts)} font families on page {page_num + 1}",
                    }
                )

    family_count = len(all_fonts)
    if family_count <= 1:
        font_score = 0.0
    elif family_count == 2:
        font_score = 0.2
    elif family_count == 3:
        font_score = 0.5
    else:
        font_score = 0.85

    return {
        "font_score": font_score,
        "font_list": sorted(all_fonts),
        "suspicious_regions": suspicious_regions,
        "font_flags": [
            {
                "type": "mixed_fonts",
                "severity": "medium" if family_count >= 3 else "low",
                "details": f"{family_count} different font families detected",
            }
        ]
        if family_count >= 3
        else [],
    }
