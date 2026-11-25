"""Render the measured review trade-off from checked-in writer metrics."""
import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


def render(report, output):
    summaries = [row for row in report["summary"]
                 if row["strategy"] == "cell" and row["split"] == "held_out"]
    figure, (risk_axis, count_axis) = plt.subplots(1, 2, figsize=(10.5, 4.2), layout="constrained")
    colours = {"clean": "#09665b", "skew": "#a53b25"}
    report_by_condition = {row["condition"]: row for row in summaries}
    for condition, colour in colours.items():
        row = report_by_condition[condition]
        points = [point for point in row["risk_coverage"] if point["accepted"]]
        x = [point["review_rate"] for point in points]
        risk_axis.plot(x, [point["accepted_row_error"] for point in points], "o-", color=colour, label=condition.title())
        count_axis.plot(x, [point["wrong_quantities_accepted"] for point in points], "o-", color=colour, label=condition.title())
        default = next(point for point in points if point["threshold"] == 0.8)
        risk_axis.annotate(
            f'{default["accepted"]} accepted at 0.80',
            (default["review_rate"], default["accepted_row_error"]),
            xytext=(-116, 12), textcoords="offset points", color=colour, fontsize=8,
        )
    risk_axis.set(title="Error among accepted rows", ylabel="Incorrect or unsafe rows")
    risk_axis.yaxis.set_major_formatter(PercentFormatter(1))
    count_axis.set(title="Incorrect quantities that passed", ylabel="Wrong quantities")
    count_axis.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    for axis in (risk_axis, count_axis):
        axis.set_xlabel("Rows routed to review")
        axis.xaxis.set_major_formatter(PercentFormatter(1))
        axis.grid(alpha=0.22)
        axis.legend(frameon=False)
    figure.suptitle("Held-out writer benchmark | Cell-first extraction", fontweight="bold")
    figure.savefig(output, dpi=160, facecolor="white")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("docs/writer-metrics.json"))
    parser.add_argument("--output", type=Path, default=Path("docs/review-tradeoff.png"))
    args = parser.parse_args()
    render(json.loads(args.input.read_text()), args.output)
