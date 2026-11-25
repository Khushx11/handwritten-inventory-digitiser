"""Exercise the complete browser review path against a running local app."""
import argparse
import csv
from io import StringIO
from pathlib import Path
from time import sleep

from playwright.sync_api import expect, sync_playwright


def caption(page, text, seconds, record):
    if not record:
        return
    page.evaluate("""text => {
      let panel = document.getElementById('demo-caption');
      if (!panel) {
        panel = document.createElement('aside');
        panel.id = 'demo-caption';
        panel.style.cssText = 'position:fixed;bottom:18px;left:18px;right:18px;z-index:99;padding:15px 20px;border-radius:9px;background:#15332d;color:#fff;font:600 21px/1.35 system-ui;pointer-events:none';
        document.body.append(panel);
      }
      panel.textContent = text;
    }""", text)
    sleep(seconds)


def run(url, record):
    root = Path(__file__).resolve().parents[1]
    with sync_playwright() as runner:
        browser = runner.chromium.launch()
        options = {"viewport": {"width": 1280, "height": 900}, "accept_downloads": True}
        if record:
            options.update(record_video_dir=record, record_video_size=options["viewport"], bypass_csp=True)
        context = browser.new_context(**options)
        page = context.new_page()
        page.goto(url)
        expect(page.get_by_role("heading", name="Verify a stocktake sheet")).to_be_visible()
        caption(page, "Upload a ruled stocktake sheet to extract handwritten item IDs and quantities.", 11, record)
        page.locator("#file").set_input_files(root / "examples/ambiguous.png")
        page.get_by_role("button", name="Extract counts").click()
        expect(page.get_by_text("Extraction complete", exact=False)).to_be_visible(timeout=30_000)
        caption(page, "The sheet is aligned and recognised locally. Each row retains its OCR output and source cells.", 11, record)
        page.get_by_label("Flagged only").check()
        target = page.get_by_role("button", name="Row 4", exact=False)
        expect(target).to_contain_text("unreadable")
        if record:
            target.scroll_into_view_if_needed()
        target.focus()
        target.press("Enter")
        expect(page.get_by_role("img", name="Quantity source crop")).to_be_visible()
        if record:
            page.locator("#review").scroll_into_view_if_needed()
        caption(page, "The crossed-out quantity is unreadable. Select the flagged row to inspect both source crops.", 14, record)
        page.get_by_label("Quantity", exact=True).fill("13")
        caption(page, "A reviewer confirms the correct count before approving it. The system retains the original OCR reading.", 12, record)
        page.get_by_role("button", name="Approve row").click()
        expect(page.get_by_text("Row approved.", exact=True)).to_be_visible()
        page.get_by_label("Printed total", exact=True).fill("80")
        page.get_by_role("button", name="Confirm total", exact=True).click()
        expect(page.get_by_text("Confirmed total 80", exact=False)).to_be_visible()
        page.get_by_role("link", name="Export CSV").scroll_into_view_if_needed()
        with page.expect_download() as download:
            page.get_by_role("link", name="Export CSV").click()
        rows = list(csv.DictReader(StringIO(download.value.path().read_text())))
        assert download.value.suggested_filename == "stocktake-partial.csv"
        assert len(rows) == 1 and rows[0]["export_status"] == "partial", rows
        assert [rows[0][key] for key in ("row", "sku", "quantity")] == ["4", "0642", "13"], rows
        if not record:
            page.get_by_role("button", name="Row 3", exact=False).click()
            page.get_by_label("Exclusion reason").fill("Blank line confirmed against source")
            page.get_by_role("button", name="Exclude row").click()
            expect(page.get_by_text("Row excluded.", exact=True)).to_be_visible()
        caption(page, "Export contains the approved count. Unresolved rows remain visible in the workspace and JSON export.", 15, record)
        page.reload()
        expect(page.get_by_text("5 unresolved" if record else "4 unresolved", exact=False)).to_be_visible()
        expect(page.get_by_text("Confirmed total 80", exact=False)).to_be_visible()
        if not record:
            page.get_by_label("Flagged only").uncheck()
            for number in (1, 2, 5, 6):
                page.get_by_role("button", name=f"Row {number}", exact=False).click()
                page.get_by_label("Exclusion reason").fill("Synthetic mismatch test: deliberately omit this row")
                page.get_by_role("button", name="Exclude row").click()
                expect(page.get_by_text("Row excluded.", exact=True)).to_be_visible()
            expect(page.get_by_text("Export: mismatch", exact=False)).to_be_visible()
            csv_link = page.get_by_role("link", name="Export CSV")
            href = csv_link.get_attribute("href")
            assert href
            blocked = page.request.get(url.rstrip("/") + href)
            assert blocked.status == 409
            assert page.request.get(url.rstrip("/") + href + "?confirm_revision=0").status == 409
            page.once("dialog", lambda dialog: dialog.accept())
            with page.expect_download() as confirmed:
                csv_link.click()
            assert confirmed.value.suggested_filename == "stocktake-mismatch.csv"
            row = next(csv.DictReader(StringIO(confirmed.value.path().read_text())))
            assert row["export_status"] == "mismatch" and row["total_difference"] == "-67"
            page.get_by_label("Example condition").select_option("heavy-blur")
            page.get_by_role("button", name="Load labelled example").click()
            expect(page.get_by_text("Soft edges detected.", exact=False)).to_be_visible(timeout=20_000)
        video = page.video
        context.close()
        if record and video:
            video.save_as(record / "walkthrough.webm")
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8010")
    parser.add_argument("--record", type=Path)
    cfg = parser.parse_args()
    run(cfg.url, cfg.record)
