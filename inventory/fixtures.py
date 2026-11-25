"""Deterministic synthetic stocktake sheets with labelled stroke styles."""
import random

from PIL import Image, ImageDraw, ImageFilter, ImageOps

from .matching import catalogue

STROKES = {
 "0": [[(4,0),(11,1),(14,6),(13,19),(9,24),(3,23),(0,16),(1,5),(4,0)]],
 "1": [[(2,5),(7,0),(7,24)],[(2,24),(13,24)]],
 "2": [[(0,5),(4,0),(10,0),(14,4),(13,9),(1,23),(14,23)]],
 "3": [[(0,2),(8,0),(14,4),(10,10),(6,11),(12,12),(14,17),(11,23),(5,24),(0,21)]],
 "4": [[(10,0),(0,16),(15,16)],[(11,1),(11,24)]],
 "5": [[(14,0),(2,0),(0,11),(9,10),(14,14),(13,20),(9,24),(3,23),(0,21)]],
 "6": [[(13,0),(8,1),(2,8),(0,17),(3,23),(9,24),(14,19),(13,14),(9,11),(2,13)]],
 "7": [[(0,1),(14,0),(11,7),(8,14),(5,24)]],
 "8": [[(7,10),(1,7),(2,2),(7,0),(13,2),(14,6),(7,10),(1,15),(0,20),(4,24),(10,24),(14,20),(13,15),(7,10)]],
 "9": [[(13,11),(7,13),(2,10),(1,4),(6,0),(12,2),(14,8),(12,18),(7,24),(3,24)]],
}
LAYOUTS = [(700,650,54,270,648,62,66), (760,680,68,342,691,77,62), (720,650,40,315,681,74,60)]


def sheet(seed=1, style=0, layout=0, stress=None, digit_renderer=None):
    rng = random.Random(seed)
    width, height, left, middle, right, top, step = LAYOUTS[layout]
    image = Image.new("RGB", (width, height), "#fdfcf8")
    draw = ImageDraw.Draw(image)
    draw.text((left, top - 34), "STOCKROOM / INVENTORY COUNT", fill="#14232a")
    items = rng.sample(list(catalogue()["items"]), 6)
    counts = [str(rng.randint(0, 39)) for _ in items]
    counts[0] = "0"
    counts[2] = ""
    rows = list(zip(items, counts))
    for i in range(len(rows)+3):
        line = top+i*step
        draw.line((left, line, right, line), fill="#24343b", width=3)
    for x in (left, middle, right):
        draw.line((x, top, x, top+(len(rows)+2)*step), fill="#24343b", width=3)
    draw.text((left+15, top+22), "ITEM ID", fill="#14232a")
    draw.text((middle+15, top+22), "QUANTITY", fill="#14232a")
    draw.text((left+15, top+(len(rows)+1)*step+22), "TOTAL OF FILLED COUNTS", fill="#14232a")

    def digits(text, x, y, crossed=False):
        start = x
        slant = (-0.18, 0.11, 0.26, -0.08)[style]
        for digit in text:
            if digit_renderer is not None:
                digit_renderer(draw, digit, x, y, rng)
                x += 38
                continue
            for stroke in STROKES[digit]:
                points = [(round(x+2*(a+b*slant)+rng.uniform(-0.7,0.7)),
                           round(y+1.38*b+rng.uniform(-0.9,0.9))) for a,b in stroke]
                draw.line(points, fill="#1a3043", width=4+(style % 2), joint="curve")
            x += 38 + rng.randint(-1, 2)
        if crossed and text:
            draw.line((start-7,y+11,x,y+21), fill="#24343b", width=5)

    for i,(sku,count) in enumerate(rows,1):
        digits(sku,left+35,top+i*step+15)
        digits(count,middle+42,top+i*step+15,stress == "crossed-out" and i == 4)
    total = sum(int(value) for value in counts if value)
    draw.text((middle+45,top+(len(rows)+1)*step+15),str(total),font_size=31,fill="#24343b")
    if stress == "blur":
        image = image.filter(ImageFilter.GaussianBlur(1.6))
    elif stress == "skew":
        image = image.rotate(5, resample=Image.Resampling.BICUBIC, fillcolor="#fdfcf8")
    elif stress == "shadow":
        shade = Image.new("L", (width, height))
        shade.putdata([max(105, min(255, 70+int(x/width*260))) for x in range(width)]*height)
        image = Image.composite(image, ImageOps.colorize(image.convert("L"), "#11161d", "#a4acb4"), shade)
    return image, {"rows": [{"sku":sku,"quantity":count,"crossed_out":stress == "crossed-out" and i == 4}
                            for i,(sku,count) in enumerate(rows,1)], "printed_total":total,
                   "style":style,"layout":layout,"stress":stress or "clean"}
