"""Prepare verified model weights and launch conservative review mode."""
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

from .extra_datasets import MNIST_SHA, MNIST_URL, PEN_SHA, PEN_URL
from .extra_training import run
from .webserver import main as serve


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def materialise(path, url, expected):
    if path.is_file() and digest(path) == expected:
        return
    with TemporaryDirectory(dir=path.parent) as temporary:
        candidate = Path(temporary) / path.name
        with urlopen(url, timeout=90) as response:
            raw = response.read(20_000_001)
        if len(raw) > 20_000_000 or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"Downloaded {path.name} failed source verification")
        candidate.write_bytes(raw)
        candidate.replace(path)


def prepare_models(directory):
    directory.mkdir(parents=True, exist_ok=True)
    mnist, pen = directory / "mnist.npz", directory / "pendigits.zip"
    checkpoints = [directory / f"handwriting-{mode}.npz" for mode in ("mlp", "robust")]
    for path, robust in zip(checkpoints, (False, True)):
        receipt = path.with_suffix(".json")
        if path.is_file() and receipt.is_file():
            try:
                recorded = json.loads(receipt.read_text())
            except (OSError, ValueError):
                recorded = {}
            expected_mode = "degradation-augmented" if robust else "standard"
            if (isinstance(recorded, dict) and recorded.get("sha256") == digest(path)
                    and recorded.get("training", {}).get("mode") == expected_mode):
                continue
        materialise(mnist, MNIST_URL, MNIST_SHA)
        materialise(pen, PEN_URL, PEN_SHA)
        print(f"Training {path.stem} from verified source archives…", flush=True)
        with TemporaryDirectory(dir=directory) as temporary:
            weights = Path(temporary) / path.name
            metrics = Path(temporary) / "metrics.json"
            run(mnist, pen, metrics, weights, robust=robust)
            metadata = json.loads(metrics.read_text())
            metadata["sha256"] = digest(weights)
            metrics.write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n")
            weights.replace(path)
            metrics.replace(receipt)
    return checkpoints


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path("runtime"))
    parser.add_argument("--port", type=int, default=8013)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    standard, robust = prepare_models(args.workspace / "models")
    if not args.prepare_only:
        serve(["--port", str(args.port), "--workspace", str(args.workspace / "cross-checked"),
               "--model", str(robust), "--comparison-model", str(standard)])


if __name__ == "__main__":
    main()
