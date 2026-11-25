"""Recover bounded numeric sequences by testing several plausible cut positions."""
from math import log

import numpy as np
from PIL import Image
from scipy import ndimage


def enhanced_mask(image):
    grey = np.asarray(image.convert("L"), dtype=np.float32)
    sharp = grey + 1.25 * (grey - ndimage.gaussian_filter(grey, 1.45))
    background = ndimage.uniform_filter(grey, size=31)
    return (sharp < 239) & (sharp < background - 10)


def split_sequence(mask, length, features, classifier, known=None):
    if not 2 <= length <= 6:
        return None
    ys, xs = np.nonzero(mask)
    if not len(xs):
        return None
    cropped = mask[ys.min():ys.max()+1, xs.min():xs.max()+1]
    height, width = cropped.shape
    if max(height, width) > 220:
        scale = 220 / max(height, width)
        reduced = Image.fromarray(cropped.astype("uint8") * 255).resize(
            (max(1, round(width*scale)), max(1, round(height*scale))), Image.Resampling.BOX,
        )
        cropped = np.asarray(reduced) >= 85
        height, width = cropped.shape
    pitch = width / length
    if height < 12 or not 3 <= pitch <= height * 1.1:
        return None

    layers = [[0]]
    for i in range(1, length):
        centre = round(i * pitch)
        radius = min(15, max(2, round(pitch * 0.24)))
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

    scores = dict(zip(keys, classifier.predict_proba(segments)))
    paths = {(0, ""): (0.0, 1.0)}
    prefixes = [{value[:i] for value in known} for i in range(length+1)] if known else None
    labels = classifier.classes_
    for i, rights in enumerate(layers[1:]):
        next_layer = {}
        for right in rights:
            for (left, digits), (previous, minimum) in paths.items():
                probabilities = scores.get((i, left, right))
                if probabilities is None:
                    continue
                cut = min(projection[right-1:right+1]) if right < width else 0
                width_penalty = 0.4 * abs((right-left)/pitch - 1)
                best = probabilities.argmax()
                choices = range(len(labels)) if known else (best,)
                for index in choices:
                    proposal = digits + str(labels[index])
                    confidence = float(probabilities[index])
                    if known and (proposal not in prefixes[i+1] or confidence < max(0.15, probabilities[best]*0.30)):
                        continue
                    score = previous + log(max(confidence, 1e-9)) - 2.0*cut - width_penalty
                    key = (right, proposal) if known else (right, "")
                    saved = next_layer.get(key)
                    if saved is None or score > saved[0]:
                        next_layer[key] = (score, min(minimum, confidence), proposal)
        if not known:
            # Keep only the highest-scoring sequence reaching each cut.
            paths = {(right, proposal): (score, minimum)
                     for (right, _), (score, minimum, proposal) in next_layer.items()}
        else:
            paths = {(right, proposal): (score, minimum)
                     for (right, proposal), (score, minimum, _) in next_layer.items()}
    ranked = sorted(((score, digits, minimum) for (right, digits), (score, minimum) in paths.items()
                     if right == width), reverse=True)
    if not ranked or (known and len(ranked) > 1 and ranked[0][0]-ranked[1][0] < 0.22):
        return None
    return ranked[0]
