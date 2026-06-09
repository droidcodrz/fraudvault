import fitz

from app.detection.document.pdf_parser import get_metadata, open_pdf

SUSPICIOUS_PRODUCERS = ("ilovepdf", "smallpdf", "pdf24", "online2pdf", "sejda")
FLAG_WEIGHTS = {
    "suspicious_producer": 0.6,
    "created_after_modified": 0.2,
    "no_producer": 0.2,
    "author_mismatch": 0.2,
    "javascript_present": 0.2,
    "page_count_mismatch": 0.2,
}


def _parse_pdf_date(date_str: str) -> str | None:
    if not date_str:
        return None
    return date_str.strip("D:")


def analyse(file_bytes: bytes) -> dict:
    """PDF metadata anomaly detection using PyMuPDF."""
    flags = {
        "created_after_modified": False,
        "suspicious_producer": False,
        "no_producer": False,
        "author_mismatch": False,
        "javascript_present": False,
        "page_count_mismatch": False,
    }

    meta_info = get_metadata(file_bytes)
    meta = meta_info["metadata"]

    creation = _parse_pdf_date(meta.get("creationDate", ""))
    modified = _parse_pdf_date(meta.get("modDate", ""))
    if creation and modified and creation > modified:
        flags["created_after_modified"] = True

    producer = (meta.get("producer") or "").lower()
    if not producer:
        flags["no_producer"] = True
    elif any(s in producer for s in SUSPICIOUS_PRODUCERS):
        flags["suspicious_producer"] = True

    title = (meta.get("title") or "").lower()
    author = (meta.get("author") or "").lower()
    if title and author and len(title) > 3 and author not in title and title not in author:
        if " " in author and " " in title:
            flags["author_mismatch"] = True

    doc = open_pdf(file_bytes)
    for page in doc:
        for annot in page.annots() or []:
            if annot.type[0] == fitz.PDF_ANNOT_TEXT and "javascript" in str(annot.info).lower():
                flags["javascript_present"] = True
                break
    doc.close()

    if meta_info["xref_length"] < meta_info["page_count"] * 2:
        flags["page_count_mismatch"] = True

    metadata_score = sum(FLAG_WEIGHTS.get(k, 0.2) for k, v in flags.items() if v)
    metadata_score = min(1.0, metadata_score)

    return {
        "metadata_score": metadata_score,
        "flags": flags,
        "metadata_flags": [
            {"type": k, "severity": "high" if k == "suspicious_producer" else "medium", "details": str(v)}
            for k, v in flags.items()
            if v
        ],
    }
