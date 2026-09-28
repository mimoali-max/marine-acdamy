"""
AASTMT — QA harness.

Loads http://127.0.0.1:5000 in headless Chromium, exercises the UI,
fills the admission form, and verifies the application was accepted.
Captures a screenshot and console errors for inspection.
"""
import json
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:5000/"
OUT = Path(__file__).resolve().parent
SHOT = OUT / "screenshot.png"
SHOT_FULL = OUT / "screenshot_full.png"
REPORT = OUT / "qa_report.json"


def main() -> int:
    console_errors = []
    failed_requests = []

    # The playwright headless_shell variant is not downloaded; point at the
    # full chromium binary that IS installed.
    chromium_path = (
        Path.home() / "AppData" / "Local" / "ms-playwright" /
        "chromium-1234" / "chrome-win64" / "chrome.exe"
    )

    with sync_playwright() as p:
        launch_kwargs = {"headless": True}
        if chromium_path.exists():
            launch_kwargs["executable_path"] = str(chromium_path)
        browser = p.chromium.launch(**launch_kwargs)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        def on_console(msg):
            if msg.type in ("error", "warning"):
                console_errors.append(f"{msg.type}: {msg.text}")

        def on_failed(r):
            failed_requests.append(f"{r.method} {r.url} :: {r.failure}")

        page.on("console", on_console)
        page.on("requestfailed", on_failed)

        print("navigating to " + URL)
        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_selector(".hero h1", timeout=15000)
        page.wait_for_function(
            "document.querySelectorAll('.college').length >= 8",
            timeout=10000,
        )

        title = page.title()
        hero_h1 = page.locator(".hero h1").first.inner_text().strip()
        nav_link_count = page.locator(".nav-links a").count()
        college_count = page.locator(".college").count()
        compare_rows = page.locator(".compare-row").count()
        form_fields = page.locator(
            "#applyForm input, #applyForm select, #applyForm textarea"
        ).count()
        term_lines = page.locator("#termBody > div").count()
        body_chars = len(page.content())

        page.screenshot(path=str(SHOT), full_page=False)
        page.screenshot(path=str(SHOT_FULL), full_page=True)

        # Drive the admission form
        page.locator("#firstName").fill("QA")
        page.locator("#lastName").fill("Bot")
        page.locator("#email").fill("qa-bot@aastmt.test")
        page.locator("#phone").fill("+20 100 000 1234")
        page.locator("#country").select_option("Egypt")
        page.wait_for_function(
            "document.getElementById('college').options.length > 1", timeout=10000
        )
        page.locator("#college").select_option(index=1)
        page.locator("#message").fill("Automated QA submission via Playwright.")
        page.locator("#applyForm button[type=submit]").click()

        page.wait_for_selector(".form-status.ok", timeout=15000)
        form_status = page.locator(".form-status.ok").inner_text().strip()

        page.locator("#admission").scroll_into_view_if_needed()
        time.sleep(0.3)

        result = {
            "ok": True,
            "url": URL,
            "title": title,
            "hero_h1": hero_h1,
            "nav_link_count": nav_link_count,
            "college_count": college_count,
            "compare_rows": compare_rows,
            "form_fields": form_fields,
            "terminal_lines": term_lines,
            "body_chars": body_chars,
            "form_submit_status": form_status,
            "console_errors": console_errors,
            "failed_requests": failed_requests,
            "screenshot": str(SHOT),
            "screenshot_full": str(SHOT_FULL),
        }

        REPORT.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
