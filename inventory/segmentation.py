"""Recover bounded numeric sequences by testing several plausible cut positions."""
from math import log

import numpy as np
from scipy import ndimage


def enhanced_mask(image):
    grey = np.asarray(image.convert("L"), dtype=np.float32)
    sharp = grey + 1.25 * (grey - ndimage.gaussian_filter(grey, 1.45))
    background = ndimage.uniform_filter(grey, size=31)
    return (sharp < 239) & (sharp < background - 10)


def split_sequence(mask, length, features, classifier):
    if not 2 <= length <= 6:
        return None
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    cropped = mask[ys.min():ys.max()+1, xs.min():xs.max()+1]
    height, width = cropped.shape
    pitch = width / length
    if height < 12 or not 3 <= pitch <= height * 1.1:
        return None

    layers = [[0]]
    for i in range(1, length):
        centre = round(i * pitch)
        radius = max(2, round(pitch * 0.24))
        layers.append(list(range(max(2, centre-radius), min(width-1, centre+radius+1))))
    layers.append([width])
    projection = cropped.sum(axis=0) / height
    segments, keys = [], []
    for i, (lefts, rights) in enumerate(zip(layers, layers[1:])):
        for left in lefts:
            for right in rights:
                if not pitch * 0.45 <= right-left <= pitch * 1.55:
                    continue
                piece = cropped[:, left:right]
                nonzero = np.nonzero(piece)
                if len(nonzero[0]) < 14 or np.ptp(nonzero[0]) < height * 0.47:
                    continue
                keys.append((i, left, right))
                segments.append(features(piece))
    if not segments:
        return None

    scores = {
        key: (int(classifier.classes_[p.argmax()]), float(p.max()))
        for key, p in zip(keys, classifier.predict_proba(segments))
    }
    paths = {0: (0.0, "", 1.0)}
    for i, rights in enumerate(layers[1:]):
        next_layer = {}
        for right in rights:
            for left, (previous, digits, minimum) in paths.items():
                entry = scores.get((i, left, right))
                if not entry:
                    continue
                label, confidence = entry
                cut = min(projection[right-1:right+1]) if right < width else 0
                width_penalty = 0.4 * abs((right-left)/pitch - 1)
                score = previous + log(max(confidence, 1e-9)) - 2.0*cut - width_penalty
                if right not in next_layer or score > next_layer[right][0]:
                    next_layer[right] = (score, digits + str(label), min(minimum, confidence))
        paths = next_layer
    return paths.get(width)
