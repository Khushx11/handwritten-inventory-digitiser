"""Benchmark public UCI pen strokes composited into held-out stocktake layouts."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

from .evaluate import CUTOFFS, measure_sheet, summarise
from .fixtures import sheet
from .recognise import model

ARCHIVE_SHA256 = "06e484103d21ead80ec7675059d3ffe66f39f51bfcb9c77a00fbbfb1c85546dc"
ARCHIVE_URL = "https://archive.ics.uci.edu/static/public/160/uji+pen+characters.zip"


def parse_writer(text):
    samples = defaultdict(list)
    strokes = None
    stroke = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith(".SEGMENT"):
            match = re.search(r'"([0-9])"$', line)
            strokes = [] if match else None
            if match:
                samples[match[1]].append(strokes)
            stroke = None
        elif strokes is None:
            continue
        elif line == ".PEN_DOWN":
            stroke = []
            strokes.append(stroke)
        elif line == ".PEN_UP":
            stroke = None
        elif stroke is not None and re.fullmatch(r"-?\d+\s+-?\d+", line):
            stroke.append(tuple(map(int, line.split())))
    if set(samples) != set("0123456789") or any(len(glyphs) != 2 for glyphs in samples.values()):
        raise ValueError("Expected two samples of each digit per UCI writer.")
    return samples


def renderer(samples):
    def draw_digit(draw, digit, left, top, rng):
        strokes = rng.choice(samples[digit])
        points = [point for stroke in strokes for point in stroke]
        x_min, y_min = min(p[0] for p in points), min(p[1] for p in points)
        width = max(p[0] for p in points) - x_min
        height = max(p[1] for p in points) - y_min
        scale = min(28 / max(1, width), 35 / max(1, height))
        for stroke in strokes:
            path = [(round(left + (x-x_min)*scale), round(top + (y-y_min)*scale))
                    for x, y in stroke]
            if len(path) > 1:
                draw.line(path, fill="#1a3043", width=4, joint="curve")
            elif path:
                draw.point(path[0], fill="#1a3043")
    return draw_digit


def evaluate_writers(archive, classifier=None, extended=False):
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != ARCHIVE_SHA256:
        raise ValueError("The UCI archive does not match the evaluated release checksum.")
    model()
    results = []
    conditions = (None, "blur", "shadow", "skew", "crossed-out")
    if extended:
        conditions += ("heavy-blur", "faint", "low-resolution", "crowded")
    with ZipFile(archive) as source:
        for index in range(1, 12):
            writer = f"w{index:02d}"
            split = "development" if index <= 5 else "held_out"
            samples = parse_writer(source.read(f"UJIpenchars-{writer}").decode("latin-1"))
            draw = renderer(samples)
            for layout in (0,) if split == "development" else (1, 2):
                for offset, stress in enumerate(conditions):
                    seed = index * 1000 + (0 if extended else offset)
                    image, truth = sheet(seed, layout=layout, stress=stress, digit_renderer=draw)
                    for strategy in ("page", "cell"):
                        results.extend(measure_sheet(image, truth, strategy, split, None, layout, seed, writer, classifier))
    return {
        "dataset": "UCI UJI Pen Characters (V1) digit strokes composited onto synthetic sheets.",
        "archive_sha256": digest,
        "source": ARCHIVE_URL,
        "thresholds": list(CUTOFFS),
        "rows": results,
        "summary": summarise(results),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, help="Optional numeric MLP weights")
    parser.add_argument("--extended-stress", action="store_true")
    args = parser.parse_args()
    from .portable_model import PortableMLP
    classifier = PortableMLP(args.model) if args.model else None
    args.output.write_text(json.dumps(evaluate_writers(args.archive, classifier, args.extended_stress), indent=2, allow_nan=False) + "\n")
