import csv
from io import StringIO

from .review import reconcile


def records(report):
    return {
        "schema_version": 1, "catalogue_version": report["catalogue"]["version"],
        "reconciliation": reconcile(report),
        "approved": [{"row": row["id"], **row["verified"]} for row in report["rows"] if row["verified"]],
        "unresolved_rows": [row["id"] for row in report["rows"] if not row["verified"]],
    }


def as_csv(report):
    stream = StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=["row", "sku", "quantity"])
    writer.writeheader()
    writer.writerows(records(report)["approved"])
    return stream.getvalue()
