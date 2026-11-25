from io import BytesIO

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_PIXELS = 12_000_000


def decode(raw):
    try:
        with Image.open(BytesIO(raw)) as source:
            if source.format not in {"PNG", "JPEG", "WEBP"}:
                raise ValueError("Upload a PNG, JPEG or WebP image.")
            if source.width * source.height > MAX_PIXELS:
                raise ValueError("Image exceeds 12 megapixels.")
            return ImageOps.exif_transpose(source).convert("RGB")
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError) as error:
        raise ValueError("The upload is not a readable image.") from error


def rectify(image, corners):
    """Warp four user-confirmed page corners in top-left clockwise order."""
    points = np.asarray(corners, dtype=float)
    if points.shape != (4, 2) or not np.isfinite(points).all():
        raise ValueError("Select four valid page corners.")
    if (points < 0).any() or (points[:, 0] >= image.width).any() or (points[:, 1] >= image.height).any():
        raise ValueError("Page corners must lie inside the source image.")
    edges = np.roll(points, -1, axis=0) - points
    next_edges = np.roll(edges, -1, axis=0)
    cross = edges[:, 0] * next_edges[:, 1] - edges[:, 1] * next_edges[:, 0]
    if np.any(cross <= 0):
        raise ValueError("Select a convex page clockwise from the top-left corner.")
    width = round(max(np.linalg.norm(edges[0]), np.linalg.norm(edges[2])))
    height = round(max(np.linalg.norm(edges[1]), np.linalg.norm(edges[3])))
    if min(width, height) < 100 or width * height > MAX_PIXELS:
        raise ValueError("Selected page dimensions are outside the supported range.")
    output = [(0, 0), (width, 0), (width, height), (0, height)]
    matrix, targets = [], []
    for (x, y), (u, v) in zip(output, points):
        matrix.extend([[x, y, 1, 0, 0, 0, -u*x, -u*y], [0, 0, 0, x, y, 1, -v*x, -v*y]])
        targets.extend([u, v])
    try:
        coefficients = np.linalg.solve(matrix, targets)
    except np.linalg.LinAlgError as error:
        raise ValueError("Page corners do not define a usable perspective.") from error
    return image.transform((width, height), Image.Transform.PERSPECTIVE, coefficients, Image.Resampling.BICUBIC)
