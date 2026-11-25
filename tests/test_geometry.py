import unittest

from inventory.fixtures import sheet
from inventory.geometry import rectify
from inventory.grid import cell_boxes, deskew, detect


class GeometryTests(unittest.TestCase):
    def test_held_out_layouts_use_detected_boundaries(self):
        for layout in (1, 2):
            with self.subTest(layout=layout):
                image, truth = sheet(layout=layout, style=2, stress="skew")
                aligned = deskew(image)
                x, y = detect(aligned)
                rows, _ = cell_boxes(x, y)
                self.assertEqual(len(rows), len(truth["rows"]))
                self.assertTrue(all(left[2] < right[0] for left, right in rows))
                self.assertGreater(abs(x[1] - 270), 20)

    def test_perspective_corners_must_be_convex_and_in_bounds(self):
        image, _ = sheet()
        with self.assertRaises(ValueError):
            rectify(image, [(10,10), (500,500), (500,10), (10,500)])
        changed = rectify(image, [(0,0), (image.width-1,0),
                                  (image.width-1,image.height-1), (0,image.height-1)])
        self.assertEqual(changed.size, (image.width-1, image.height-1))
