import unittest

import numpy as np
from PIL import Image, ImageDraw

from inventory.recognise import cell
from inventory.review import prepare
from inventory.segmentation import enhanced_mask


class ZeroClassifier:
    classes_ = np.arange(10)

    def predict_proba(self, features):
        result = np.zeros((len(features), 10))
        result[:, 0] = 1
        return result


class SegmentationTests(unittest.TestCase):
    def test_touching_ink_suggestion_preserves_raw_unreadable_state(self):
        image = Image.new("RGB", (125, 70), "white")
        draw = ImageDraw.Draw(image)
        for x in (13, 24, 35, 46):
            draw.rectangle((x, 15, x+6, 44), fill="black")
        draw.line((15, 30, 50, 30), fill="black", width=2)
        found = cell(image, (0, 0, 125, 70), expected=4, classifier=ZeroClassifier(),
                     recover_touching=True, known={"0000"})
        self.assertEqual(found["segmentation_suggestion"], "0000")
        self.assertNotEqual(found["raw"], "0000")
        self.assertEqual(found["state"], "unreadable")
        report = {
            "catalogue": {"items": {"0000": "Demo"}},
            "rows": [{"sku": found, "count": {"raw": "3", "state": "recognised", "confidence": 1}}],
        }
        row = prepare(report)["rows"][0]
        self.assertIn("SKU touching-digit suggestion needs review", row["flags"])
        self.assertIsNone(row["verified"])

    def test_flat_crop_stays_empty_after_contrast_retry(self):
        self.assertFalse(enhanced_mask(Image.new("L", (120, 55), "white")).any())
