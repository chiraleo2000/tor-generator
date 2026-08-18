# -*- coding: utf-8 -*-
"""
analyze_structure_local.py — Document Structure Analysis (Local/Offline)
วิเคราะห์โครงสร้างเอกสารด้วย regex/pattern matching — ไม่ต้องใช้ LLM API

ใช้เมื่อไม่มี API credit หรือต้องการ pre-analysis ก่อนส่ง LLM

Usage:
  python analyze_structure_local.py              # analyze ทุกไฟล์
  python analyze_structure_local.py --file <txt> # analyze ไฟล์เดียว
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
_RESEARCH = Path(__file__).resolve().parents[1] / "research"
DEFAULT_INPUT_DIR = str(_RESEARCH / "raw_text")
DEFAULT_OUTPUT_DIR = str(_RESEARCH / "analysis")

# Document type detection patterns
DOC_TYPE_PATTERNS = {
    "พระราชบัญญัติ": [
        r"พระราชบัญญัติ",
        r"พ\.?ร\.?บ\.?",
        r"มาตรา\s*\d+",
    ],
    "กฎกระทรวง": [
        r"กฎกระทรวง",
        r"อาศัยอำนาจตามความในมาตรา",
    ],
    "ระเบียบ": [
        r"ระเบียบกระทรวงการคลัง",
        r"ระเบียบ.*ว่าด้วย",
    ],
    "หนังสือเวียน": [
        r"ด่วนที่สุด",
        r"ที่\s*กค",
        r"เรียน\s*(ปลัดกระทรวง|อธิบดี|หัวหน้า)",
        r"กวจ|กวพ",
    ],
    "คู่มือ": [
        r"คู่มือ",
        r"แนวทางปฏิบัติ",
        r"แนวปฏิบัติ",
    ],
    "เอกสารวิชาการ": [
        r"บทที่\s*\d+",
        r"บทนำ",
        r"บทสรุป",
    ],
}

# TOR relevance keywords
TOR_KEYWORDS = {
    "high": [
        "ขอบเขตของงาน", "TOR", "ร่างขอบเขต", "คุณลักษณะเฉพาะ",
        "เงื่อนไขการจัดซื้อจัดจ้าง", "หลักเกณฑ์การพิจารณา",
        "รายละเอียดคุณลักษณะ", "ข้อกำหนดและขอบเขต",
    ],
    "medium": [
        "การจัดซื้อจัดจ้าง", "วิธีประกาศเชิญชวน", "วิธีคัดเลือก",
        "วิธีเฉพาะเจาะจง", "e-bidding", "ราคากลาง",
        "คุณสมบัติ.*ผู้เสนอราคา", "หลักประกัน", "ค่าปรับ",
        "สัญญา", "คณะกรรมการ", "ผู้ประกอบการ",
    ],
    "low": [
        "ทะเบียน", "ที่ปรึกษา", "ผู้ทิ้งงาน", "อุทธรณ์",
    ],
}

# Section patterns for Thai legal documents
SECTION_PATTERNS = [
    (r"^มาตรา\s*(\d+)", "มาตรา"),
    (r"^ข้อ\s*(\d+)", "ข้อ"),
    (r"^หมวด\s*(\d+)", "หมวด"),
    (r"^ส่วนที่\s*(\d+)", "ส่วนที่"),
    (r"^บทที่\s*(\d+)", "บทที่"),
    (r"^(\d+)\.\s+", "หัวข้อ"),
    (r"^(\d+\.\d+)\s+", "หัวข้อย่อย"),
]

# Procurement method keywords
METHOD_KEYWORDS = {
    "ประกาศเชิญชวนทั่วไป": ["ประกาศเชิญชวนทั่วไป", "e-bidding", "e-market", "ประกวดราคา", "สอบราคา"],
    "คัดเลือก": ["วิธีคัดเลือก", "เชิญชวนเฉพาะ"],
    "เฉพาะเจาะจง": ["วิธีเฉพาะเจาะจง", "เชิญชวนผู้ประกอบการรายใด"],
}

# Goods type keywords
GOODS_KEYWORDS = {
    "สินค้า": ["วัสดุ", "ครุภัณฑ์", "สินค้า", "ที่ดิน", "สิ่งปลูกสร้าง"],
    "งานบริการ": ["จ้างบริการ", "จ้างเหมา", "จ้างทำของ", "งานบริการ"],
    "งานก่อสร้าง": ["ก่อสร้าง", "ซ่อมแซม", "ต่อเติม", "ปรับปรุง", "รื้อถอน"],
    "จ้างที่ปรึกษา": ["จ้างที่ปรึกษา", "ให้คำปรึกษา", "ผู้เชี่ยวชาญ"],
    "จ้างออกแบบ/ควบคุมงาน": ["จ้างออกแบบ", "ควบคุมงานก่อสร้าง", "สถาปัตยกรรม", "วิศวกรรม"],
}

# ─────────────────────────────────────────────────────────────
# Analysis Functions
# ─────────────────────────────────────────────────────────────
def detect_document_type(text: str, filename: str) -> str:
    """จำแนกประเภทเอกสารจาก content + filename"""
    # Check filename first
    fname_lower = filename.lower()
    if "พรบ" in fname_lower or "พระราชบัญญัติ" in fname_lower:
        return "พระราชบัญญัติ"
    if "กฎกระทรวง" in fname_lower:
        return "กฎกระทรวง"
    if "ระเบียบ" in fname_lower:
        return "ระเบียบ"
    if "หนังสือ" in fname_lower or "กค" in fname_lower:
        return "หนังสือเวียน"
    if "คู่มือ" in fname_lower:
        return "คู่มือ"

    # Check content patterns
    first_2000 = text[:2000]
    scores = {}
    for doc_type, patterns in DOC_TYPE_PATTERNS.items():
        score = 0
        for pattern in patterns:
            matches = re.findall(pattern, first_2000)
            score += len(matches)
        scores[doc_type] = score

    if scores:
        best_type = max(scores, key=scores.get)
        if scores[best_type] > 0:
            return best_type

    return "อื่นๆ"


def extract_sections(text: str) -> list:
    """Extract section headings from text"""
    sections = []
    lines = text.split('\n')

    for line in lines:
        line = line.strip()
        if not line or len(line) > 200:
            continue

        for pattern, section_type in SECTION_PATTERNS:
            match = re.match(pattern, line)
            if match:
                section_id = f"{section_type} {match.group(1)}"
                # Get title (rest of line after the match)
                title = line[match.end():].strip()
                if not title:
                    title = line
                sections.append({
                    "level": 1 if section_type in ["หมวด", "บทที่"] else 2,
                    "section_id": section_id,
                    "title": title[:100],
                })
                break

    # Deduplicate and limit
    seen = set()
    unique_sections = []
    for s in sections:
        key = s["section_id"]
        if key not in seen:
            seen.add(key)
            unique_sections.append(s)

    return unique_sections[:50]


def detect_tor_relevance(text: str) -> dict:
    """Detect TOR relevance level and related aspects"""
    text_lower = text.lower()

    # Count keyword hits
    high_hits = sum(1 for kw in TOR_KEYWORDS["high"] if kw in text)
    medium_hits = sum(1 for kw in TOR_KEYWORDS["medium"] if kw in text)

    # Determine overall relevance
    if high_hits >= 2:
        overall = "high"
    elif high_hits >= 1 or medium_hits >= 3:
        overall = "medium"
    elif medium_hits >= 1:
        overall = "medium"
    else:
        overall = "low"

    # Detect procurement methods
    methods = []
    for method, keywords in METHOD_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            methods.append(method)
    if not methods:
        methods = ["ทุกวิธี"]

    # Detect goods types
    goods = []
    for gtype, keywords in GOODS_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            goods.append(gtype)
    if not goods:
        goods = ["ทุกประเภท"]

    # Detect TOR sections affected
    tor_sections = []
    tor_section_map = {
        "ขอบเขตงาน": ["ขอบเขต", "รายละเอียดงาน", "scope"],
        "คุณสมบัติผู้ยื่น": ["คุณสมบัติ", "ผู้เสนอราคา", "ผู้ยื่นข้อเสนอ"],
        "เกณฑ์พิจารณา": ["หลักเกณฑ์", "เกณฑ์.*พิจารณา", "คะแนน"],
        "ราคากลาง": ["ราคากลาง", "วงเงิน", "งบประมาณ"],
        "สัญญา": ["สัญญา", "ข้อตกลง"],
        "ค่าปรับ": ["ค่าปรับ", "ปรับ.*ร้อยละ"],
        "หลักประกัน": ["หลักประกัน", "ค้ำประกัน"],
        "ระยะเวลา": ["ระยะเวลา", "กำหนดส่งมอบ", "แล้วเสร็จ"],
    }
    for section, keywords in tor_section_map.items():
        if any(re.search(kw, text) for kw in keywords):
            tor_sections.append(section)

    return {
        "overall_relevance": overall,
        "relevant_sections": [],  # Will be filled by section analysis
        "procurement_methods": methods,
        "goods_types": goods,
        "tor_sections_affected": tor_sections,
    }

def extract_year(text: str, filename: str) -> str:
    """Extract year (พ.ศ.) from document"""
    # Try filename first
    year_match = re.search(r'(?:พ\.?ศ\.?\s*)?(\d{4})', filename)
    if year_match and int(year_match.group(1)) >= 2500:
        return year_match.group(1)

    # Try content
    year_matches = re.findall(r'พ\.?ศ\.?\s*(\d{4})', text[:3000])
    if year_matches:
        return year_matches[0]

    return "ไม่ระบุ"


def generate_summary(text: str, doc_type: str) -> str:
    """Generate basic summary from first few paragraphs"""
    # Take first meaningful paragraphs
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip() and len(p.strip()) > 30]

    # Skip headers/metadata
    content_paras = []
    for p in paragraphs[:10]:
        if len(p) > 50 and not p.startswith('---'):
            content_paras.append(p)
        if len(content_paras) >= 3:
            break

    if content_paras:
        summary = ' '.join(content_paras)
        if len(summary) > 500:
            summary = summary[:497] + "..."
        return summary

    return "ไม่สามารถสร้างสรุปอัตโนมัติได้"


def find_tor_relevant_sections(text: str, sections: list) -> list:
    """Find sections directly related to TOR drafting"""
    relevant = []
    tor_keywords = TOR_KEYWORDS["high"] + TOR_KEYWORDS["medium"][:5]

    for section in sections:
        section_title = section.get("title", "")
        section_id = section.get("section_id", "")
        for kw in tor_keywords:
            if kw in section_title:
                relevant.append(section_id)
                break

    return relevant[:10]


def analyze_document_local(text_path: str, output_dir: str) -> dict:
    """Analyze a single document locally"""
    text_path = Path(text_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = text_path.stem
    output_path = output_dir / f"{filename}_structure.json"

    # Read text
    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Analyze
    doc_type = detect_document_type(text, filename)
    sections = extract_sections(text)
    tor_relevance = detect_tor_relevance(text)
    tor_relevance["relevant_sections"] = find_tor_relevant_sections(text, sections)
    year = extract_year(text, filename)
    summary = generate_summary(text, doc_type)

    analysis = {
        "document_type": doc_type,
        "title": filename,
        "short_title": filename[:50],
        "year": year,
        "issuer": "กรมบัญชีกลาง" if "กค" in filename or "บัญชีกลาง" in filename else "กระทรวงการคลัง",
        "table_of_contents": sections,
        "summary": summary,
        "key_provisions": [],  # Would need LLM for detailed extraction
        "tor_relevance": tor_relevance,
        "related_documents": [],
        "notes": f"วิเคราะห์ด้วย local pattern matching (ไม่ใช้ LLM)",
        "_metadata": {
            "source_file": text_path.name,
            "analysis_time": datetime.now().isoformat(),
            "provider": "local",
            "char_count": len(text),
            "section_count": len(sections),
        }
    }

    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    return analysis

# ─────────────────────────────────────────────────────────────
# Batch Processing & Summary
# ─────────────────────────────────────────────────────────────
def process_all(input_dir: str, output_dir: str):
    """Analyze all text files"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    txt_files = sorted([f for f in input_path.glob("*.txt") if not f.name.startswith('_')])

    if not txt_files:
        print(f"[!] No text files found in: {input_dir}")
        return

    print(f"{'=' * 60}")
    print(f"LOCAL DOCUMENT STRUCTURE ANALYSIS")
    print(f"Files: {len(txt_files)} | Output: {output_dir}")
    print(f"{'=' * 60}")

    results = []
    for txt_file in txt_files:
        analysis = analyze_document_local(str(txt_file), output_dir)
        doc_type = analysis["document_type"]
        relevance = analysis["tor_relevance"]["overall_relevance"]
        sections_count = len(analysis["table_of_contents"])
        print(f"  ✓ [{doc_type:10s}] [{relevance:6s}] {txt_file.name[:55]}... ({sections_count} sections)")

        results.append({
            "file": txt_file.name,
            "document_type": doc_type,
            "title": analysis["title"],
            "year": analysis["year"],
            "tor_relevance": relevance,
            "procurement_methods": analysis["tor_relevance"]["procurement_methods"],
            "goods_types": analysis["tor_relevance"]["goods_types"],
            "tor_sections_affected": analysis["tor_relevance"]["tor_sections_affected"],
            "section_count": sections_count,
            "char_count": analysis["_metadata"]["char_count"],
        })

    generate_summary_report(results, output_path)


def generate_summary_report(results: list, output_dir: Path):
    """Generate comprehensive summary"""
    summary = {
        "analysis_date": datetime.now().isoformat(),
        "provider": "local",
        "total_files": len(results),
        "by_type": {},
        "by_relevance": {"high": [], "medium": [], "low": []},
        "files": results,
    }

    for r in results:
        doc_type = r["document_type"]
        if doc_type not in summary["by_type"]:
            summary["by_type"][doc_type] = []
        summary["by_type"][doc_type].append(r["file"])

        relevance = r["tor_relevance"]
        if relevance in summary["by_relevance"]:
            summary["by_relevance"][relevance].append(r["file"])

    # Save JSON
    with open(output_dir / "_analysis_summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Save readable report
    with open(output_dir / "_analysis_summary.txt", 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("DOCUMENT STRUCTURE ANALYSIS SUMMARY (LOCAL)\n")
        f.write(f"วันที่: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"จำนวนไฟล์: {len(results)}\n")
        f.write("=" * 70 + "\n\n")

        # By document type
        f.write("─" * 70 + "\n")
        f.write("จำแนกตามประเภทเอกสาร:\n")
        f.write("─" * 70 + "\n")
        for doc_type, files in summary["by_type"].items():
            f.write(f"\n  📄 {doc_type} ({len(files)} ไฟล์)\n")
            for fname in files:
                f.write(f"     - {fname}\n")

        # By TOR relevance
        f.write("\n" + "─" * 70 + "\n")
        f.write("จำแนกตามความเกี่ยวข้องกับ TOR:\n")
        f.write("─" * 70 + "\n")
        for level, label in [("high", "สูง"), ("medium", "ปานกลาง"), ("low", "ต่ำ")]:
            files = summary["by_relevance"][level]
            f.write(f"\n  🔴 ความเกี่ยวข้อง{label} ({len(files)} ไฟล์)\n")
            for fname in files:
                f.write(f"     - {fname}\n")

        # Detail table
        f.write("\n" + "─" * 70 + "\n")
        f.write("รายละเอียดแต่ละไฟล์:\n")
        f.write("─" * 70 + "\n\n")
        for i, r in enumerate(results, 1):
            f.write(f"  {i:2d}. {r['file']}\n")
            f.write(f"      ประเภท: {r['document_type']} | ปี: {r['year']} | ")
            f.write(f"TOR relevance: {r['tor_relevance']}\n")
            f.write(f"      วิธีจัดซื้อ: {', '.join(r['procurement_methods'])}\n")
            f.write(f"      ประเภทพัสดุ: {', '.join(r['goods_types'])}\n")
            f.write(f"      ส่วน TOR: {', '.join(r['tor_sections_affected'])}\n")
            f.write(f"      Sections: {r['section_count']} | Chars: {r['char_count']:,}\n\n")

    print(f"\n{'=' * 60}")
    print(f"ANALYSIS COMPLETE")
    print(f"  Total: {len(results)} files analyzed")
    print(f"  High relevance: {len(summary['by_relevance']['high'])}")
    print(f"  Medium relevance: {len(summary['by_relevance']['medium'])}")
    print(f"  Low relevance: {len(summary['by_relevance']['low'])}")
    print(f"  Report: {output_dir / '_analysis_summary.txt'}")
    print(f"{'=' * 60}")


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Local document structure analysis")
    parser.add_argument('--input', '-i', default=DEFAULT_INPUT_DIR)
    parser.add_argument('--output', '-o', default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--file', '-f', help='Analyze single file')
    args = parser.parse_args()

    if args.file:
        result = analyze_document_local(args.file, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        process_all(args.input, args.output)


if __name__ == "__main__":
    main()
