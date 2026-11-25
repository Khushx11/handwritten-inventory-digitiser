"""Small offline digit classifier trained on the scikit-learn digits dataset."""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from sklearn.datasets import load_digits
from sklearn.neighbors import KNeighborsClassifier

from .grid import cell_boxes, detect, ink
from .training import training_glyphs


def glyph(mask):
    y, x = np.nonzero(mask)
    if not len(x):
        return np.zeros(64)
    crop = Image.fromarray(np.asarray(mask[y.min():y.max()+1, x.min():x.max()+1] * 255, dtype=np.uint8))
    ratio = min(7 / crop.width, 8 / crop.height)
    crop = crop.resize((max(1, round(crop.width * ratio)), max(1, round(crop.height * ratio))), Image.Resampling.LANCZOS)
    canvas = Image.new("L", (8, 8))
    canvas.paste(crop, ((8-crop.width)//2, (8-crop.height)//2))
    return np.asarray(canvas).ravel() / 255


@lru_cache(maxsize=1)
def model():
    data = load_digits()
    features = [glyph(np.asarray(Image.fromarray((image * 15).astype("uint8")).resize((40, 40))) > 85)
                for image in data.images]
    targets = list(data.target)
    # Supplement handwritten digits with the two development stroke styles.
    # Evaluation layouts and stroke styles are deliberately excluded.
    from .fixtures import sheet
    for style in (0, 1):
        for seed in range(100, 120):
            image, truth = sheet(seed, style, layout=0)
            boxes, _ = cell_boxes(*detect(image))
            for region, row in zip(boxes, truth["rows"]):
                for box, text in zip(region, (row["sku"], row["quantity"])):
                    parts = components(ink(image.crop(box)))
                    if len(parts) == len(text):
                        features.extend(glyph(part[-1]) for part in parts)
                        targets.extend(int(value) for value in text)
    for mask, digit in training_glyphs():
        features.append(glyph(mask))
        targets.append(digit)
    return KNeighborsClassifier(n_neighbors=9, weights="distance", n_jobs=1).fit(features, targets)


def components(mask):
    labels, count = ndimage.label(mask, np.ones((3, 3)))
    found = []
    for i, bounds in enumerate(ndimage.find_objects(labels, max_label=count), 1):
        y, x = bounds
        if (y.stop - y.start) < 8 or (x.stop - x.start) < 2:
            continue
        piece = labels[bounds] == i
        if piece.sum() >= 18:
            found.append((x.start, y.start, x.stop, y.stop, piece))
    return sorted(found, key=lambda part: part[0])


def recognise(parts, *, width, expected=None, classifier=None):
    if not parts:
        return {"raw": "", "confidence": 0.0, "state": "blank"}
    if len(parts) > 6 or any(right-left >= width * 0.4 or right-left > (bottom-top)*1.5
                             for left, top, right, bottom, _ in parts):
        return {"raw": "", "confidence": 0.0, "state": "unreadable"}
    classifier = classifier or model()
    probabilities = classifier.predict_proba([glyph(part[-1]) for part in parts])
    raw = "".join(str(digit) for digit in classifier.classes_[probabilities.argmax(axis=1)])
    confidence = float(probabilities.max(axis=1).min())
    state = "unreadable" if expected and len(raw) != expected else "recognised"
    return {"raw": raw, "confidence": round(confidence, 5), "state": state}


def cell(image, box, expected=None, classifier=None):
    crop = image.crop(box)
    return recognise(components(ink(crop)), width=crop.width, expected=expected, classifier=classifier)

@lru_cache(maxsize=1)
def printed_model():
    features, targets = [], []
    for size in (24, 27, 31, 35, 38):
        for digit in range(10):
            sample = Image.new("L", (60, 65), "white")
            ImageDraw.Draw(sample).text((8, 5), str(digit), fill="black", font_size=size)
            features.append(glyph(ink(sample)))
            targets.append(digit)
    return KNeighborsClassifier(n_neighbors=5, weights="distance", n_jobs=1).fit(features, targets)


def printed_total(image, box):
    crop = image.crop(box)
    return recognise(components(ink(crop)), width=crop.width, classifier=printed_model())
