"""Heuristic scan feedback. Recognition results always require human approval."""
import numpy as np
from scipy import ndimage


def assess(image):
    grey = np.asarray(image.convert("L"), dtype=np.float32)
    contrast = float(np.percentile(grey, 95) - np.percentile(grey, 2))
    # Compare strong gradients to the scan's contrast, so dim ink alone does not imply blur.
    dx = np.diff(grey, axis=1, prepend=grey[:, :1])
    dy = np.diff(grey, axis=0, prepend=grey[:1])
    magnitude = np.hypot(dx, dy)
    sharpness = float(np.percentile(magnitude, 99.5) / max(contrast, 1))
    light = ndimage.gaussian_filter(grey[::8, ::8], 7)
    unevenness = float(np.percentile(light, 95) - np.percentile(light, 5))
    warnings = []
    if contrast < 70:
        warnings.append("Low contrast. Check faint strokes against the source crop.")
    if sharpness < 0.39:
        warnings.append("Soft edges detected. Consider retaking the photo in focus.")
    if unevenness > 50:
        warnings.append("Uneven lighting detected. Check the darker cells or retake the photo.")
    if min(image.size) < 450:
        warnings.append("Small image. Use the original scan or a closer photo.")
    return {"warnings": warnings, "contrast": round(contrast, 2),
            "edge_sharpness": round(sharpness, 3), "lighting_range": round(unevenness, 2)}
