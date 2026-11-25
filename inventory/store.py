import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .review import approve


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db = self.directory / "stocktake.sqlite3"
        with self.connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS sheets (id TEXT PRIMARY KEY, report TEXT NOT NULL)")
            connection.execute("""CREATE TABLE IF NOT EXISTS history
                               (sequence INTEGER PRIMARY KEY, sheet TEXT, event TEXT NOT NULL)""")

    def connect(self):
        return sqlite3.connect(self.db, timeout=10)

    def add(self, image, report, *, original=None):
        sheet = uuid4().hex
        target = self.directory / (sheet + ".png")
        source = self.directory / (sheet + "-original.png")
        try:
            image.save(target)
            if original is not None:
                original.save(source)
            with self.connect() as connection:
                connection.execute("INSERT INTO sheets VALUES (?, ?)", (sheet, json.dumps(report)))
        except Exception:
            target.unlink(missing_ok=True)
            source.unlink(missing_ok=True)
            raise
        return sheet

    @staticmethod
    def read(connection, sheet):
        result = connection.execute("SELECT report FROM sheets WHERE id = ?", (sheet,)).fetchone()
        if result is None:
            raise KeyError("Sheet not found.")
        return json.loads(result[0])

    def get(self, sheet):
        with self.connect() as connection:
            report = self.read(connection, sheet)
            report["history"] = [json.loads(event) for (event,) in connection.execute(
                "SELECT event FROM history WHERE sheet = ? ORDER BY sequence", (sheet,))]
        return report

    def update(self, sheet, row_id, sku, quantity, revision, action):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            report = self.read(connection, sheet)
            if revision != report.get("revision", 0):
                raise ValueError("This sheet changed. Reload before making another edit.")
            row = next((row for row in report["rows"] if row["id"] == row_id), None)
            if row is None:
                raise KeyError("Row not found.")
            before = row["verified"]
            if action == "reopen":
                row["verified"] = None
            elif action == "approve":
                approve(report, row, sku, quantity)
            else:
                raise ValueError("Unknown review action.")
            report["revision"] = revision + 1
            event = {"row": row_id, "action": action, "before": before, "after": row["verified"],
                     "time": datetime.now(timezone.utc).isoformat()}
            connection.execute("UPDATE sheets SET report = ? WHERE id = ?", (json.dumps(report), sheet))
            connection.execute("INSERT INTO history (sheet, event) VALUES (?, ?)", (sheet, json.dumps(event)))
        return self.get(sheet)
