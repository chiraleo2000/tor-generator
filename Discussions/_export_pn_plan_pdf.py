"""Export Discussions 33/34 markdown to HTML then PDF via Edge/Chrome headless."""
from __future__ import annotations

import html as html_lib
import pathlib
import subprocess
import sys

import markdown as md

ROOT = pathlib.Path(__file__).resolve().parent
CSS = """
@page { size: A4; margin: 18mm 16mm; }
body { font-family: 'Segoe UI', 'Tahoma', 'Arial', sans-serif; font-size: 11pt; line-height: 1.45; color: #111; }
h1 { font-size: 18pt; border-bottom: 2px solid #333; padding-bottom: 6px; }
h2 { font-size: 14pt; margin-top: 1.4em; color: #1a1a1a; }
h3 { font-size: 12pt; margin-top: 1.1em; }
table { border-collapse: collapse; width: 100%; margin: 0.8em 0; font-size: 10pt; }
th, td { border: 1px solid #888; padding: 5px 7px; vertical-align: top; text-align: left; }
th { background: #f0f0f0; }
code, pre { font-family: Consolas, 'Courier New', monospace; font-size: 9pt; }
pre { background: #f6f6f6; border: 1px solid #ddd; padding: 10px; white-space: pre-wrap; word-break: break-word; }
code { background: #f3f3f3; padding: 1px 4px; }
ul, ol { padding-left: 1.3em; }
a { color: #0645ad; text-decoration: none; }
hr { border: none; border-top: 1px solid #ccc; margin: 1.2em 0; }
"""

BROWSER_CANDIDATES = [
    pathlib.Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    pathlib.Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    pathlib.Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
]


def find_browser() -> pathlib.Path:
    for path in BROWSER_CANDIDATES:
        if path.is_file():
            return path
    raise FileNotFoundError("Edge/Chrome not found for headless PDF export")


def md_to_html(src: pathlib.Path, title: str) -> pathlib.Path:
    text = src.read_text(encoding="utf-8")
    body = md.markdown(text, extensions=["tables", "fenced_code", "nl2br"])
    doc = (
        "<!DOCTYPE html><html lang=\"th\"><head><meta charset=\"utf-8\"/>"
        f"<title>{html_lib.escape(title)}</title><style>{CSS}</style></head>"
        f"<body>{body}</body></html>"
    )
    out = src.with_suffix(".html")
    out.write_text(doc, encoding="utf-8")
    return out


def html_to_pdf(browser: pathlib.Path, html_path: pathlib.Path, pdf_path: pathlib.Path) -> None:
    tmp_pdf = pdf_path.with_suffix(".tmp.pdf")
    if tmp_pdf.exists():
        tmp_pdf.unlink()
    uri = html_path.resolve().as_uri()
    cmd = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        f"--print-to-pdf={tmp_pdf.resolve()}",
        "--no-pdf-header-footer",
        uri,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    if not tmp_pdf.is_file() or tmp_pdf.stat().st_size < 100:
        raise RuntimeError(f"PDF not created: {tmp_pdf}")
    try:
        if pdf_path.exists():
            pdf_path.unlink()
        tmp_pdf.replace(pdf_path)
    except PermissionError:
        # File open in viewer — leave .tmp.pdf for manual replace
        print(f"WARN locked, wrote {tmp_pdf.name} instead of {pdf_path.name}")
        return


def main() -> int:
    browser = find_browser()
    jobs = [
        ("33-AWS-PN-CLOUD-MINIMUM-COST-PLAN.md", "33 PN Cloud: Embed 4 / S3 Vectors / MCP"),
        ("34-AWS-PN-TOOLS-LIST.md", "34 AWS PN Tools List"),
        ("35-AWS-PN-DEV-AND-DEPLOY.md", "35 PN EC2 Deploy and .env"),
        (
            "36-AWS-PN-USER-SETUP-AND-RUNBOOK.md",
            "36 PN User Setup Local to AWS + Manual Tasks",
        ),
    ]
    for name, title in jobs:
        src = ROOT / name
        html_path = md_to_html(src, title)
        pdf_path = src.with_suffix(".pdf")
        html_to_pdf(browser, html_path, pdf_path)
        print(f"OK {pdf_path.name} ({pdf_path.stat().st_size} bytes)")
        # keep HTML as intermediate for re-print; optional cleanup
        html_path.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
