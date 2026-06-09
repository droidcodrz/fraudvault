import io

import cv2
import numpy as np
from PIL import Image


def analyse(file_bytes: bytes) -> dict:
    """Error Level Analysis — detect regions with different compression levels."""
    original = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    buffer = io.BytesIO()
    original.save(buffer, format="JPEG", quality=90)
    buffer.seek(0)
    resaved = Image.open(buffer).convert("RGB")

    orig_arr = np.array(original, dtype=np.float32)
    resaved_arr = np.array(resaved, dtype=np.float32)
    diff = np.abs(orig_arr - resaved_arr)
    ela_array = np.clip(diff * 15, 0, 255).astype(np.uint8)
    gray = cv2.cvtColor(ela_array, cv2.COLOR_RGB2GRAY)

    flat = gray.flatten()
    top_count = max(1, int(len(flat) * 0.05))
    top_pixels = np.partition(flat, -top_count)[-top_count:]
    ela_score = float(np.mean(top_pixels) / 255.0)

    _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    anomaly_regions = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > 500:
            x, y, w, h = cv2.boundingRect(contour)
            anomaly_regions.append([int(x), int(y), int(x + w), int(y + h)])

    return {
        "ela_array": ela_array,
        "ela_score": ela_score,
        "anomaly_regions": anomaly_regions,
    }
