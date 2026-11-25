"""Train a reproducible digit candidate and test each official partition separately."""
import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.neural_network import MLPClassifier
from threadpoolctl import threadpool_limits

from .extra_datasets import MNIST_SHA, MNIST_URL, PEN_SHA, PEN_URL, mnist, pendigits
from .recognise import glyph, model


def features(images):
    return np.array([glyph(mask) for mask in images], dtype=np.float32)


def score(labels, predicted):
    return {
        "samples": len(labels),
        "accuracy": accuracy_score(labels, predicted),
        "macro_f1": f1_score(labels, predicted, average="macro"),
        "confusion_matrix": confusion_matrix(labels, predicted, labels=list(range(10))).tolist(),
    }


def run(mnist_path, pen_path, output, weights):
    datasets = {"mnist": mnist(mnist_path), "pendigits": pendigits(pen_path)}
    transformed = {
        name: {partition: (features(images), labels) for partition, (images, labels) in data.items()}
        for name, data in datasets.items()
    }
    train = [data["train"] for data in transformed.values()]
    x_train = np.concatenate([x for x, _ in train])
    y_train = np.concatenate([y for _, y in train])
    classifier = MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=40, early_stopping=True,
                               validation_fraction=0.10, batch_size=256, random_state=42)
    baseline = model()
    with threadpool_limits(limits=4):
        classifier.fit(x_train, y_train)
        reports = {}
        for name, data in transformed.items():
            x_test, y_test = data["test"]
            reports[name] = {
                "train_rows": len(data["train"][1]),
                "baseline": score(y_test, baseline.predict(x_test)),
                "candidate": score(y_test, classifier.predict(x_test)),
            }
    np.savez_compressed(weights, classes=classifier.classes_, **{
        f"{kind}{i}": array
        for kind, arrays in (("w", classifier.coefs_), ("b", classifier.intercepts_))
        for i, array in enumerate(arrays)
    })
    report = {
        "model": "MLP 128/64 ReLU, seed 42, early stopping on training-only validation",
        "evaluation": "Official held-out test partitions scored separately; no test rows used for fitting.",
        "input_sources": {
            "mnist": {"url": MNIST_URL, "sha256": MNIST_SHA},
            "pendigits": {"url": PEN_URL, "sha256": PEN_SHA},
        },
        "epochs": classifier.n_iter_,
        "results": reports,
    }
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mnist", required=True, type=Path)
    parser.add_argument("--pendigits", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--weights", required=True, type=Path)
    args = parser.parse_args()
    run(args.mnist, args.pendigits, args.output, args.weights)
