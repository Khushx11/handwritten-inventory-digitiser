import hashlib
from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from inventory.setup import materialise


class SetupTests(unittest.TestCase):
    def test_only_verified_downloads_replace_cache(self):
        correct = b"trusted archive"
        digest = hashlib.sha256(correct).hexdigest()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "source.npz"
            path.write_bytes(b"stale file")
            with patch("inventory.setup.urlopen", return_value=BytesIO(b"wrong checksum")):
                with self.assertRaisesRegex(ValueError, "failed source verification"):
                    materialise(path, "https://example.invalid/source", digest)
            self.assertEqual(path.read_bytes(), b"stale file")
            with patch("inventory.setup.urlopen", return_value=BytesIO(correct)) as download:
                materialise(path, "https://example.invalid/source", digest)
                materialise(path, "https://example.invalid/source", digest)
                download.assert_called_once()
            self.assertEqual(path.read_bytes(), correct)
