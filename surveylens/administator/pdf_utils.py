from playwright.sync_api import sync_playwright
import tempfile
import os

def html_to_pdf_bytes(html: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        html_path = os.path.join(tmpdir, "report.html")
        pdf_path = os.path.join(tmpdir, "report.pdf")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(f"file://{html_path}", wait_until="networkidle")
            # Wait until Chart.js has rendered
            try:
                page.wait_for_function("() => window.__chartsReady === true", timeout=10000)
            except Exception:
                pass
            page.pdf(path=pdf_path, format="A4", print_background=True)
            browser.close()

        with open(pdf_path, "rb") as f:
            return f.read()
