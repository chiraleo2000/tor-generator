"""Build documents/exports/tor-rag-mcp-dataset-vX.Y.Z.zip"""

from __future__ import annotations

import argparse
import zipfile
from datetime import datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="0.4.0")
    args = parser.parse_args()
    version = args.version

    root = Path(__file__).resolve().parents[2]
    out_dir = root / "documents" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"tor-rag-mcp-dataset-v{version}.zip"

    raw_dir = root / "documents" / "sources" / "การจัดซื้อจัดจ้าง" / "ข้อมูลดิบ"
    kb_dir = root / "documents" / "knowledge-base"
    quick_dir = root / "app" / "infra" / "quick"

    pdfs = sorted({*raw_dir.glob("*.pdf"), *raw_dir.glob("*.PDF")}, key=lambda p: p.name.lower())
    entries: list[tuple[Path, str]] = []

    for pdf in pdfs:
        entries.append((pdf, f"rag-pdfs/{pdf.name}"))
        extract = kb_dir / f"{pdf.stem}_tor_extract.json"
        if extract.is_file():
            entries.append((extract, f"rag-json-chunks/{extract.name}"))

    for path in sorted(quick_dir.iterdir()):
        if path.is_file():
            entries.append((path, f"mcp-amazon-quick/{path.name}"))

    mcp_server = root / "app" / "backend" / "app" / "mcp_retrieve_server.py"
    entries.append((mcp_server, "mcp-pgvector/mcp_retrieve_server.py"))
    doc = root / "Discussions" / "32-AMAZON-QUICK.md"
    entries.append((doc, "docs/32-AMAZON-QUICK.md"))

    manifest_lines = [
        f"TOR Generator dataset export v{version}",
        f"Built: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"RAG PDFs: {len(pdfs)}",
        f"JSON extracts: {sum(1 for _, arc in entries if arc.startswith('rag-json-chunks/'))}",
        "",
        "Compose tips:",
        "  docker compose up -d mcp-rag",
        "  docker compose --profile amazon-quick up -d amazon-quick",
        "  Amazon Quick Desktop MCP URL: http://127.0.0.1:8767/mcp",
        "",
    ]
    for src, arc in entries:
        manifest_lines.append(f"{src.stat().st_size}\t{arc}")

    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("MANIFEST.txt", "\n".join(manifest_lines) + "\n")
        for src, arc in entries:
            zf.write(src, arcname=arc)

    mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"Wrote {zip_path} size_MB={mb:.1f}")


if __name__ == "__main__":
    main()
