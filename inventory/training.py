"""Rasterise the five UCI development writers with fixed augmentations."""
from importlib.resources import files
import json

from PIL import Image, ImageDraw

from .grid import ink


def training_glyphs():
    samples = json.loads(files("inventory").joinpath("uji_training.json").read_text())
    for writer in samples["writers"].values():
        for digit, candidates in writer.items():
            for strokes in candidates:
                points = [point for stroke in strokes for point in stroke]
                x_low, y_low = min(x for x, _ in points), min(y for _, y in points)
                dx = max(x for x, _ in points) - x_low
                dy = max(y for _, y in points) - y_low
                scale = min(28 / max(dx, 1), 35 / max(dy, 1))
                for angle in (-10, -5, 0, 5, 10):
                    for thickness in (3, 4, 5):
                        image = Image.new("L", (60, 65), "white")
                        draw = ImageDraw.Draw(image)
                        for stroke in strokes:
                            path = [(round(12+(x-x_low)*scale), round(12+(y-y_low)*scale)) for x,y in stroke]
                            if len(path) > 1:
                                draw.line(path, fill="black", width=thickness, joint="curve")
                            elif path:
                                draw.point(path[0], fill="black")
                        image = image.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor="white")
                        yield ink(image), int(digit)
