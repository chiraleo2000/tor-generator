# -*- coding: utf-8 -*-
"""
extract_tor_content.py — Deep Extract TOR-Relevant Content
Extract มาตรา/ข้อ/หัวข้อที่เกี่ยวข้องกับการร่าง TOR จากเอกสารกฎหมาย

แยก sections ที่เกี่ยวข้องออกมาเป็น structured JSON จัดตาม 8 focus areas:
  1. นิยามและประเภท (definitions)
  2. วิธีจัดซื้อจัดจ้าง (procurement_methods)
  3. การจัดทำ TOR (tor_preparation)
  4. คุณสมบัติผู้เสนอราคา (qualifications)
  5. เกณฑ์การพิจารณา (evaluation_criteria)
  6. สัญญาและค่าปรับ (contract_penalty)
  7. หลักประกัน (guarantee)
  8. ระยะเวลาและขั้นตอน (timeline_process)

Usage:
  python extract_tor_content.py                  # extract ทุกไฟล์ high-relevance
  python extract_tor_content.py --file <txt>     # extract ไฟล์เดียว
  python extract_tor_content.py --all            # extract ทุกไฟล์
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
_DOCUMENTS = Path(__file__).resolve().parents[1]
_RESEARCH = _DOCUMENTS / "research"
RAW_TEXT_DIR = str(_RESEARCH / "raw_text")
ANALYSIS_DIR = str(_RESEARCH / "analysis")
OUTPUT_DIR = str(_DOCUMENTS / "knowledge-base")

# Focus areas with keywords for matching
FOCUS_AREAS = {
    "definitions": {
        "name": "นิยามและประเภท",
        "keywords": [
            "พัสดุ", "การจัดซื้อจัดจ้าง", "หน่วยงานของรัฐ", "ผู้ประกอบการ",
            "งานก่อสร้าง", "งานจ้างที่ปรึกษา", "งานจ้างออกแบบ",
            "ในพระราชบัญญัตินี้", "หมายความว่า", "ให้หมายความรวมถึง",
        ],
        "section_patterns": [
            r"มาตรา\s*[๔4][\s\n]",  # มาตรา 4 นิยาม
            r"มาตรา\s*[๙9][\s\n]",  # มาตรา 9
            r"ข้อ\s*[๔4][\s\n]",
        ],
    },
    "procurement_methods": {
        "name": "วิธีจัดซื้อจัดจ้าง",
        "keywords": [
            "วิธีประกาศเชิญชวนทั่วไป", "วิธีคัดเลือก", "วิธีเฉพาะเจาะจง",
            "e-bidding", "e-market", "ประกวดราคาอิเล็กทรอนิกส์",
            "ตลาดอิเล็กทรอนิกส์", "สอบราคา",
            "วงเงิน", "ไม่เกินห้าแสนบาท", "เกินห้าแสนบาท",
        ],
        "section_patterns": [
            r"มาตรา\s*[๕5][๔4]",  # 54
            r"มาตรา\s*[๕5][๕5]",  # 55
            r"มาตรา\s*[๕5][๖6]",  # 56
            r"มาตรา\s*[๕5][๗7]",  # 57-68
            r"มาตรา\s*[๕5][๘8]",
            r"มาตรา\s*[๖6][๐-๙0-9]",
        ],
    },
    "tor_preparation": {
        "name": "การจัดทำ TOR",
        "keywords": [
            "ร่างขอบเขตของงาน", "ขอบเขตของงาน", "รายละเอียดคุณลักษณะ",
            "TOR", "คุณลักษณะเฉพาะ", "แต่งตั้งคณะกรรมการ.*จัดทำ",
            "รายงานขอซื้อ", "รายงานขอจ้าง", "เหตุผลความจำเป็น",
            "ราคากลาง", "กำหนดราคากลาง",
        ],
        "section_patterns": [
            r"ข้อ\s*[๒2][๑1]",  # ข้อ 21
            r"ข้อ\s*[๒2][๒2]",  # ข้อ 22
            r"ข้อ\s*[๒2][๓3]",  # ข้อ 23
            r"ข้อ\s*[๒2][๔4]",
        ],
    },
    "qualifications": {
        "name": "คุณสมบัติผู้เสนอราคา",
        "keywords": [
            "คุณสมบัติ", "ผู้ยื่นข้อเสนอ", "ผู้เสนอราคา",
            "ไม่เป็นผู้ที่ถูกระบุชื่อ", "ไม่เป็นผู้มีผลประโยชน์ร่วม",
            "ไม่เป็นผู้ที่ถูกแจ้งเวียน", "ผู้ทิ้งงาน",
            "นิติบุคคล", "จดทะเบียน", "ใบอนุญาต",
        ],
        "section_patterns": [
            r"มาตรา\s*[๖6][๕5]",  # 65
            r"มาตรา\s*[๖6][๖6]",  # 66
            r"ข้อ\s*[๑1][๖6]",
            r"ข้อ\s*[๑1][๗7]",
        ],
    },
    "evaluation_criteria": {
        "name": "เกณฑ์การพิจารณา",
        "keywords": [
            "หลักเกณฑ์.*พิจารณา", "เกณฑ์ราคา", "เกณฑ์คุณภาพ",
            "ราคาต่ำสุด", "ข้อเสนอ.*ดีที่สุด", "คะแนน",
            "Price Performance", "เกณฑ์ราคาประกอบเกณฑ์อื่น",
            "เทคนิค", "น้ำหนักคะแนน",
        ],
        "section_patterns": [
            r"ข้อ\s*[๘8][๒2]",  # ข้อ 82-87
            r"ข้อ\s*[๘8][๓3]",
            r"ข้อ\s*[๘8][๔4]",
            r"ข้อ\s*[๘8][๕5]",
            r"ข้อ\s*[๘8][๖6]",
            r"ข้อ\s*[๘8][๗7]",
        ],
    },
    "contract_penalty": {
        "name": "สัญญาและค่าปรับ",
        "keywords": [
            "สัญญา", "ทำสัญญา", "ลงนาม", "ข้อตกลง",
            "ค่าปรับ", "ร้อยละ", "ค่าเสียหาย",
            "แก้ไขสัญญา", "บอกเลิกสัญญา",
            "งวดงาน", "การส่งมอบ", "ตรวจรับ",
        ],
        "section_patterns": [
            r"มาตรา\s*[๙9][๓3]",  # 93-102
            r"มาตรา\s*[๙9][๔-๙4-9]",
            r"มาตรา\s*[๑1][๐0][๐-๒0-2]",
            r"ข้อ\s*[๑1][๖6][๐-๙0-9]",  # ข้อ 160+
        ],
    },
    "guarantee": {
        "name": "หลักประกัน",
        "keywords": [
            "หลักประกัน", "หลักประกันสัญญา", "หลักประกันซอง",
            "ค้ำประกัน", "หนังสือค้ำประกัน", "เงินสด",
            "ร้อยละห้า", "ร้อยละสิบ", "คืนหลักประกัน",
        ],
        "section_patterns": [
            r"มาตรา\s*[๑1][๐0][๓-๖3-6]",  # 103-106
            r"ข้อ\s*[๑1][๖6][๗7]",
            r"ข้อ\s*[๑1][๖6][๘8]",
        ],
    },
    "timeline_process": {
        "name": "ระยะเวลาและขั้นตอน",
        "keywords": [
            "ระยะเวลา", "วันทำการ", "กำหนดส่งมอบ",
            "แผนการจัดซื้อจัดจ้าง", "ประกาศเผยแพร่",
            "ยื่นข้อเสนอ", "เปิดซอง", "ประกาศผู้ชนะ",
            "ขั้นตอน", "กระบวนการ",
        ],
        "section_patterns": [
            r"ข้อ\s*[๑1][๑1]",  # ข้อ 11 แผน
            r"ข้อ\s*[๑1][๒2]",
            r"ข้อ\s*[๔4][๖-๙6-9]",  # ข้อ 46-49
        ],
    },
}

# ─────────────────────────────────────────────────────────────
# Section Splitting
# ─────────────────────────────────────────────────────────────
# Pattern to split document into sections (มาตรา, ข้อ, หมวด, บทที่)
SECTION_SPLIT_PATTERNS = [
    # พ.ร.บ. - มาตรา (Thai numerals)
    r'(?=\nมาตรา\s*[๐-๙]+)',
    # ระเบียบ - ข้อ (Thai numerals)
    r'(?=\nข้อ\s*[๐-๙]+)',
    # พ.ร.บ. - มาตรา (Arabic numerals from some PDFs)
    r'(?=\nมาตรา\s*\d+)',
    # ระเบียบ - ข้อ (Arabic)
    r'(?=\nข้อ\s*\d+)',
]


def split_into_sections(text: str) -> list:
    """Split document text into individual sections (มาตรา/ข้อ)"""
    sections = []

    # Detect document type: มาตรา-based or ข้อ-based
    mattra_count = len(re.findall(r'มาตรา\s*[๐-๙\d]+', text))
    kho_count = len(re.findall(r'(?<!\S)ข้อ\s*[๐-๙\d]+', text))

    if mattra_count >= 10:
        # Split by มาตรา (allow newline or start-of-text before)
        parts = re.split(r'(?=(?:^|\n)\s*มาตรา\s*[๐-๙\d]+)', text)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            match = re.match(r'\s*(มาตรา\s*[๐-๙\d]+)', part)
            if match:
                section_id = match.group(1).strip()
                sections.append({"section_id": section_id, "content": part})

    if kho_count >= 10 and len(sections) < 20:
        # Split by ข้อ - use lookahead that matches "ข้อ ๑" at line start or after newline
        sections = []  # Reset if มาตรา split was weak
        # Find all positions of "ข้อ N" that start a new provision
        # A new provision starts when "ข้อ N" is preceded by newline or is near start
        pattern = r'(?:(?<=\n)|(?<=^))\s*ข้อ\s*([๐-๙\d]+)'
        matches = list(re.finditer(pattern, text, re.MULTILINE))

        if not matches:
            # Try less strict: "ข้อ N" anywhere but only standalone (not inside word like "ตามข้อ")
            pattern = r'(?<![ก-๙a-z])ข้อ\s*([๐-๙\d]+)\s'
            all_matches = list(re.finditer(pattern, text))
            # Filter: only keep matches where the number is sequential or "ข้อ" starts a paragraph
            matches = []
            for m in all_matches:
                # Check if preceded by newline within 5 chars
                start = max(0, m.start() - 5)
                prefix = text[start:m.start()]
                if '\n' in prefix or m.start() < 5:
                    matches.append(m)

        if matches:
            for i, m in enumerate(matches):
                start = m.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                content = text[start:end].strip()
                num = m.group(1)
                section_id = f"ข้อ {num}"
                if len(content) > 20:  # Skip trivial matches
                    sections.append({"section_id": section_id, "content": content})

    # If no structured sections found, split by numbered headings
    if not sections:
        parts = re.split(r'\n(?=\d+\.\s)', text)
        for i, part in enumerate(parts):
            part = part.strip()
            if part and len(part) > 50:
                match = re.match(r'(\d+\.[\d.]*)', part)
                section_id = match.group(1) if match else f"ส่วน {i+1}"
                sections.append({"section_id": section_id, "content": part})

    # Fallback: split into chunks
    if not sections:
        paragraphs = text.split('\n\n')
        chunk = ""
        chunk_id = 1
        for para in paragraphs:
            chunk += para + "\n\n"
            if len(chunk) > 2000:
                sections.append({"section_id": f"ส่วน {chunk_id}", "content": chunk.strip()})
                chunk = ""
                chunk_id += 1
        if chunk.strip():
            sections.append({"section_id": f"ส่วน {chunk_id}", "content": chunk.strip()})

    return sections


def thai_to_arabic(text: str) -> str:
    """Convert Thai numerals to Arabic for comparison"""
    thai_digits = '๐๑๒๓๔๕๖๗๘๙'
    result = text
    for i, thai in enumerate(thai_digits):
        result = result.replace(thai, str(i))
    return result

# ─────────────────────────────────────────────────────────────
# Content Extraction & Classification
# ─────────────────────────────────────────────────────────────
def classify_section(section: dict) -> list:
    """Classify a section into focus areas based on content"""
    content = section["content"]
    content_lower = content.lower()
    section_id = section["section_id"]
    section_id_arabic = thai_to_arabic(section_id)

    matched_areas = []

    for area_key, area_config in FOCUS_AREAS.items():
        score = 0

        # Check section pattern match (strongest signal)
        for pattern in area_config["section_patterns"]:
            if re.search(pattern, section_id) or re.search(pattern, content[:100]):
                score += 10
                break

        # Check keyword matches
        for keyword in area_config["keywords"]:
            if re.search(keyword, content):
                score += 1

        # Threshold: need at least pattern match OR 3+ keyword matches
        if score >= 3:
            matched_areas.append((area_key, score))

    # Sort by score descending
    matched_areas.sort(key=lambda x: x[1], reverse=True)
    return [area for area, score in matched_areas]


def extract_tor_content_from_file(text_path: str) -> dict:
    """Extract TOR-relevant content from a single text file"""
    text_path = Path(text_path)
    filename = text_path.stem

    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Split into sections
    sections = split_into_sections(text)

    # Classify each section
    extracted = {
        "source_file": text_path.name,
        "source_path": str(text_path),
        "extraction_time": datetime.now().isoformat(),
        "total_sections": len(sections),
        "tor_relevant_sections": 0,
        "focus_areas": {key: [] for key in FOCUS_AREAS.keys()},
    }

    for section in sections:
        areas = classify_section(section)
        if areas:
            extracted["tor_relevant_sections"] += 1
            content = section["content"]
            # Truncate very long sections
            if len(content) > 3000:
                content = content[:3000] + "\n[...ตัดที่ 3000 ตัวอักษร...]"

            entry = {
                "section_id": section["section_id"],
                "content": content,
                "char_count": len(section["content"]),
            }

            # Add to primary area
            primary_area = areas[0]
            extracted["focus_areas"][primary_area].append(entry)

            # Cross-reference to secondary areas
            for secondary_area in areas[1:3]:  # Max 2 secondary
                xref = {
                    "section_id": section["section_id"],
                    "primary_area": primary_area,
                    "note": "cross-reference",
                }
                extracted["focus_areas"][secondary_area].append(xref)

    return extracted

# ─────────────────────────────────────────────────────────────
# Batch Processing & Output
# ─────────────────────────────────────────────────────────────
def get_high_relevance_files() -> list:
    """Get list of high-relevance files from analysis summary"""
    summary_path = Path(ANALYSIS_DIR) / "_analysis_summary.json"
    if not summary_path.exists():
        return []

    with open(summary_path, 'r', encoding='utf-8') as f:
        summary = json.load(f)

    return summary.get("by_relevance", {}).get("high", [])


def process_files(file_list: list, output_dir: str):
    """Process multiple files and save results"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create subdirectories for focus areas
    for area_key in FOCUS_AREAS.keys():
        (output_path / area_key).mkdir(exist_ok=True)

    all_results = []
    coverage_matrix = {key: {"files": [], "total_sections": 0, "total_chars": 0}
                       for key in FOCUS_AREAS.keys()}

    print(f"{'=' * 60}")
    print(f"TOR CONTENT EXTRACTION")
    print(f"Files: {len(file_list)} | Output: {output_dir}")
    print(f"{'=' * 60}\n")

    for txt_file in file_list:
        txt_path = Path(RAW_TEXT_DIR) / txt_file
        if not txt_path.exists():
            print(f"  [SKIP] Not found: {txt_file}")
            continue

        result = extract_tor_content_from_file(str(txt_path))
        all_results.append(result)

        # Update coverage matrix
        relevant_count = result["tor_relevant_sections"]
        total = result["total_sections"]
        print(f"  ✓ {txt_file[:55]}... ({relevant_count}/{total} relevant sections)")

        for area_key, sections in result["focus_areas"].items():
            real_sections = [s for s in sections if "note" not in s]
            if real_sections:
                coverage_matrix[area_key]["files"].append(txt_file)
                coverage_matrix[area_key]["total_sections"] += len(real_sections)
                coverage_matrix[area_key]["total_chars"] += sum(
                    s.get("char_count", 0) for s in real_sections
                )

        # Save per-file result
        result_path = output_path / f"{Path(txt_file).stem}_tor_extract.json"
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    # Save combined focus area files
    save_focus_area_files(all_results, output_path)

    # Save coverage matrix
    save_coverage_matrix(coverage_matrix, output_path)

    print(f"\n{'=' * 60}")
    print("EXTRACTION COMPLETE")
    print(f"  Files processed: {len(all_results)}")
    for area_key, data in coverage_matrix.items():
        name = FOCUS_AREAS[area_key]["name"]
        print(f"  {name}: {data['total_sections']} sections from {len(data['files'])} files")
    print(f"{'=' * 60}")


def save_focus_area_files(all_results: list, output_path: Path):
    """Combine all extractions by focus area into single files"""
    for area_key, area_config in FOCUS_AREAS.items():
        combined = {
            "focus_area": area_key,
            "name": area_config["name"],
            "extraction_time": datetime.now().isoformat(),
            "sources": [],
            "sections": [],
        }

        for result in all_results:
            sections = result["focus_areas"].get(area_key, [])
            real_sections = [s for s in sections if "note" not in s]
            if real_sections:
                combined["sources"].append(result["source_file"])
                for s in real_sections:
                    s_copy = dict(s)
                    s_copy["source_file"] = result["source_file"]
                    combined["sections"].append(s_copy)

        combined["total_sections"] = len(combined["sections"])
        combined["total_sources"] = len(combined["sources"])

        # Save
        area_path = output_path / area_key / f"_{area_key}_combined.json"
        with open(area_path, 'w', encoding='utf-8') as f:
            json.dump(combined, f, ensure_ascii=False, indent=2)


def save_coverage_matrix(coverage: dict, output_path: Path):
    """Save coverage matrix showing which focus areas have data from which files"""
    matrix = {
        "extraction_time": datetime.now().isoformat(),
        "focus_areas": {},
    }

    for area_key, data in coverage.items():
        matrix["focus_areas"][area_key] = {
            "name": FOCUS_AREAS[area_key]["name"],
            "file_count": len(data["files"]),
            "section_count": data["total_sections"],
            "char_count": data["total_chars"],
            "files": data["files"],
        }

    # Save JSON
    with open(output_path / "_coverage_matrix.json", 'w', encoding='utf-8') as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)

    # Save readable version
    with open(output_path / "_coverage_matrix.txt", 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("TOR CONTENT COVERAGE MATRIX\n")
        f.write(f"วันที่: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        for area_key, info in matrix["focus_areas"].items():
            f.write(f"{'─' * 70}\n")
            f.write(f"📋 {info['name']} ({area_key})\n")
            f.write(f"   Sections: {info['section_count']} | ")
            f.write(f"Files: {info['file_count']} | ")
            f.write(f"Chars: {info['char_count']:,}\n")
            f.write(f"   Sources:\n")
            for fname in info["files"]:
                f.write(f"     - {fname}\n")
            f.write("\n")

# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Extract TOR-relevant content")
    parser.add_argument('--file', '-f', help='Extract from single text file')
    parser.add_argument('--all', action='store_true', help='Process all files (not just high-relevance)')
    parser.add_argument('--output', '-o', default=OUTPUT_DIR)
    args = parser.parse_args()

    if args.file:
        result = extract_tor_content_from_file(args.file)
        print(json.dumps({
            "source_file": result["source_file"],
            "total_sections": result["total_sections"],
            "tor_relevant_sections": result["tor_relevant_sections"],
            "focus_areas_summary": {
                k: len([s for s in v if "note" not in s])
                for k, v in result["focus_areas"].items()
            }
        }, ensure_ascii=False, indent=2))
        return

    if args.all:
        # Process all txt files
        raw_path = Path(RAW_TEXT_DIR)
        file_list = [f.name for f in sorted(raw_path.glob("*.txt")) if not f.name.startswith('_')]
    else:
        # Process only high-relevance files
        file_list = get_high_relevance_files()
        if not file_list:
            # Fallback: all files
            raw_path = Path(RAW_TEXT_DIR)
            file_list = [f.name for f in sorted(raw_path.glob("*.txt")) if not f.name.startswith('_')]

    process_files(file_list, args.output)


if __name__ == "__main__":
    main()
