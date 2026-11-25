"""Deliberate human approval and sheet-level consistency checks."""
from collections import Counter
import re

from .pipeline import reasons


def prepare(report, cutoff=0.80):
    items = report["catalogue"]["items"]
    repeated = Counter(row["sku"]["raw"] for row in report["rows"] if row["sku"]["raw"] in items)
    for row in report["rows"]:
        row["flags"] = reasons(row, items, cutoff)
        if report.get("quality_gate") and report.get("scan_quality", {}).get("warnings"):
            row["flags"].append("Scan quality needs review")
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
    row.pop("exclusion_reason", None)


def exclude(row, reason):
    if not isinstance(reason, str) or not 2 <= len(reason.strip()) <= 240:
        raise ValueError("Enter an exclusion reason of 2 to 240 characters.")
    row["verified"] = None
    row["exclusion_reason"] = reason.strip()


def reconcile(report):
    counts = [row["verified"]["quantity"] for row in report["rows"] if row["verified"]]
    total = report["total"]
    confirmed = report.get("verified_total")
    stated = confirmed if confirmed is not None else (
        int(total["raw"]) if total["state"] == "recognised" and total["confidence"] >= 0.80 else None
    )
    excluded = sum(bool(row.get("exclusion_reason")) for row in report["rows"])
    unresolved = len(report["rows"]) - len(counts) - excluded
    return {"approved_sum": sum(counts), "unresolved": unresolved, "excluded": excluded, "stated_total": stated,
            "total_source": "reviewed" if confirmed is not None else "ocr" if stated is not None else None,
            "difference": sum(counts) - stated if not unresolved and stated is not None else None}



def confirm_total(report, text):
    if not isinstance(text, str) or not re.fullmatch(r"[0-9]{1,8}", text):
        raise ValueError("Enter the printed total as a whole number of up to eight digits.")
    report["verified_total"] = int(text)
