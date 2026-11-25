import numpy as np
from scipy import ndimage
from PIL import Image


def ink(image, *, relaxed=False):
    grey = np.asarray(image.convert("L"))
    local = ndimage.uniform_filter(grey.astype(np.float32), size=35)
    if relaxed:
        return (grey < 236) & (grey < local - 11)
    return (grey < 166) & (grey < local - 18)


def line_centres(projection, threshold):
    hits = np.flatnonzero(projection >= threshold)
    sections = np.split(hits, np.flatnonzero(np.diff(hits) > 2) + 1)
    return [int(round(part.mean())) for part in sections if len(part)]


def deskew(image):
    mask = ink(image)
    sample = mask[::3, ::3]
    angles = range(-8, 9)
    def score(angle):
        rotated = ndimage.rotate(sample, angle, reshape=False, order=0)
        return np.square(rotated.sum(axis=1, dtype=float)).sum()
    angle = max(angles, key=lambda a: (score(a), -abs(a)))
    return image.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor="white") if angle else image


def detect(image):
    for relaxed in (False, True):
        mask = ink(image, relaxed=relaxed)
        x = line_centres(mask.sum(axis=0), image.height * 0.46)
        y = line_centres(mask.sum(axis=1), image.width * 0.45)
        if (len(x) == 3 and 4 <= len(y) <= 32
                and min(np.diff(x)) >= 24 and min(np.diff(y)) >= 22):
            return x, y
    raise ValueError("Could not locate a two-column ruled grid. Crop or straighten the page and retry.")


def cell_boxes(x, y):
    """The first row is a header and the last row contains the optional total."""
    return [
        ((x[0]+4, top+4, x[1]-4, bottom-4), (x[1]+4, top+4, x[2]-4, bottom-4))
        for top, bottom in zip(y[1:-2], y[2:-1])
    ], (x[1]+4, y[-2]+4, x[2]-4, y[-1]-4)
