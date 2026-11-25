"""Load numeric model weights without Python-object deserialisation."""
import numpy as np


class PortableMLP:
    def __init__(self, path):
        with np.load(path, allow_pickle=False) as archive:
            self.classes_ = archive["classes"]
            self.weights = [archive[f"w{i}"] for i in range(3)]
            self.bias = [archive[f"b{i}"] for i in range(3)]
        if not np.array_equal(self.classes_, np.arange(10)):
            raise ValueError("Model must expose classes 0–9 in order")
        for (inputs, outputs), weight, bias in zip(
            ((64, 128), (128, 64), (64, 10)), self.weights, self.bias
        ):
            if weight.shape != (inputs, outputs) or bias.shape != (outputs,):
                raise ValueError("Unexpected handwriting model dimensions")
            if not np.isfinite(weight).all() or not np.isfinite(bias).all():
                raise ValueError("Handwriting model weights must be finite")

    def predict_proba(self, features):
        value = np.asarray(features, dtype=np.float32)
        for index, (weight, bias) in enumerate(zip(self.weights, self.bias)):
            value = value @ weight + bias
            if index < 2:
                value = np.maximum(value, 0)
        result = np.exp(value - value.max(axis=1, keepdims=True))
        return result / result.sum(axis=1, keepdims=True)


class CrossCheckedMLP(PortableMLP):
    """Keep the primary reading and expose independent model disagreement."""

    def __init__(self, primary, comparison):
        super().__init__(primary)
        self.comparison = PortableMLP(comparison)

    def cross_check(self, features):
        return self.comparison.predict_proba(features)
