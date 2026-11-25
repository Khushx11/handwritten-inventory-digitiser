import unittest

from inventory.export import as_csv, records
from inventory.review import approve, prepare, reconcile


def field(value, state="recognised", confidence=1.0):
    return {"raw": value, "state": state, "confidence": confidence}


def report():
    return prepare({
        "catalogue": {"version": "fixture", "items": {"0012": "clips", "0017": "blocks"}},
        "total": field("0"),
        "rows": [{"id": 1, "sku": field("0012"), "count": field("0")},
                 {"id": 2, "sku": field("0012"), "count": field("", "blank")}],
    })


class ReviewTests(unittest.TestCase):
    def test_zero_and_blank_are_distinct_and_exports_keep_leading_zeros(self):
        data = report()
        first, second = data["rows"]
        approve(data, first, "0012", "0")
        with self.assertRaisesRegex(ValueError, "blank is unresolved"):
            approve(data, second, "0017", "")
        self.assertEqual(records(data)["approved"][0]["quantity"], 0)
        self.assertIn("1,0012,0", as_csv(data))
        self.assertEqual(records(data)["unresolved_rows"], [2])

    def test_duplicate_requires_review_and_cannot_be_approved_twice(self):
        data = report()
        first, second = data["rows"]
        self.assertIn("Repeated SKU", first["flags"])
        approve(data, first, "0012", "0")
        with self.assertRaisesRegex(ValueError, "already has an approved row"):
            approve(data, second, "0012", "4")
        self.assertIsNone(reconcile(data)["difference"])
        approve(data, second, "0017", "4")
        self.assertEqual(reconcile(data)["difference"], 4)

    def test_scan_warning_routes_even_high_confidence_rows_to_review(self):
        data = report()
        data["quality_gate"] = True
        data["scan_quality"] = {"warnings": ["Soft edges detected."]}
        first = prepare(data, 0.99)["rows"][0]
        self.assertIn("Scan quality needs review", first["flags"])
        self.assertIsNone(first["verified"])
