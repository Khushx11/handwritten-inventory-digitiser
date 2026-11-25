"""Training-only degradations for isolated handwriting crops."""
import numpy as np
from scipy import ndimage

from .recognise import glyph


def degraded_examples(images, labels, sample_count, seed):
    rng = np.random.default_rng(seed)
    selected = rng.choice(len(labels), size=min(sample_count, len(labels)), replace=False)
    result = []
    for index in selected:
        image = np.asarray(images[index], dtype=np.float32)
        # Keep the evaluation sheets completely outside this transform.
        if rng.random() < 0.35:
            image = ndimage.rotate(image, rng.uniform(-12, 12), reshape=False, order=1)
        sigma = rng.uniform(0.45, 1.55)
        texture = ndimage.gaussian_filter(image, sigma)
        texture *= rng.uniform(0.50, 1.0)
        texture += rng.normal(0, 0.025, texture.shape)
        degraded = texture > rng.uniform(0.19, 0.39)
        result.append(glyph(degraded if degraded.any() else image > 0))
    return np.asarray(result, dtype=np.float32), labels[selected]
