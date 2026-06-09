import io

import cv2
import numpy as np
from PIL import Image


def analyse(file_bytes: bytes) -> dict:
    """Copy-move detection using SIFT feature matching."""
    image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)

    sift = cv2.SIFT_create()
    keypoints, descriptors = sift.detectAndCompute(gray, None)

    if descriptors is None or len(keypoints) < 2:
        return {"clone_score": 0.0, "matched_regions": []}

    index_params = dict(algorithm=1, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    matches = flann.knnMatch(descriptors, descriptors, k=3)

    good_matches = []
    for match_group in matches:
        if len(match_group) < 2:
            continue
        m, n = match_group[0], match_group[1]
        if m.distance < 0.75 * n.distance and m.queryIdx != m.trainIdx:
            pt1 = keypoints[m.queryIdx].pt
            pt2 = keypoints[m.trainIdx].pt
            dist = np.sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)
            if dist > 20:
                good_matches.append((pt1, pt2))

    clone_score = min(1.0, len(good_matches) / 50)
    return {"clone_score": clone_score, "matched_regions": good_matches}
