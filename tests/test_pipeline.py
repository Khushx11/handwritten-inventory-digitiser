import unittest

from inventory.fixtures import sheet
from inventory.pipeline import extract
from inventory.review import prepare


class PipelineTests(unittest.TestCase):
    def test_corrected_zero_and_crossed_out_cells_keep_source_evidence(self):
        image, _ = sheet(stress="crossed-out")
        aligned, raw = extract(image)
        result = prepare(raw)
        zero, blank, crossed = [result["rows"][index] for index in (0, 2, 3)]
        self.assertEqual(zero["count"]["raw"], "0")
        self.assertEqual(blank["count"]["state"], "blank")
        self.assertIn("Quantity unreadable", crossed["flags"])
        self.assertEqual(crossed["sku"]["raw"], "0642")
        self.assertGreater(aligned.crop(crossed["boxes"][1]).width, 20)
        self.assertEqual(result["total"]["raw"], "80")
