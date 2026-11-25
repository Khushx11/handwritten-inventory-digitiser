# Handwritten Inventory Sheet Digitiser

Portfolio by [Khush Bhavin Maru](https://github.com/Khushx11) · Adelaide University MAAIM.

Turn ruled stocktake sheets into source-linked inventory records. Upload a photo, inspect each recognised SKU and count beside its source crop, then correct and approve the rows you want to export.


## Review a row against its source

[![Stocktake workspace showing an unreadable count beside its source crop](docs/demo/preview.png)](https://raw.githubusercontent.com/Khushx11/handwritten-inventory-digitiser/main/docs/demo/walkthrough.mp4)

| What the reviewer sees | What to check before export |
| --- | --- |
| Recognised SKU and count | Compare both values with the linked source crop. |
| Unreadable or incorrect count | Correct the row from the source when the value is legible. |
| Approved rows | Export the reviewed records as CSV or JSON. |

[Watch the 66-second walkthrough](https://raw.githubusercontent.com/Khushx11/handwritten-inventory-digitiser/main/docs/demo/walkthrough.mp4).

The recorded walkthrough shows the earlier workspace layout. The current version uses the same source-linked review and export workflow.

## Run locally

Use Python 3.11–3.13.

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install .
inventory-digitiser-setup
```

Open <http://127.0.0.1:8013>. The first setup downloads checksum-verified MNIST and PenDigits archives and trains both checkpoints locally. Later launches reuse verified weights and start the same conservative review mode. Use `inventory-digitiser` for an immediate offline preview with the bundled baseline on port 8010.

### Review a sheet

1. Choose **Load labelled example** or upload a PNG, JPEG or WebP up to 10 MB. Sheets need two ruled columns, a header and a final total row. The total cell may be blank. Correct orientation or perspective before extraction.
2. Select a row to inspect its aligned cell crops. The original scan remains available alongside the corrected view. If the models disagree, the UI shows both readings and leaves the disputed field empty. Each new sheet records the model identifiers used.
3. Correct and approve each count, or exclude a blank, crossed-out or duplicate row with a reason. Any exclusion can be reopened. The app allows one approved row per SKU per sheet. If repeated counts represent distinct stock, reconcile them against the source and record the decision before approving one combined count and excluding the component rows.
4. Confirm the printed total where available, then export. Filenames and CSV records distinguish **partial**, **unreconciled**, **mismatch** and **reconciled** states. A total mismatch requires explicit confirmation for the current sheet revision. JSON includes unresolved and excluded row IDs, exclusion reasons and model identifiers.

All scans and review history stay in the local workspace under `runtime/` by default. CSV preserves SKU strings on disk. When importing into a spreadsheet, select text for SKU so that leading zeros survive.

## What the benchmark found

- **52.8% exact row accuracy** on 72 clean rows rendered from six held-out UCI writers across two layouts excluded from development. Cell-first and page-first tied on accuracy.
- **12 of 72 clean rows** passed the simulated review threshold at 0.80, with no errors among those 12. On skewed sheets, two incorrect quantities passed at that same threshold.
- Synthetic sheets composed entirely of procedural ink are measured separately. The app requires human approval before exporting any record.

The evaluator matches detections by source geometry. Missing reference rows and extra detections both count against accuracy. See the [evaluation protocol and measured results](docs/evaluation.md) and [data provenance and attribution](docs/data.md).

```sh
python -m inventory.evaluate --output docs/metrics.json
curl --fail --location 'https://archive.ics.uci.edu/static/public/160/uji+pen+characters.zip' -o /tmp/uji-pen.zip
python -m inventory.writer_benchmark /tmp/uji-pen.zip --output docs/writer-metrics.json
python -m unittest discover -s tests -v
```

## Additional handwriting model

The optional MNIST and PenDigits model scored **97.46%** and **93.40%** on their respective official test partitions. It reached **86.1% exact row accuracy** on the same clean writer-held-out stocktake composites. The benchmark still found wrong quantities above the simulated acceptance threshold. [Results and training instructions](docs/additional-handwriting.md)

## Difficult scans

Try **Blurred photo**, **Faint handwriting** or **Crowded digits** from the example selector. The app shows scan-quality warnings and flags faint recovered readings for review. An optional degradation-trained model improved exact rows in the paired blur tests. For difficult scans, enable the second-model check and conservative review policy. [Stress results and reproduction](docs/difficult-scans.md)

## Touching digits and real photographs

Conservative mode can propose a catalogue SKU when handwriting components touch. Reviewers still enter the verified SKU from the crop. The crowded benchmark produced **38 correct proposals out of 42**. A new sheet-adapted model performed worse on severe blur, so the existing augmented model remains in service. [Crowded and blurred results, external dataset and private photo benchmark](docs/touching-digits-and-real-photos.md)

## Design

- **Alignment and extraction** use bounded image decoding, manual corner correction, deskew, ruled-grid detection and offline digit classification.
- **Review** flags uncertain reads, unknown SKUs, blanks, unreadable marks and duplicate candidates. Suggestions never replace the raw OCR. Explicit edits and reopening events are recorded with their previous values.
- **Reconciliation** compares an OCR-read printed total with the sum of approved quantities once all rows are resolved. Reviewers can confirm a printed total separately and preserve the original OCR reading. An uncertain or missing total stays unknown until confirmed. The total never fills a missing quantity.
- **Storage** uses SQLite for approval history and the local filesystem for scans. The HTTP server binds to loopback. Use the demo locally with non-sensitive images.

The current model supports digits and a documented two-column format. Real-world sheet accuracy is unverified. The benchmark uses stylus strokes composited onto generated tables, so its metrics should guide review design rather than stock-control decisions.
