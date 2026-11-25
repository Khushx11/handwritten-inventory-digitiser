"""Evaluate consent-cleared stocktake photos without publishing images or row values."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

from .geometry import decode, rectify
from .image_quality import assess
from .pipeline import extract
from .portable_model import CrossCheckedMLP
from .review import prepare


def validate_rows(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("Each photo must have manually verified rows in visual order.")
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("sku"), str) or not re.fullmatch(r"[0-9]{4}", row["sku"]):
            raise ValueError("Reference SKUs must be four-digit strings, including leading zeros.")
        if "quantity" not in row:
            raise ValueError("Include quantity explicitly, using null for a blank.")
        count = row["quantity"]
        if count is not None and (not isinstance(count, str) or not re.fullmatch(r"[0-9]{1,6}", count)):
            raise ValueError("Use a digit string for a count or null for a blank.")


def evaluate(root, manifest, classifier):
    groups = defaultdict(lambda: {
        "photos": 0, "reference_rows": 0, "grid_failures": 0, "row_count_mismatches": 0,
        "exact_rows": 0, "exact_counts": 0, "routed_by_review_policy": 0,
    })
    entries = json.loads(manifest.read_text())["photos"]
    if not entries:
        raise ValueError("No photos were provided for evaluation.")
    for entry in entries:
        rows = entry["rows"]
        validate_rows(rows)
        source = (root / entry["image"]).resolve()
        if not source.is_relative_to(root.resolve()):
            raise ValueError("Photo path must stay inside the evaluation folder.")
        group = groups[entry["condition"]]
        group["photos"] += 1
        group["reference_rows"] += len(rows)
        image = decode(source.read_bytes())
        if entry.get("corners"):
            image = rectify(image, entry["corners"])
        rotation = entry.get("rotation", 0)
        if rotation not in (0, 90, 180, 270):
            raise ValueError("Unsupported photo rotation.")
        if rotation:
            image = image.rotate(rotation, expand=True)
        try:
            _, report = extract(image, classifier=classifier, recover_touching=True)
        except ValueError:
            group["grid_failures"] += 1
            group["routed_by_review_policy"] += len(rows)
            continue
        detected = report["rows"]
        if len(detected) != len(rows):
            group["row_count_mismatches"] += 1
            group["routed_by_review_policy"] += len(rows)
            continue
        report["scan_quality"] = assess(image)
        report["quality_gate"] = True
        prepare(report, classifier.review_cutoff)
        for truth, prediction in zip(rows, detected):
            sku, quantity = prediction["sku"], prediction["count"]
            quantity_matches = quantity["state"] == "blank" if truth["quantity"] is None else (
                quantity["state"] == "recognised" and quantity["raw"] == truth["quantity"]
            )
            group["exact_counts"] += int(quantity_matches)
            group["exact_rows"] += int(quantity_matches and sku["state"] == "recognised"
                                       and sku["raw"] == truth["sku"])
            group["routed_by_review_policy"] += int(bool(prediction["flags"]))
    return {"scope": "Independent photos; ordered exact matches on sheets with matching row counts.",
            "models": [classifier.model_id, classifier.comparison.model_id], "conditions": dict(groups)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--photos", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--comparison-model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.photos, args.manifest, CrossCheckedMLP(args.model, args.comparison_model))
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
