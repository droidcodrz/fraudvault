import io

import fitz


def open_pdf(file_bytes: bytes) -> fitz.Document:
    return fitz.open(stream=file_bytes, filetype="pdf")


def rasterize_page(doc: fitz.Document, page_num: int, dpi: int = 150) -> bytes:
    """Rasterize a PDF page to PNG bytes."""
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)
    return pix.tobytes("png")


def get_page_count(file_bytes: bytes) -> int:
    doc = open_pdf(file_bytes)
    count = len(doc)
    doc.close()
    return count


def get_metadata(file_bytes: bytes) -> dict:
    doc = open_pdf(file_bytes)
    meta = doc.metadata or {}
    xref_len = doc.xref_length()
    page_count = len(doc)
    doc.close()
    return {"metadata": meta, "xref_length": xref_len, "page_count": page_count}
