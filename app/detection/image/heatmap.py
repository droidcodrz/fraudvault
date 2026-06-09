import io

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def generate(file_bytes: bytes, ela_result: dict) -> bytes:
    """Generate heatmap overlay PNG from ELA analysis."""
    original = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    orig_arr = np.array(original)
    ela_array = ela_result.get("ela_array")

    if ela_array is None:
        ela_array = np.zeros_like(orig_arr)

    if ela_array.ndim == 3:
        ela_gray = cv2.cvtColor(ela_array, cv2.COLOR_RGB2GRAY)
    else:
        ela_gray = ela_array

    heatmap = cv2.applyColorMap(ela_gray, cv2.COLORMAP_JET)
    heatmap_rgb = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
    blended = cv2.addWeighted(orig_arr, 0.6, heatmap_rgb, 0.4, 0)

    result = Image.fromarray(blended)
    draw = ImageDraw.Draw(result)

    for region in ela_result.get("anomaly_regions", []):
        if len(region) == 4:
            draw.rectangle(region, outline="red", width=2)

    legend_height = 30
    width = result.width
    legend = Image.new("RGB", (width, legend_height), color=(30, 30, 30))
    legend_draw = ImageDraw.Draw(legend)
    legend_draw.text((10, 8), "FraudVault — Tampering Analysis", fill="white")

    combined = Image.new("RGB", (width, result.height + legend_height))
    combined.paste(result, (0, 0))
    combined.paste(legend, (0, result.height))

    buffer = io.BytesIO()
    combined.save(buffer, format="PNG")
    return buffer.getvalue()
