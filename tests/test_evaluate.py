import unittest
from unittest.mock import patch

from inventory.evaluate import measure_sheet, summarise
from inventory.fixtures import sheet


class BenchmarkAlignmentTests(unittest.TestCase):
    def test_missing_and_spurious_rows_are_charged_separately(self):
        def field(value):
            return {"raw": value, "state": "recognised", "confidence": 1.0}

        def detection(sku, y):
            return {"sku": field(sku), "count": field("5"),
                    "boxes": [(60, y-20, 180, y+20), (290, y-20, 505, y+20)]}

        image, _ = sheet()
        expected = {"rows": [{"sku": "0012", "quantity": "5", "crossed_out": False},
                             {"sku": "0017", "quantity": "5", "crossed_out": False}],
                    "stress": "clean"}
        result = {"catalogue": {"items": {"0012": "one", "0017": "two", "0074": "three"}},
                  "rows": [detection("0074", 75), detection("0017", 227)]}
        with patch("inventory.evaluate.extract", return_value=(image, result)):
            rows = measure_sheet(image, expected, "cell", "held_out", 0, 0, 7)
        self.assertEqual([row["alignment"] for row in rows], ["missing", "matched", "extra"])
        summary = summarise(rows)[0]
        self.assertEqual((summary["reference_rows"], summary["missing_rows"], summary["extra_rows"]), (2, 1, 1))
        self.assertAlmostEqual(summary["exact_row_rate"], 1 / 3)
        self.assertEqual(summary["risk_coverage"][-1]["accepted_row_error"], 0.5)
