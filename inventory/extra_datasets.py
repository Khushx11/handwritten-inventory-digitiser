"""Verified loaders for the original MNIST and UCI PenDigits partitions."""
import hashlib
from io import BytesIO
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageDraw

MNIST_URL = "https://storage.googleapis.com/tensorflow/tf-keras-datasets/mnist.npz"
PEN_URL = "https://archive.ics.uci.edu/static/public/81/pen+based+recognition+of+handwritten+digits.zip"
MNIST_SHA = "731c5ac602752760c8e48fbffcf8c3b850d9dc2a2aedcf2cc48468fc17b673d1"
PEN_SHA = "1e02bea023613c2b11c9492f6f34caf975420455934f3527d270cee9a1f03b64"


def checked(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"{path.name} does not match its pinned SHA-256")
    return BytesIO(raw)


def mnist(path):
    with np.load(checked(path, MNIST_SHA), allow_pickle=False) as archive:
        return {key: (archive["x_"+key] > 75, archive["y_"+key]) for key in ("train", "test")}


def raster_pendigit(trajectory):
    points = [(round(9+x*0.42), round(51-y*0.42)) for x, y in trajectory.reshape(8, 2)]
    image = Image.new("L", (60, 60))
    ImageDraw.Draw(image).line(points, fill=255, width=5, joint="curve")
    return np.asarray(image) > 0


def pendigits(path):
    result = {}
    with ZipFile(checked(path, PEN_SHA)) as archive:
        for name, filename, count in (("train", "pendigits.tra", 7494), ("test", "pendigits.tes", 3498)):
            with archive.open(filename) as stream:
                data = np.loadtxt(stream, delimiter=",", dtype=np.int16)
            if data.shape != (count, 17) or not np.isin(data[:, -1], np.arange(10)).all():
                raise ValueError("Unexpected PenDigits partition shape or labels")
            result[name] = ([raster_pendigit(row[:-1]) for row in data], data[:, -1])
    return result
