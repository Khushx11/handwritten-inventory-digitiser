import unittest

from PIL import Image, ImageDraw

from inventory.fixtures import sheet
from inventory.grid import deskew, detect
from inventory.image_quality import assess
from inventory.recognise import cell


class ScanQualityTests(unittest.TestCase):
    def test_blur_is_reported_and_a_degraded_grid_can_be_located(self):
        clean, _ = sheet()
        blurred, _ = sheet(stress="heavy-blur")
        self.assertFalse(assess(clean)["warnings"])
        self.assertTrue(any("Soft edges" in item for item in assess(blurred)["warnings"]))
        x, y = detect(deskew(blurred))
        self.assertEqual((len(x), len(y)), (3, 9))
        with self.assertRaisesRegex(ValueError, "ruled grid"):
            detect(Image.new("RGB", (700, 650), "white"))

    def test_faint_ink_cannot_turn_into_a_high_confidence_count(self):
        image = Image.new("RGB", (100, 65), "white")
        self.assertEqual(cell(image, (0, 0, 100, 65))["state"], "blank")
        draw = ImageDraw.Draw(image)
        draw.line(((35, 15), (43, 10), (44, 45)), fill=(184, 184, 184), width=3)
        value = cell(image, (0, 0, 100, 65))
        self.assertNotEqual(value["state"], "blank")
        self.assertLessEqual(value["confidence"], 0.5)
