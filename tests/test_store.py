import tempfile
import unittest

from PIL import Image

from inventory.store import Store
from test_review import report


class StoreTests(unittest.TestCase):
    def test_approval_history_survives_reopening_and_stale_edit_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            sheet = store.add(Image.new("RGB", (100, 100)), report())
            store.update(sheet, 1, "0012", "0", 0, "approve")
            with self.assertRaisesRegex(ValueError, "Reload"):
                store.update(sheet, 1, "0012", "20", 0, "approve")
            final = Store(folder).update(sheet, 1, None, None, 1, "reopen")
            self.assertIsNone(final["rows"][0]["verified"])
            self.assertEqual(final["rows"][0]["count"]["raw"], "0")
            self.assertEqual([event["action"] for event in final["history"]], ["approve", "reopen"])

    def test_confirmed_total_is_audited_without_overwriting_ocr(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Store(folder)
            sheet = store.add(Image.new("RGB", (100, 100)), report())
            updated = store.update(sheet, None, None, "14", 0, "confirm-total")
            self.assertEqual(updated["verified_total"], 14)
            self.assertEqual(updated["total"]["raw"], "0")
            self.assertEqual(updated["history"][0]["after"], 14)
