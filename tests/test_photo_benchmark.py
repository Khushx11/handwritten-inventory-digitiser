import unittest
from inventory.photo_benchmark import validate_rows


class PhotoBenchmarkTests(unittest.TestCase):
    def test_reference_keeps_leading_zeros_and_blank_distinct_from_zero(self):
        validate_rows([{"sku": "0012", "quantity": "0"}, {"sku": "0074", "quantity": None}])
        for value in (12, "12", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_rows([{"sku": value, "quantity": "0"}])
        with self.assertRaises(ValueError):
            validate_rows([{"sku": "0012", "quantity": 0}])
