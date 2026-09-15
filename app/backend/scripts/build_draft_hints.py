"""Refresh category_hints.json from taxonomy gold headings and OCR few-shots.

Does not ingest scans into the law RAG. OCR text is only used as draft hints.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parents[1]
sys.path.insert(0, str(BACKEND))

from app.domain.section_profile import SEMANTIC_TO_STORAGE  # noqa: E402
from app.domain.tor_taxonomy import (  # noqa: E402
    PROCUREMENT_TYPES,
    SECTION_LABELS,
    section_order,
)

HINTS_PATH = BACKEND / "app" / "domain" / "category_hints.json"
OCR_DIR = REPO / "documents" / "ตัวอย่าง TOR" / "corpus_ocr"


def _storage_order(category: str) -> list[str]:
    keys: list[str] = []
    for semantic in section_order(category):
        storage = SEMANTIC_TO_STORAGE.get(semantic)
        if storage and storage not in keys:
            keys.append(storage)
    return keys


def _ocr_snippets(limit: int = 4) -> list[str]:
    snippets: list[str] = []
    if not OCR_DIR.is_dir():
        return snippets
    heading = re.compile(r"(ความเป็นมา|วัตถุประสงค์|ขอบเขต|คุณสมบัติ|งวด|ค่าปรับ|หลักเกณฑ์)")
    for path in sorted(OCR_DIR.glob("*.txt")):
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            clean = " ".join(line.split())
            if len(clean) < 24 or not heading.search(clean):
                continue
            snippets.append(clean[:240])
            if len(snippets) >= limit:
                return snippets
    return snippets


def merge_hints(existing: dict) -> dict:
    payload = dict(existing) if isinstance(existing, dict) else {}
    snippets = _ocr_snippets()
    for category in PROCUREMENT_TYPES:
        blob = dict(payload.get(category) or {})
        blob["structure"] = _storage_order(category)
        blob["gold_headings"] = [
            SECTION_LABELS.get(semantic, semantic) for semantic in section_order(category)
        ]
        formulaic = dict(blob.get("formulaic") or {})
        if snippets and "ocr_fewshot" not in formulaic:
            formulaic["ocr_fewshot"] = " / ".join(snippets[:2])
        blob["formulaic"] = formulaic
        payload[category] = blob
    return payload


def main() -> int:
    existing: dict = {}
    if HINTS_PATH.is_file():
        existing = json.loads(HINTS_PATH.read_text(encoding="utf-8"))
    payload = merge_hints(existing)
    HINTS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {HINTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
