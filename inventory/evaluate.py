"""Evaluate extraction and review coverage on a frozen synthetic protocol."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from time import perf_counter

from .fixtures import sheet
from .matching import distance
from .pipeline import extract
from .recognise import model
from .review import prepare

CUTOFFS = (0.55, 0.70, 0.80, 0.90, 0.99)


def evaluate():
    model()  # Exclude the once-per-process model fit from warm inference times.
    records = []
    for strategy in ("page", "cell"):
        for split, styles, layouts, seed_start in (("development", (0,1), (0,), 10), ("held_out", (2,3), (1,2), 40)):
            for style in styles:
                for layout in layouts:
                    for offset, stress in enumerate((None, "blur", "shadow", "skew", "crossed-out")):
                        image, expected = sheet(seed_start+offset, style, layout, stress)
                        start = perf_counter()
                        try:
                            _, result = extract(image, strategy)
                        except ValueError:
                            result = {"rows": [], "catalogue": {"items": {}}}
                        duration = (perf_counter()-start)*1000
                        observed = result["rows"]
                        for index, truth in enumerate(expected["rows"]):
                            row = observed[index] if index < len(observed) else None
                            sku = row["sku"]["raw"] if row else ""
                            qty = row["count"]["raw"] if row else ""
                            qty_ok = qty == truth["quantity"] and (truth["quantity"] != "" or bool(row and row["count"]["state"] == "blank"))
                            accepted = []
                            for cutoff in CUTOFFS:
                                if row and not prepare(result, cutoff)["rows"][index]["flags"]:
                                    accepted.append(cutoff)
                            records.append({"strategy":strategy,"split":split,"condition":expected["stress"],
                                            "style":style,"layout":layout,"sheet_seed":seed_start+offset,"row":index+1,
                                            "aligned":len(observed)==len(expected["rows"]),
                                            "sku_exact":sku==truth["sku"],"quantity_exact":qty_ok,
                                            "crossed_out":truth["crossed_out"],"policy_safe":qty_ok and not truth["crossed_out"],
                                            "accepted_at":accepted,"character_errors":distance(sku,truth["sku"])+distance(qty,truth["quantity"]),
                                            "characters":len(truth["sku"])+len(truth["quantity"]),"sheet_ms":round(duration,3)})
    return {"dataset":"Synthetic procedural strokes and layouts; no real writer identities or inventory records.",
            "thresholds":list(CUTOFFS),"rows":records,"summary":summarise(records)}


def summarise(records):
    groups = defaultdict(list)
    for row in records:
        groups[row["strategy"], row["split"], row["condition"]].append(row)
    summary = []
    for (strategy, split, condition), rows in sorted(groups.items()):
        n = len(rows)
        risks = []
        for cutoff in CUTOFFS:
            accepted = [r for r in rows if cutoff in r["accepted_at"]]
            wrong_quantity = sum(not row["quantity_exact"] for row in accepted)
            errors = sum(not (row["sku_exact"] and row["policy_safe"]) for row in accepted)
            risks.append({"threshold":cutoff,"accepted":len(accepted),"review_rate":1-len(accepted)/n,
                          "accepted_row_error":errors/len(accepted) if accepted else None,
                          "wrong_quantities_accepted":wrong_quantity})
        summary.append({"strategy":strategy,"split":split,"condition":condition,"rows":n,
                        "character_error_rate":sum(row["character_errors"] for row in rows)/sum(row["characters"] for row in rows),
                        "exact_sku_rate":sum(row["sku_exact"] for row in rows)/n,
                        "exact_quantity_rate":sum(row["quantity_exact"] for row in rows)/n,
                        "exact_row_rate":sum(row["sku_exact"] and row["quantity_exact"] for row in rows)/n,
                        "row_alignment_rate":sum(row["aligned"] for row in rows)/n,
                        "mean_sheet_ms":sum(row["sheet_ms"] for row in rows)/n,"risk_coverage":risks})
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("docs/metrics.json"))
    args = parser.parse_args()
    args.output.write_text(json.dumps(evaluate(), indent=2, allow_nan=False) + "\n")
