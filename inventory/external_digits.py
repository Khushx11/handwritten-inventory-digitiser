"""External check on manually drawn HwD-1000 digits and paired image degradations."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from .grid import ink
from .portable_model import PortableMLP
from .recognise import glyph

SOURCE = "https://github.com/niklashenning/hwd-1000-dataset"
REVISION = "93b3ba9e45624ee557360229a42298eaa6b3a106"


def benchmark(dataset, checkpoints):
    raw_manifest = (dataset / "dataset.csv").read_bytes()
    manifest = list(csv.reader(raw_manifest.decode("utf-8-sig").splitlines()))
    digest = hashlib.sha256(raw_manifest)
    digits, labels = [], []
    for path, label in manifest[1:]:
        candidate = (dataset / path).resolve()
        if not candidate.is_relative_to(dataset.resolve()) or candidate.suffix != ".png":
            raise ValueError("Unexpected path in HwD-1000 manifest")
        digest.update(candidate.read_bytes())
        with Image.open(candidate) as raw:
            if raw.size != (28, 28):
                raise ValueError("Expected a 28×28 source digit")
            digits.append(ImageOps.expand(raw.convert("L"), border=4, fill=255))
        labels.append(int(label))
    if len(labels) != 1000 or np.bincount(labels).tolist() != [100] * 10:
        raise ValueError("Expected 100 examples per digit")
    models = {name: PortableMLP(path) for name, path in checkpoints.items()}
    results = []
    for condition, transform in (
        ("as-released", lambda image: image),
        ("gaussian-blur-1.6px", lambda image: image.filter(ImageFilter.GaussianBlur(1.6))),
        ("gaussian-blur-2.8px", lambda image: image.filter(ImageFilter.GaussianBlur(2.8))),
        ("faint-45-percent", lambda image: Image.blend(image, Image.new("L", image.size, 255), 0.45)),
    ):
        masks = [ink(transform(image), relaxed=True) for image in digits]
        features = [glyph(mask) for mask in masks]
        missing = np.asarray([not mask.any() for mask in masks])
        for name, classifier in models.items():
            predicted = classifier.predict_proba(features).argmax(axis=1)
            predicted[missing] = -1
            results.append({
                "model": name, "condition": condition, "samples": len(labels),
                "accuracy": float(np.mean(predicted == labels)),
                "empty_masks": int(missing.sum()),
                "predictions": predicted.tolist(),
            })
    return {"source": SOURCE, "source_revision": REVISION, "input_sha256": digest.hexdigest(),
            "training_overlap": "No HwD-1000 files were used in training or model selection.",
            "labels": labels, "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--robust", required=True, type=Path)
    parser.add_argument("--sheet-adapted", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = benchmark(args.dataset, {"augmented": args.robust, "sheet-adapted": args.sheet_adapted})
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
