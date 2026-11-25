"""Make supervised scan-like glyphs using development-only UCI writers."""
from importlib.resources import files
import json

import numpy as np

from .fixtures import LAYOUTS, sheet
from .grid import ink
from .segmentation import enhanced_mask


def sheet_glyphs():
    from .writer_benchmark import renderer

    source = json.loads(files("inventory").joinpath("uji_training.json").read_text())
    _, _, left, middle, _, top, step = LAYOUTS[0]
    for writer_index, writer in enumerate(source["writers"].values()):
        draw = renderer(writer)
        for sample in range(24):
            condition = ("blur", "heavy-blur", "low-resolution", "shadow", "faint", None)[sample % 6]
            image, truth = sheet(6000 + writer_index * 100 + sample, layout=0,
                                 stress=condition, digit_renderer=draw)
            for row_index, row in enumerate(truth["rows"], 1):
                y = top + row_index * step + 15
                for start, sequence in ((left+35, row["sku"]), (middle+42, row["quantity"])):
                    for offset, digit in enumerate(sequence):
                        x = start + offset*38
                        crop = image.crop((x-4, y-5, x+34, y+42))
                        for mask in (ink(crop), ink(crop, relaxed=True), enhanced_mask(crop)):
                            if np.count_nonzero(mask) > 18:
                                yield mask, int(digit)
