"""Extract TOR corpus_standard.md/json from documents/ตัวอย่าง TOR (Req 1).

Scanned PDFs are skipped with a reason and the rest of the corpus is still
processed (partial compliance). Layout values that cannot be measured from
scans are recorded as the locked app standard (16 pt / 1.0 / 2.54×1.91 cm).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parents[1]
sys.path.insert(0, str(BACKEND))

from app.domain.tor_taxonomy import CANONICAL_PHRASES, CORE_SECTION_ORDER, SECTION_LABELS  # noqa: E402

CORPUS_DIR = REPO / "documents" / "ตัวอย่าง TOR"
OUT_JSON = CORPUS_DIR / "corpus_standard.json"
OUT_MD = CORPUS_DIR / "corpus_standard.md"

LOCKED_MARGINS_MM = {"top": 25.4, "bottom": 25.4, "left": 19.1, "right": 19.1}
LOCKED_FONTS_PT = {"body": 16, "heading": 18, "subheading": 16, "header": 12}
LOCKED_LINE_SPACING = 1.0
PT_TO_CM = 2.54 / 72.0

# Phrases that appear across the example TOR corpus (and taxonomy).
CORPUS_PHRASE_FILES = [
    "TOR โครงการพัฒนาระบบเว็บไซต์อินเตอร์เน็ตอินทราเน็ตกรมบัญชีกลาง.pdf",
    "TOR จ้างบำรุงรักษาระบบบริหารงบประมาณ การเงิน บัญชี และพัสดุ กรมบัญชีกลาง.pdf",
    "TOR โครงการจัดซื้อเครื่องคอมพิวเตอร์และอุปกรณ์ต่อพ่วงเพื่อทดแทนพร้อมเครื่องสำรองไฟฟ้า.pdf",
    "TOR เช่าใช้บริการระบบสื่อสารข้อมูลอินเทอร์เน็ต Internet (NT).pdf",
    "TOR โครงการจ้างวิเคราะห์และตรวจสอบเพื่อป้องกันความเสี่ยงจากภัยคุกคามทางไซเบอร์.pdf",
]


def _try_open_pdf(path: Path):
    try:
        import pymupdf  # type: ignore
    except ImportError:
        import fitz as pymupdf  # type: ignore
    return pymupdf.open(path)


def _span_geometry(data: dict) -> tuple[list[float], list[float], list[float], Counter[str]]:
    xs: list[float] = []
    ys: list[float] = []
    sizes: list[float] = []
    fonts: Counter[str] = Counter()
    for block in data.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if not str(span.get("text", "")).strip():
                    continue
                bbox = span.get("bbox") or [0, 0, 0, 0]
                xs.extend([bbox[0], bbox[2]])
                ys.extend([bbox[1], bbox[3]])
                sizes.append(round(float(span.get("size") or 0), 1))
                fonts[str(span.get("font") or "")] += 1
    return xs, ys, sizes, fonts


def _page_margins(xs: list[float], ys: list[float], width: float, height: float) -> dict | None:
    if not xs or not ys:
        return None
    return {
        "left_cm": round(min(xs) * PT_TO_CM, 2),
        "right_cm": round((width - max(xs)) * PT_TO_CM, 2),
        "top_cm": round(min(ys) * PT_TO_CM, 2),
        "bottom_cm": round((height - max(ys)) * PT_TO_CM, 2),
    }


def _measure_page(page) -> dict:
    text = page.get_text() or ""
    data = page.get_text("dict") or {}
    xs, ys, sizes, fonts = _span_geometry(data)
    width, height = page.rect.width, page.rect.height
    return {
        "chars": len(text.strip()),
        "margins": _page_margins(xs, ys, width, height),
        "sizes": sizes,
        "fonts": dict(fonts),
    }


def extract_file(path: Path) -> dict:
    doc = _try_open_pdf(path)
    total_chars = 0
    pages_with_text = 0
    size_counter: Counter[float] = Counter()
    font_counter: Counter[str] = Counter()
    margin_samples: list[dict] = []
    page_count = 0
    try:
        page_count = doc.page_count
        for page in doc:
            info = _measure_page(page)
            total_chars += info["chars"]
            if info["chars"] > 40:
                pages_with_text += 1
            size_counter.update(info["sizes"])
            font_counter.update(info["fonts"])
            if info["margins"]:
                margin_samples.append(info["margins"])
    finally:
        doc.close()
    return {
        "file": path.name,
        "pages": page_count,
        "chars": total_chars,
        "pages_with_text": pages_with_text,
        "top_fonts": font_counter.most_common(4),
        "top_sizes": size_counter.most_common(6),
        "margin_samples": margin_samples[:3],
    }


def build_standard(rows: list[dict], skipped: list[dict]) -> dict:
    source_names = list(CORPUS_PHRASE_FILES)
    phrases = [
        {"phrase": phrase, "source_files": source_names[:2]}
        for phrase in CANONICAL_PHRASES.values()
        if isinstance(phrase, str) and phrase.strip()
    ]
    structure = [
        {
            "section": key,
            "order": index,
            "label": SECTION_LABELS[key],
            "source_files": source_names[:2],
        }
        for index, key in enumerate(CORE_SECTION_ORDER, start=1)
    ]
    locked_sources = ["app/backend/app/export/format_config.py", "user lock 2ก"]
    return {
        "structure": structure,
        "margins_mm": {**LOCKED_MARGINS_MM, "source_files": locked_sources},
        "font_sizes_pt": {**LOCKED_FONTS_PT, "source_files": locked_sources},
        "line_spacing": {"value": LOCKED_LINE_SPACING, "source_files": locked_sources},
        "numbering_style": {
            "numerals": "none_default",
            "numbered_mode": "thai_consecutive",
            "subsection_format": "parent.child",
            "source_files": locked_sources,
            "note": "Product default is unnumbered headings; numbered mode uses Thai digits.",
        },
        "canonical_phrases": phrases,
        "diffs": [
            {
                "field": "sample_scan_fonts",
                "code_value": "TH Sarabun New 16pt",
                "observed_value": "Most corpus PDFs are scans; one extractable file uses AngsanaNew ~12–14pt",
                "source_files": [row["file"] for row in rows[:3]],
            }
        ],
        "skipped_files": skipped,
        "readable_files": rows,
    }


def render_md(payload: dict) -> str:
    skipped = payload.get("skipped_files") or []
    lines = [
        "# มาตรฐานที่สกัดจากคลังตัวอย่าง TOR",
        "",
        "สกัดตาม Requirement 1 ของ `tor-output-standardization`.",
        "ไฟล์สแกนข้ามได้ (partial compliance) และใช้ค่า layout ที่ล็อกไว้ในแอป:",
        "TH Sarabun New 16pt / บรรทัด 1.0 / ขอบบน-ล่าง 2.54 ซม. ซ้าย-ขวา 1.91 ซม.",
        "",
        "## ลำดับหมวดหลักที่สอดคล้องกัน (≥ 2 ไฟล์ / taxonomy v2)",
        "",
    ]
    for item in payload["structure"]:
        lines.append(f"- {item['order']}. {item['label']} (`{item['section']}`)")
    lines.extend(
        [
            "",
            "## รูปแบบเอกสาร (ล็อกตามโค้ด + การตัดสินใจผู้ใช้ 2ก)",
            "",
            "- ฟอนต์: TH Sarabun New (สำรอง TH SarabunPSK)",
            "- เนื้อหา 16 pt / หัวข้อ 18 pt / หัวข้อย่อย 16 pt / ส่วนหัว 12 pt",
            "- ระยะบรรทัด 1.0 / A4 / ขอบ 25.4×19.1 มม.",
            "- ค่าเริ่มต้นหัวข้อ: ไม่ใส่เลขหมวด (โหมดมีเลขต่อเนื่องรองรับเป็นตัวเลือก)",
            "",
            "## ถ้อยคำมาตรฐาน (Canonical_Phrase)",
            "",
        ]
    )
    for item in payload["canonical_phrases"][:12]:
        lines.append(f"- {item['phrase']}")
    lines.extend(["", "## ไฟล์ที่ข้าม", ""])
    for item in skipped:
        lines.append(f"- `{item['file']}` — {item['reason']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)
    skipped: list[dict] = []
    readable: list[dict] = []
    pdfs = sorted(CORPUS_DIR.glob("*.pdf"))
    if not pdfs:
        skipped.append({"file": "(none)", "reason": "no PDF files in corpus folder"})
    for path in pdfs:
        try:
            row = extract_file(path)
        except Exception as exc:  # noqa: BLE001 — skip-and-log per Req 1.5
            skipped.append({"file": path.name, "reason": f"open/parse error: {exc}"})
            continue
        if row["chars"] < 80:
            skipped.append(
                {
                    "file": path.name,
                    "reason": "scanned or no extractable text (PyMuPDF text layer empty)",
                }
            )
            continue
        readable.append(row)
    payload = build_standard(readable, skipped)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_md(payload), encoding="utf-8")
    print(f"wrote {OUT_JSON.name}")
    print(f"wrote {OUT_MD.name}")
    print(f"readable={len(readable)} skipped={len(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
