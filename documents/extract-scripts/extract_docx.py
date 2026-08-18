# -*- coding: utf-8 -*-
"""
extract_docx.py — DOCX Extraction Pipeline
แกะเนื้อหาจากไฟล์ .docx ที่มีอยู่ในโปรเจกต์ เป็น raw text

รองรับ:
  - Paragraphs (รวม heading levels)
  - Tables (แปลงเป็น text format)
  - Nested content

Usage:
  python extract_docx.py                          # extract ทุก .docx ในโฟลเดอร์เริ่มต้น
  python extract_docx.py --input <folder>         # ระบุโฟลเดอร์
  python extract_docx.py --file <single_docx>     # extract ไฟล์เดียว
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

try:
    from docx import Document
    from docx.text.paragraph import Paragraph
    from docx.table import Table
except ImportError:
    print("[ERROR] python-docx not installed. Run: pip install python-docx")
    sys.exit(1)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable


# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
_DOCUMENTS = Path(__file__).resolve().parents[1]
_SOURCES = _DOCUMENTS / "sources"
_RESEARCH = _DOCUMENTS / "research"
DEFAULT_INPUT_DIRS = [
    str(_SOURCES / "การจัดจ้างทำของ"),
    str(_SOURCES / "การจัดจ้างทำของ" / "ข้อมูลดิบ"),
]
DEFAULT_OUTPUT_DIR = str(_RESEARCH / "raw_text")


# ─────────────────────────────────────────────────────────────
# DOCX Extraction
# ─────────────────────────────────────────────────────────────
def get_heading_prefix(paragraph) -> str:
    """สร้าง prefix ตาม heading level"""
    style_name = paragraph.style.name if paragraph.style else ""
    if "Heading 1" in style_name or "หัวเรื่อง 1" in style_name:
        return "\n\n# "
    elif "Heading 2" in style_name or "หัวเรื่อง 2" in style_name:
        return "\n\n## "
    elif "Heading 3" in style_name or "หัวเรื่อง 3" in style_name:
        return "\n\n### "
    elif "Heading" in style_name:
        return "\n\n#### "
    return ""


def extract_table_text(table) -> str:
    """แปลง table เป็น readable text format"""
    rows_text = []
    for row_idx, row in enumerate(table.rows):
        cells = []
        for cell in row.cells:
            cell_text = cell.text.strip().replace('\n', ' ')
            cells.append(cell_text)
        row_text = " | ".join(cells)
        rows_text.append(row_text)

        # เพิ่ม separator หลัง header row
        if row_idx == 0:
            separator = " | ".join(["---"] * len(cells))
            rows_text.append(separator)

    return "\n".join(rows_text)


def iter_block_items(parent):
    """
    Iterate through document body items in order (paragraphs and tables).
    This preserves the document's reading order.
    """
    from docx.oxml.ns import qn
    body = parent.element.body

    for child in body:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
        if tag == 'p':
            yield ('paragraph', Paragraph(child, parent))
        elif tag == 'tbl':
            yield ('table', Table(child, parent))


def extract_docx(docx_path: str) -> dict:
    """Extract text from a DOCX file preserving structure"""
    try:
        doc = Document(docx_path)
        parts = []
        para_count = 0
        table_count = 0

        for block_type, block in iter_block_items(doc):
            if block_type == 'paragraph':
                text = block.text.strip()
                if not text:
                    continue

                prefix = get_heading_prefix(block)
                if prefix:
                    parts.append(f"{prefix}{text}")
                else:
                    parts.append(text)
                para_count += 1

            elif block_type == 'table':
                table_text = extract_table_text(block)
                if table_text.strip():
                    parts.append(f"\n[ตาราง]\n{table_text}\n")
                    table_count += 1

        full_text = '\n'.join(parts)

        # Basic cleanup
        full_text = re.sub(r'\n{4,}', '\n\n\n', full_text)
        full_text = full_text.strip()

        return {
            "success": True,
            "engine": "python-docx",
            "num_paragraphs": para_count,
            "num_tables": table_count,
            "char_count": len(full_text),
            "text": full_text,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"python-docx error: {str(e)}",
            "engine": "python-docx",
            "num_paragraphs": 0,
            "num_tables": 0,
            "char_count": 0,
            "text": "",
        }


# ─────────────────────────────────────────────────────────────
# Batch Processing
# ─────────────────────────────────────────────────────────────
def get_safe_filename(original_name: str) -> str:
    """สร้างชื่อไฟล์ที่ปลอดภัย"""
    name = Path(original_name).stem
    if len(name) > 100:
        name = name[:100]
    return name


def process_single_docx(docx_path: str, output_dir: str) -> dict:
    """Process ไฟล์ docx เดียว → save raw text + return metadata"""
    docx_path = Path(docx_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = docx_path.name
    safe_name = get_safe_filename(filename)

    # Extract
    result = extract_docx(str(docx_path))

    # Prepare metadata
    metadata = {
        "source_file": filename,
        "source_path": str(docx_path),
        "extraction_time": datetime.now().isoformat(),
        "engine": result.get("engine", "none"),
        "num_paragraphs": result.get("num_paragraphs", 0),
        "num_tables": result.get("num_tables", 0),
        "char_count": result.get("char_count", 0),
        "success": result.get("success", False),
        "error": result.get("error", None),
    }

    if result.get("success") and result.get("text"):
        # Save text file
        text_path = output_dir / f"{safe_name}.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(result["text"])
        metadata["output_file"] = str(text_path)
        metadata["output_filename"] = f"{safe_name}.txt"
    else:
        metadata["output_file"] = None

    return metadata


def process_directory(input_dir: str, output_dir: str) -> list:
    """Process ทุก DOCX ในโฟลเดอร์"""
    input_path = Path(input_dir)
    docx_files = sorted(input_path.glob("*.docx"))

    # Filter out temp files (starting with ~$ or .$)
    docx_files = [f for f in docx_files if not f.name.startswith(('~$', '.$'))]

    if not docx_files:
        print(f"  [!] ไม่พบไฟล์ DOCX ใน: {input_dir}")
        return []

    print(f"  พบ {len(docx_files)} ไฟล์ DOCX ใน: {input_dir}")

    results = []
    for docx_file in tqdm(docx_files, desc="  Extracting"):
        meta = process_single_docx(str(docx_file), output_dir)
        results.append(meta)

        status = "✓" if meta["success"] else "✗"
        chars = meta["char_count"]
        tables = meta["num_tables"]
        print(f"    {status} {meta['source_file'][:60]}... ({chars:,} chars, {tables} tables)")

    return results


def generate_report(all_results: list, output_dir: str):
    """สร้าง extraction report"""
    output_path = Path(output_dir)

    total = len(all_results)
    success = sum(1 for r in all_results if r["success"])
    failed = total - success
    total_chars = sum(r["char_count"] for r in all_results)

    report = {
        "extraction_date": datetime.now().isoformat(),
        "file_type": "docx",
        "summary": {
            "total_files": total,
            "successful": success,
            "failed": failed,
            "total_characters": total_chars,
        },
        "files": all_results,
    }

    # Save JSON report
    report_path = output_path / "_extraction_report_docx.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"DOCX EXTRACTION COMPLETE")
    print(f"  Total: {total} | Success: {success} | Failed: {failed}")
    print(f"  Total chars: {total_chars:,}")
    print(f"  Report: {report_path}")
    print(f"{'=' * 60}")

    return report


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Extract text from DOCX documents"
    )
    parser.add_argument('--input', '-i', nargs='*',
                        help='Input directories containing DOCX files')
    parser.add_argument('--output', '-o', default=DEFAULT_OUTPUT_DIR,
                        help='Output directory for raw text files')
    parser.add_argument('--file', '-f',
                        help='Extract single DOCX file')

    args = parser.parse_args()

    output_dir = args.output
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if args.file:
        print(f"Extracting single file: {args.file}")
        meta = process_single_docx(args.file, output_dir)
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return

    # Batch mode
    input_dirs = args.input if args.input else DEFAULT_INPUT_DIRS

    print("=" * 60)
    print("DOCX EXTRACTION PIPELINE")
    print(f"Output: {output_dir}")
    print("=" * 60)

    all_results = []
    for input_dir in input_dirs:
        if not Path(input_dir).exists():
            print(f"\n[SKIP] Directory not found: {input_dir}")
            continue

        print(f"\n{'─' * 60}")
        print(f"Processing: {input_dir}")
        print(f"{'─' * 60}")

        results = process_directory(input_dir, output_dir)
        all_results.extend(results)

    if all_results:
        generate_report(all_results, output_dir)


if __name__ == "__main__":
    main()
