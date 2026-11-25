import tempfile
import unittest
from pathlib import Path

import numpy as np

from inventory.portable_model import PortableMLP


class PortableModelTests(unittest.TestCase):
    def test_numeric_weights_produce_normalised_deterministic_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.npz"
            weights = {
                "classes": np.arange(10),
                "w0": np.zeros((64, 128)), "b0": np.zeros(128),
                "w1": np.zeros((128, 64)), "b1": np.zeros(64),
                "w2": np.zeros((64, 10)), "b2": np.arange(10, dtype=float),
            }
            np.savez(path, **weights)
            probability = PortableMLP(path).predict_proba(np.zeros((2, 64)))
            np.testing.assert_allclose(probability.sum(axis=1), [1, 1])
            np.testing.assert_array_equal(probability.argmax(axis=1), [9, 9])
            weights["w1"][0, 0] = float("nan")
            np.savez(path, **weights)
            with self.assertRaisesRegex(ValueError, "finite"):
                PortableMLP(path)
