"""Page-first baseline: segment all glyphs before assigning table cells."""
from .grid import ink
from .recognise import components, recognise


def page_reader(image, x, y):
    mask = ink(image)
    for line in x:
        mask[:, max(0, line-3):line+4] = False
    for line in y:
        mask[max(0, line-3):line+4, :] = False
    marks = components(mask)

    def read(box, expected=None):
        left, top, right, bottom = box
        parts = [part for part in marks if left <= (part[0]+part[2])/2 < right
                 and top <= (part[1]+part[3])/2 < bottom]
        return recognise(parts, width=right-left, expected=expected)

    return read
