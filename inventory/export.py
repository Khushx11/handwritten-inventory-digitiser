import csv
from io import StringIO

from .review import reconcile


def status(reconciliation):
    if reconciliation["unresolved"]:
        return "partial"
    if reconciliation["difference"] is None:
        return "unreconciled"
    return "mismatch" if reconciliation["difference"] else "reconciled"


def records(report):
    reconciliation = reconcile(report)
    return {
        "schema_version": 2, "catalogue_version": report["catalogue"]["version"],
        "export_status": status(reconciliation),
        "reconciliation": reconciliation,
        "models": report.get("models"),
        "approved": [{"row": row["id"], **row["verified"]} for row in report["rows"] if row["verified"]],
        "excluded_rows": [{"row": row["id"], "reason": row["exclusion_reason"]}
                          for row in report["rows"] if row.get("exclusion_reason")],
        "unresolved_rows": [row["id"] for row in report["rows"]
                            if not row["verified"] and not row.get("exclusion_reason")],
    }


def as_csv(report):
    payload = records(report)
    reconciliation = payload["reconciliation"]
    stream = StringIO(newline="")
    columns = ["row", "sku", "quantity", "export_status", "unresolved_rows", "excluded_rows", "total_difference"]
    writer = csv.DictWriter(stream, fieldnames=columns)
    writer.writeheader()
    for row in payload["approved"]:
        writer.writerow({**row, "export_status": payload["export_status"],
                         "unresolved_rows": reconciliation["unresolved"],
                         "excluded_rows": reconciliation["excluded"],
                         "total_difference": reconciliation["difference"]})
    return stream.getvalue()
