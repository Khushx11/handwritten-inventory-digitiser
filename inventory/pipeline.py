from .baseline import page_reader
from .grid import cell_boxes, deskew, detect
from .matching import catalogue, suggestions
from .recognise import cell, printed_total


def extract(image, strategy="cell"):
    if strategy not in {"cell", "page"}:
        raise ValueError("Choose cell or page recognition.")
    aligned = deskew(image)
    x, y = detect(aligned)
    boxes, total_box = cell_boxes(x, y)
    read = page_reader(aligned, x, y) if strategy == "page" else lambda box, expected=None: cell(aligned, box, expected)
    reference = catalogue()
    rows = []
    for index, (sku_box, count_box) in enumerate(boxes, 1):
        sku = read(sku_box, 4)
        count = read(count_box)
        rows.append({
            "id": index, "sku": sku, "count": count, "boxes": [sku_box, count_box],
            "suggestions": suggestions(sku["raw"], reference["items"]),
        })
    return aligned, {"rows": rows, "total": printed_total(aligned, total_box), "total_box": total_box,
                     "catalogue": reference, "strategy": strategy}


def reasons(row, items, cutoff):
    result = []
    if row["sku"]["raw"] not in items:
        result.append("Unknown or ambiguous SKU")
    for key, name in (("sku", "SKU"), ("count", "Quantity")):
        field = row[key]
        if field["state"] != "recognised":
            result.append(f"{name} {field['state']}")
        elif field["confidence"] < cutoff:
            result.append(f"Low-confidence {name}")
    return result
