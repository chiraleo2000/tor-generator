"""
Generate `*_tor_extract.json` files from raw PDF sources.

This is intended for GitHub Pages / mock RAG simulation and for ensuring
`documents/knowledge-base` has JSON extracts to seed/ingest.

Output format matches `app.rag.extraction.extract_tor_extract_json`:
{
  "source_file": "<original filename>",
  "focus_areas": {
     "<focus_name>": [{"content": "<chunk text>"} ...]
  }
}

Usage (from app/backend/):
  python scripts/generate_tor_extracts_from_pdfs.py

Optional env:
  RAW_DOCS_DIR   - folder containing PDFs (default: documents/sources/การจัดซื้อจัดจ้าง/ข้อมูลดิบ)
  KB_DIR          - output folder (default: documents/knowledge-base)
  TOR_EXTRACT_LIMIT - max number of PDFs to process (default: 0 = no limit)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.rag.chunking import chunk_text
from app.rag.extraction import extract_text


def _repo_root() -> Path:
    # scripts/... → app/backend/scripts → parents[3] is repo root
    parts = Path(__file__).resolve().parents
    return parts[3]


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name)
    return Path(raw) if raw else default


def _list_pdfs(raw_docs_dir: Path, limit: int) -> list[Path]:
    pdfs = sorted(raw_docs_dir.glob("*.pdf"))
    if limit > 0:
        pdfs = pdfs[:limit]
    return pdfs


def generate_for_pdf(pdf_path: Path, kb_dir: Path) -> Path | None:
    output_path = kb_dir / f"{pdf_path.stem}_tor_extract.json"
    if output_path.exists():
        return None

    extraction = extract_text(str(pdf_path), mime_type="application/pdf")
    text = extraction.text.strip()
    if not text:
        return None

    chunks = chunk_text(text=text, document_id=str(pdf_path)).chunks
    chunk_texts = [c.text.strip() for c in chunks if c.text and c.text.strip()]
    if not chunk_texts:
        return None

    payload = {
        "source_file": pdf_path.name,
        "focus_areas": {
            "chunks": [{"content": t} for t in chunk_texts],
        },
    }
    kb_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return output_path


def main() -> None:
    repo = _repo_root()
    raw_docs_dir = _env_path(
        "RAW_DOCS_DIR",
        repo / "documents" / "sources" / "การจัดซื้อจัดจ้าง" / "ข้อมูลดิบ",
    )
    kb_dir = _env_path("KB_DIR", repo / "documents" / "knowledge-base")
    limit = int(os.environ.get("TOR_EXTRACT_LIMIT", "0"))

    if not raw_docs_dir.exists():
        raise SystemExit(f"RAW_DOCS_DIR not found: {raw_docs_dir}")

    pdfs = _list_pdfs(raw_docs_dir, limit=limit)
    if not pdfs:
        raise SystemExit(f"No PDFs found in: {raw_docs_dir}")

    created = 0
    for pdf in pdfs:
        out = generate_for_pdf(pdf, kb_dir=kb_dir)
        if out is not None:
            created += 1
            print(f"created: {out.name}")

    print(f"done. created {created} tor_extract files.")


if __name__ == "__main__":
    main()

