"""Loopback-only inventory review application."""
import argparse
import base64
import binascii
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from io import BytesIO
import json
from pathlib import Path
import re

from .export import as_csv, records
from .fixtures import sheet
from .geometry import decode, rectify
from .image_quality import assess
from .pipeline import extract
from .review import prepare, reconcile
from .store import Store

ASSETS = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"),
          "/style.css": ("style.css", "text/css")}
SHEET = re.compile(r"/api/sheets/([a-f0-9]{32})(?:/(image|original|review|json|csv))?")
LIMIT = 15_000_000
EXAMPLES = {"crossed-out", "blur", "heavy-blur", "faint", "crowded", "shadow", "low-resolution"}


def png(image):
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def handler_for(store, classifier=None):
    class Handler(BaseHTTPRequestHandler):
        def send(self, content, kind, status=HTTPStatus.OK, filename=None):
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' blob: data:; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(content)

        def json(self, data, status=HTTPStatus.OK, filename=None):
            self.send(json.dumps(data, allow_nan=False).encode(), "application/json", status, filename)

        def report(self, sheet_id, report):
            return {"sheet": sheet_id, "report": report, "reconciliation": reconcile(report)}

        def do_GET(self):
            try:
                if self.path in ASSETS:
                    name, content_type = ASSETS[self.path]
                    self.send(files("inventory").joinpath("web", name).read_bytes(), content_type+"; charset=utf-8")
                elif self.path == "/api/example":
                    self.send(png(sheet(stress="crossed-out")[0]), "image/png")
                elif self.path.startswith("/api/example/"):
                    condition = self.path.removeprefix("/api/example/")
                    if condition not in EXAMPLES:
                        raise KeyError("Example not found.")
                    self.send(png(sheet(stress=condition)[0]), "image/png")
                elif match := SHEET.fullmatch(self.path):
                    sheet_id, action = match.groups()
                    report = store.get(sheet_id)
                    if action in {"image", "original"}:
                        ending = ".png" if action == "image" else "-original.png"
                        self.send((store.directory / (sheet_id + ending)).read_bytes(), "image/png")
                    elif action == "json":
                        self.json(records(report), filename="stocktake.json")
                    elif action == "csv":
                        self.send(as_csv(report).encode(), "text/csv; charset=utf-8", filename="stocktake.csv")
                    elif action is None:
                        self.json(self.report(sheet_id, report))
                    else:
                        raise KeyError("Endpoint not found.")
                else:
                    raise KeyError("Endpoint not found.")
            except (KeyError, FileNotFoundError) as error:
                self.json({"error": str(error)}, HTTPStatus.NOT_FOUND)

        def do_POST(self):
            if self.headers.get("Origin") not in (None, f"http://127.0.0.1:{self.server.server_port}",
                                                   f"http://localhost:{self.server.server_port}"):
                self.json({"error": "Request origin is outside this local workspace."}, HTTPStatus.FORBIDDEN)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= LIMIT:
                    raise ValueError("Upload is empty or exceeds 15 MB.")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Expected an object.")
                if self.path == "/api/sheets":
                    original = decode(base64.b64decode(data["image"], validate=True))
                    rotation = data.get("rotation", 0)
                    if rotation not in (0, 90, 180, 270):
                        raise ValueError("Unsupported rotation.")
                    working = rectify(original, data["corners"]) if data.get("corners") else original
                    working = working.rotate(rotation, expand=True) if rotation else working
                    quality = assess(working)
                    try:
                        aligned, report = extract(working, data.get("strategy", "cell"), classifier=classifier)
                    except ValueError as error:
                        if quality["warnings"]:
                            raise ValueError(f"{error} {' '.join(quality['warnings'])}") from error
                        raise
                    report["scan_quality"] = quality
                    sheet_id = store.add(aligned, prepare(report), original=original)
                    self.json(self.report(sheet_id, store.get(sheet_id)), HTTPStatus.CREATED)
                elif (match := SHEET.fullmatch(self.path)) and match[2] == "review":
                    report = store.update(match[1], data["row"], data.get("sku"), data.get("quantity"),
                                          data["revision"], data["action"])
                    self.json(self.report(match[1], report))
                else:
                    self.json({"error": "Endpoint not found."}, HTTPStatus.NOT_FOUND)
            except (ValueError, KeyError, TypeError, binascii.Error) as error:
                self.json({"error": str(error)}, HTTPStatus.BAD_REQUEST)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--workspace", type=Path, default=Path("runtime"))
    parser.add_argument("--model", type=Path, help="Optional locally trained numeric MLP weights")
    parser.add_argument("--comparison-model", type=Path, help="Optional second checkpoint for disagreement review")
    args = parser.parse_args()
    from .portable_model import CrossCheckedMLP, PortableMLP
    if args.comparison_model and not args.model:
        parser.error("--comparison-model requires --model")
    classifier = None
    if args.comparison_model:
        classifier = CrossCheckedMLP(args.model, args.comparison_model)
    elif args.model:
        classifier = PortableMLP(args.model)
    with ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(Store(args.workspace), classifier)) as server:
        print(f"Open http://127.0.0.1:{server.server_port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
