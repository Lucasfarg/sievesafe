"""Build the medRxiv PDFs: paper/sievesafe-preprint.pdf and paper/tripod-llm-checklist.pdf.

  uvx --with markdown python paper/build.py && NODE_PATH=<dir with playwright> node paper/pdf.mjs

Markdown → self-contained HTML (inline CSS, no external requests) in paper/build/; pdf.mjs prints them with Chromium."""
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
CSS = """
@page { size: A4; margin: 22mm 20mm; }
body { font: 10.5pt/1.5 "Liberation Serif", "Times New Roman", serif; color: #111; }
h1 { font-size: 16pt; line-height: 1.25; margin: 0 0 8pt; }
h2 { font-size: 12.5pt; margin: 16pt 0 4pt; } h3 { font-size: 11pt; margin: 12pt 0 3pt; }
p, li { text-align: justify; hyphens: auto; } code { font-size: 9pt; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; margin: 6pt 0 10pt; page-break-inside: avoid; }
th, td { border-top: 0.5pt solid #999; border-bottom: 0.5pt solid #999; padding: 2pt 4pt; vertical-align: top; }
th { text-align: left; background: #f2f2f2; }
a { color: #111; text-decoration: none; }
"""
(HERE / "build").mkdir(exist_ok=True)
for name in ("sievesafe-preprint", "tripod-llm-checklist"):
    body = markdown.markdown((HERE / f"{name}.md").read_text(encoding="utf-8"), extensions=["tables"])
    (HERE / "build" / f"{name}.html").write_text(
        f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{name}</title><style>{CSS}</style></head><body>{body}</body></html>',
        encoding="utf-8")
print("wrote paper/build/*.html")
