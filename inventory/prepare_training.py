"""Derive annotated training strokes from UCI development writers only."""
import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

from .writer_benchmark import ARCHIVE_SHA256, parse_writer


def build(archive):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("Unexpected UCI source archive.")
    with ZipFile(archive) as source:
        writers = {f"w{i:02}": parse_writer(source.read(f"UJIpenchars-w{i:02}").decode("latin-1"))
                   for i in range(1, 6)}
    return {"archive_sha256": ARCHIVE_SHA256, "writers": writers}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(build(args.archive), separators=(",", ":")) + "\n")
