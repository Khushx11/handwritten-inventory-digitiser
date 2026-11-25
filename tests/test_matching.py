import unittest

from inventory.matching import catalogue, distance, suggestions


class CatalogueTests(unittest.TestCase):
    def test_known_ids_keep_leading_zeros_and_ambiguity_is_suggested(self):
        items = catalogue()["items"]
        self.assertIn("0012", items)
        self.assertEqual(suggestions("0012", items), [])
        self.assertEqual(suggestions("0013", items), ["0012", "0017"])
        self.assertEqual(suggestions("4444", items), [])
        self.assertEqual(distance("0012", "012"), 1)
