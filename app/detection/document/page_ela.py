import io

from PIL import Image

from app.detection.document.pdf_parser import open_pdf, rasterize_page
from app.detection.image import ela


def analyse(file_bytes: bytes) -> dict:
    """Run ELA on rasterized PDF pages."""
    doc = open_pdf(file_bytes)
    max_score = 0.0
    max_page = 0
    all_regions: list = []

    for page_num in range(len(doc)):
        png_bytes = rasterize_page(doc, page_num, dpi=150)
        result = ela.analyse(png_bytes)
        score = result["ela_score"]
        if score > max_score:
            max_score = score
            max_page = page_num + 1
            all_regions = result.get("anomaly_regions", [])

    doc.close()

    return {
        "ela_score": max_score,
        "most_suspicious_page": max_page,
        "anomaly_regions": all_regions,
        "ela_flags": [
            {
                "type": "ela_anomaly",
                "severity": "high" if max_score > 0.75 else "medium",
                "region": all_regions[0] if all_regions else None,
                "details": f"Highest ELA score on page {max_page}",
            }
        ]
        if max_score > 0.45
        else [],
    }
