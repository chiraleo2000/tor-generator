# -*- coding: utf-8 -*-
"""
extract_pdf.py — PDF Extraction Pipeline
แกะเนื้อหาจาก PDF ภาษาไทย (กฎหมายจัดซื้อจัดจ้างภาครัฐ) เป็น raw text

ใช้ 2 engines:
  1. pdfplumber (primary) — ดีกับ PDF ที่เป็น text-based
  2. PyMuPDF/fitz (fallback) — ดีกับ PDF ที่มี layout ซับซ้อน

Usage:
  python extract_pdf.py                          # extract ทุกไฟล์ในโฟลเดอร์เริ่มต้น
  python extract_pdf.py --input <folder>         # ระบุโฟลเดอร์ input
  python extract_pdf.py --input <folder> --output <folder>
  python extract_pdf.py --file <single_pdf>      # extract ไฟล์เดียว
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from datetime import datetime

# Ensure stdout handles Thai text
sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    print("[WARN] pdfplumber not installed, will use PyMuPDF only")

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None
    print("[WARN] PyMuPDF not installed, will use pdfplumber only")

try:
    import pytesseract
    from PIL import Image
    import io
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("[WARN] pytesseract/Pillow not installed, OCR fallback disabled")

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
    str(_SOURCES / "การจัดซื้อจัดจ้าง" / "ข้อมูลดิบ"),
    str(_SOURCES / "การจัดจ้างทำของ" / "ข้อมูลดิบ"),
]
DEFAULT_OUTPUT_DIR = str(_RESEARCH / "raw_text")


# ─────────────────────────────────────────────────────────────
# Text Cleaning Utilities
# ─────────────────────────────────────────────────────────────
def clean_text(text: str) -> str:
    """ทำความสะอาด text ที่ extract จาก PDF"""
    if not text:
        return ""

    # ลบ null characters
    text = text.replace('\x00', '')

    # แก้ปัญหา ligature ภาษาไทยที่พบบ่อยใน PDF
    # บางไฟล์ encode สระ/วรรณยุกต์แยก → รวมกลับ
    # (ไม่ต้องทำอะไรพิเศษถ้า PDF encode ถูกต้อง)

    # ลบ multiple spaces แต่เก็บ newlines
    text = re.sub(r'[^\S\n]+', ' ', text)

    # ลบ lines ที่มีแค่ spaces
    text = re.sub(r'\n\s*\n', '\n\n', text)

    # ลบ page numbers ที่อยู่บรรทัดเดียว (เช่น "- 5 -" หรือ "5" หรือ "หน้า 5")
    text = re.sub(r'\n\s*-?\s*\d+\s*-?\s*\n', '\n', text)
    text = re.sub(r'\n\s*หน้า\s*\d+\s*\n', '\n', text)

    # ลบ leading/trailing whitespace แต่ละบรรทัด
    lines = [line.strip() for line in text.split('\n')]
    text = '\n'.join(lines)

    # ลบ newlines ที่เกิน 3 ติดกัน
    text = re.sub(r'\n{4,}', '\n\n\n', text)

    return text.strip()


def remove_headers_footers(pages_text: list, threshold: int = 3) -> list:
    """
    ตรวจหาและลบ header/footer ที่ซ้ำกันทุกหน้า
    threshold: จำนวนหน้าขั้นต่ำที่ text ต้องซ้ำจึงถือว่าเป็น header/footer
    """
    if len(pages_text) < threshold:
        return pages_text

    # เก็บ first line และ last line ของแต่ละหน้า
    first_lines = []
    last_lines = []

    for page in pages_text:
        lines = [l.strip() for l in page.split('\n') if l.strip()]
        first_lines.append(lines[0] if lines else "")
        last_lines.append(lines[-1] if lines else "")

    # หา header ที่ซ้ำ
    header_candidates = set()
    for line in first_lines:
        if line and first_lines.count(line) >= threshold:
            header_candidates.add(line)

    # หา footer ที่ซ้ำ
    footer_candidates = set()
    for line in last_lines:
        if line and last_lines.count(line) >= threshold:
            footer_candidates.add(line)

    # ลบ header/footer
    cleaned_pages = []
    for page in pages_text:
        lines = page.split('\n')
        cleaned_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped in header_candidates and i < 3:
                continue
            if stripped in footer_candidates and i > len(lines) - 4:
                continue
            cleaned_lines.append(line)
        cleaned_pages.append('\n'.join(cleaned_lines))

    return cleaned_pages


# ─────────────────────────────────────────────────────────────
# PDF Extraction Engines
# ─────────────────────────────────────────────────────────────
def extract_with_pdfplumber(pdf_path: str) -> dict:
    """Extract text using pdfplumber (better for text-based PDFs)"""
    if pdfplumber is None:
        return {"success": False, "error": "pdfplumber not installed"}

    try:
        pages_text = []
        with pdfplumber.open(pdf_path) as pdf:
            num_pages = len(pdf.pages)
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)

        # Remove headers/footers
        pages_text = remove_headers_footers(pages_text)

        # Clean and join
        full_text = '\n\n--- หน้า ---\n\n'.join(pages_text)
        full_text = clean_text(full_text)

        return {
            "success": True,
            "engine": "pdfplumber",
            "num_pages": num_pages,
            "char_count": len(full_text),
            "text": full_text
        }
    except Exception as e:
        return {"success": False, "error": f"pdfplumber error: {str(e)}"}


def extract_with_pymupdf(pdf_path: str) -> dict:
    """Extract text using PyMuPDF/fitz (better for complex layouts)"""
    if fitz is None:
        return {"success": False, "error": "PyMuPDF not installed"}

    try:
        pages_text = []
        doc = fitz.open(pdf_path)
        num_pages = len(doc)

        for page in doc:
            text = page.get_text("text") or ""
            pages_text.append(text)

        doc.close()

        # Remove headers/footers
        pages_text = remove_headers_footers(pages_text)

        # Clean and join
        full_text = '\n\n--- หน้า ---\n\n'.join(pages_text)
        full_text = clean_text(full_text)

        return {
            "success": True,
            "engine": "PyMuPDF",
            "num_pages": num_pages,
            "char_count": len(full_text),
            "text": full_text
        }
    except Exception as e:
        return {"success": False, "error": f"PyMuPDF error: {str(e)}"}


def extract_with_ocr(pdf_path: str) -> dict:
    """Extract text from scanned PDF using Tesseract OCR (Thai + English)"""
    if not OCR_AVAILABLE or fitz is None:
        return {"success": False, "error": "OCR not available (need pytesseract + PyMuPDF)"}

    try:
        pages_text = []
        doc = fitz.open(pdf_path)
        num_pages = len(doc)

        for page_num, page in enumerate(doc):
            # Render page to image at 300 DPI for good OCR quality
            mat = fitz.Matrix(300 / 72, 300 / 72)  # 300 DPI
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            # OCR with Thai + English
            text = pytesseract.image_to_string(img, lang='tha+eng')
            pages_text.append(text)

        doc.close()

        # Remove headers/footers
        pages_text = remove_headers_footers(pages_text)

        # Clean and join
        full_text = '\n\n--- หน้า ---\n\n'.join(pages_text)
        full_text = clean_text(full_text)

        return {
            "success": True,
            "engine": "OCR (Tesseract)",
            "num_pages": num_pages,
            "char_count": len(full_text),
            "text": full_text
        }
    except Exception as e:
        return {"success": False, "error": f"OCR error: {str(e)}"}


def is_scanned_pdf(pdf_path: str) -> bool:
    """ตรวจว่า PDF เป็น scanned image หรือไม่"""
    if fitz is None:
        return False
    try:
        doc = fitz.open(pdf_path)
        total_text = 0
        num_pages = len(doc)
        for page in doc:
            total_text += len(page.get_text("text").strip())
        doc.close()
        avg_text = total_text / max(num_pages, 1)
        return avg_text < 50  # น้อยกว่า 50 chars ต่อหน้า = น่าจะเป็น scan
    except:
        return False


def extract_pdf(pdf_path: str) -> dict:
    """
    Extract text from PDF using best available engine.
    Strategy:
      1. ตรวจว่าเป็น scanned PDF หรือไม่
      2. ถ้าเป็น scan → ใช้ OCR
      3. ถ้าไม่ → ลอง pdfplumber และ PyMuPDF, เลือกตัวที่ได้ text มากกว่า
    """
    # Check if scanned
    if is_scanned_pdf(pdf_path):
        print(f"    [OCR] Detected scanned PDF, using Tesseract OCR...")
        ocr_result = extract_with_ocr(pdf_path)
        if ocr_result["success"] and ocr_result["char_count"] > 50:
            return ocr_result
        # If OCR fails or gets too little, try text extraction anyway

    results = {}

    # Try pdfplumber first
    result_plumber = extract_with_pdfplumber(pdf_path)
    if result_plumber["success"]:
        results["pdfplumber"] = result_plumber

    # Try PyMuPDF
    result_mupdf = extract_with_pymupdf(pdf_path)
    if result_mupdf["success"]:
        results["pymupdf"] = result_mupdf

    if not results:
        # Last resort: try OCR even if not detected as scanned
        if OCR_AVAILABLE:
            ocr_result = extract_with_ocr(pdf_path)
            if ocr_result["success"]:
                return ocr_result

        error_msg = result_plumber.get("error", "") + " | " + result_mupdf.get("error", "")
        return {
            "success": False,
            "error": error_msg,
            "engine": "none",
            "num_pages": 0,
            "char_count": 0,
            "text": ""
        }

    # เลือก engine ที่ได้ text มากกว่า
    best = None
    best_chars = 0
    for engine, result in results.items():
        if result["char_count"] > best_chars:
            best_chars = result["char_count"]
            best = result

    # ถ้า text extraction ได้น้อยมาก อาจเป็น partial scan → ลอง OCR
    if best_chars < 100 and OCR_AVAILABLE:
        print(f"    [OCR] Low text yield ({best_chars} chars), trying OCR...")
        ocr_result = extract_with_ocr(pdf_path)
        if ocr_result["success"] and ocr_result["char_count"] > best_chars:
            return ocr_result

    return best


# ─────────────────────────────────────────────────────────────
# Batch Processing
# ─────────────────────────────────────────────────────────────
def get_safe_filename(original_name: str) -> str:
    """สร้างชื่อไฟล์ที่ปลอดภัย แต่ยังอ่านได้"""
    # ตัด extension
    name = Path(original_name).stem
    # ตัดให้ไม่เกิน 100 chars (เก็บภาษาไทยได้)
    if len(name) > 100:
        name = name[:100]
    return name


def process_single_file(pdf_path: str, output_dir: str) -> dict:
    """Process ไฟล์เดียว → save raw text + return metadata"""
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = pdf_path.name
    safe_name = get_safe_filename(filename)

    # Extract
    result = extract_pdf(str(pdf_path))

    # Prepare metadata
    metadata = {
        "source_file": filename,
        "source_path": str(pdf_path),
        "extraction_time": datetime.now().isoformat(),
        "engine": result.get("engine", "none"),
        "num_pages": result.get("num_pages", 0),
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
    """Process ทุก PDF ในโฟลเดอร์"""
    input_path = Path(input_dir)
    pdf_files = sorted(input_path.glob("*.pdf"))

    if not pdf_files:
        print(f"  [!] ไม่พบไฟล์ PDF ใน: {input_dir}")
        return []

    print(f"  พบ {len(pdf_files)} ไฟล์ PDF ใน: {input_dir}")

    results = []
    for pdf_file in tqdm(pdf_files, desc="  Extracting"):
        meta = process_single_file(str(pdf_file), output_dir)
        results.append(meta)

        # Progress indicator
        status = "✓" if meta["success"] else "✗"
        chars = meta["char_count"]
        print(f"    {status} {meta['source_file'][:60]}... ({chars:,} chars, {meta['num_pages']} pages)")

    return results


def generate_report(all_results: list, output_dir: str):
    """สร้าง extraction report (JSON + text summary)"""
    output_path = Path(output_dir)

    # Summary stats
    total = len(all_results)
    success = sum(1 for r in all_results if r["success"])
    failed = total - success
    total_chars = sum(r["char_count"] for r in all_results)
    total_pages = sum(r["num_pages"] for r in all_results)

    report = {
        "extraction_date": datetime.now().isoformat(),
        "summary": {
            "total_files": total,
            "successful": success,
            "failed": failed,
            "total_characters": total_chars,
            "total_pages": total_pages,
        },
        "files": all_results,
    }

    # Save JSON report
    report_path = output_path / "_extraction_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Save text summary
    summary_path = output_path / "_extraction_summary.txt"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("PDF EXTRACTION REPORT\n")
        f.write(f"วันที่: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"สรุป:\n")
        f.write(f"  ไฟล์ทั้งหมด: {total}\n")
        f.write(f"  สำเร็จ:      {success}\n")
        f.write(f"  ล้มเหลว:     {failed}\n")
        f.write(f"  ตัวอักษรรวม: {total_chars:,}\n")
        f.write(f"  หน้ารวม:     {total_pages:,}\n")
        f.write("\n" + "-" * 70 + "\n\n")

        f.write("รายละเอียดแต่ละไฟล์:\n\n")
        for i, r in enumerate(all_results, 1):
            status = "✓" if r["success"] else "✗"
            f.write(f"  {i:2d}. [{status}] {r['source_file']}\n")
            f.write(f"      Engine: {r['engine']} | Pages: {r['num_pages']} | Chars: {r['char_count']:,}\n")
            if r.get("error"):
                f.write(f"      Error: {r['error']}\n")
            f.write("\n")

    print(f"\n{'=' * 60}")
    print(f"EXTRACTION COMPLETE")
    print(f"  Total: {total} | Success: {success} | Failed: {failed}")
    print(f"  Total chars: {total_chars:,} | Total pages: {total_pages}")
    print(f"  Report: {report_path}")
    print(f"{'=' * 60}")

    return report


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Extract text from Thai PDF documents (กฎหมายจัดซื้อจัดจ้าง)"
    )
    parser.add_argument('--input', '-i', nargs='*',
                        help='Input directories containing PDFs')
    parser.add_argument('--output', '-o', default=DEFAULT_OUTPUT_DIR,
                        help='Output directory for raw text files')
    parser.add_argument('--file', '-f',
                        help='Extract single PDF file')

    args = parser.parse_args()

    output_dir = args.output
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if args.file:
        # Single file mode
        print(f"Extracting single file: {args.file}")
        meta = process_single_file(args.file, output_dir)
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return

    # Batch mode
    input_dirs = args.input if args.input else DEFAULT_INPUT_DIRS

    print("=" * 60)
    print("PDF EXTRACTION PIPELINE")
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
