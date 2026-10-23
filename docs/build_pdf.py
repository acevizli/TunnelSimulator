"""Turns docs/write-up.md into docs/write-up.pdf (A4), printed by the installed Google Chrome.

    uv run --with markdown --with playwright python docs/build_pdf.py
"""

from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

DOCS = Path(__file__).resolve().parent

STYLE = """
@page { size: A4; margin: 12mm 14mm; }
body { font: 8.6pt/1.36 -apple-system, "Helvetica Neue", Arial, sans-serif; color: #111; }
h1 { font-size: 14pt; margin: 0 0 3pt; }
h2 { font-size: 10pt; margin: 8pt 0 2pt; border-bottom: 0.5pt solid #bbb; break-after: avoid; }
p, ul, ol { margin: 2pt 0; }
ul, ol { padding-left: 13pt; }
li { margin: 1pt 0; }
a { color: #1d4ed8; text-decoration: none; }
code { font-size: 8pt; }
table { border-collapse: collapse; margin: 3pt 0; width: 100%; break-inside: avoid; }
th, td { border-bottom: 0.5pt solid #ddd; padding: 1.2pt 5pt; text-align: left; }
th { border-bottom: 0.8pt solid #888; }
img { width: 100%; margin-top: 5pt; }
p:has(> img) { margin: 4pt 0; font-size: 7.6pt; color: #444; }
"""


def main() -> None:
    body = markdown.markdown((DOCS / "write-up.md").read_text(), extensions=["tables"])
    html = f'<!doctype html><meta charset="utf-8"><style>{STYLE}</style>{body}'
    page_file = DOCS / "_write-up.html"
    page_file.write_text(html)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome")
            page = browser.new_page()
            page.goto(page_file.as_uri())
            # The picture's alt text doubles as its caption
            page.evaluate("""() => document.querySelectorAll('p > img').forEach(img => {
                const caption = document.createElement('div'); caption.textContent = img.alt;
                img.after(caption); })""")
            page.pdf(path=DOCS / "write-up.pdf", format="A4", prefer_css_page_size=True)
            browser.close()
    finally:
        page_file.unlink()
    print(f"wrote {DOCS / 'write-up.pdf'}")


if __name__ == "__main__":
    main()
