"""Deliberate human approval and sheet-level consistency checks."""
from collections import Counter
import re

from .pipeline import reasons


def prepare(report, cutoff=0.80):
    items = report["catalogue"]["items"]
    repeated = Counter(row["sku"]["raw"] for row in report["rows"] if row["sku"]["raw"] in items)
    for row in report["rows"]:
        row["flags"] = reasons(row, items, cutoff)
        if repeated[row["sku"]["raw"]] > 1:
            row["flags"].append("Repeated SKU")
        row["verified"] = None
    return report


def approve(report, row, sku, quantity):
    if sku not in report["catalogue"]["items"]:
        raise ValueError("Select a SKU present in the versioned catalogue.")
    if not isinstance(quantity, str) or not re.fullmatch(r"[0-9]{1,6}", quantity):
        raise ValueError("Enter a quantity from 0 to 999999. A blank is unresolved.")
    if any(other is not row and other.get("verified") and other["verified"]["sku"] == sku
           for other in report["rows"]):
        raise ValueError("This SKU already has an approved row. Resolve duplicates first.")
    row["verified"] = {"sku": sku, "quantity": int(quantity)}


def reconcile(report):
    counts = [row["verified"]["quantity"] for row in report["rows"] if row["verified"]]
    total = report["total"]
    stated = int(total["raw"]) if total["state"] == "recognised" and total["confidence"] >= 0.80 else None
    unresolved = len(report["rows"]) - len(counts)
    return {"approved_sum": sum(counts), "unresolved": unresolved, "stated_total": stated,
            "difference": sum(counts) - stated if not unresolved and stated is not None else None}
