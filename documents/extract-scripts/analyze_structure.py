# -*- coding: utf-8 -*-
"""
analyze_structure.py — Document Structure Analysis with LLM
วิเคราะห์โครงสร้างเนื้อหาเอกสารกฎหมายจัดซื้อจัดจ้างด้วย LLM (Anthropic Claude / OpenAI GPT)

- จำแนกประเภทเอกสาร
- สร้าง Table of Contents
- ระบุมาตรา/ข้อที่เกี่ยวกับ TOR
- สรุปสาระสำคัญ
- ระบุความเกี่ยวข้องกับ: วิธีจัดซื้อ, ประเภทพัสดุ, ขั้นตอน TOR

Usage:
  python analyze_structure.py                    # analyze ทุกไฟล์ใน raw_text/
  python analyze_structure.py --file <txt>       # analyze ไฟล์เดียว
  python analyze_structure.py --provider openai  # ใช้ OpenAI แทน Anthropic
"""

import os
import sys
import json
import argparse
import time
from pathlib import Path
from datetime import datetime

sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable


# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
_RESEARCH = Path(__file__).resolve().parents[1] / "research"
DEFAULT_INPUT_DIR = str(_RESEARCH / "raw_text")
DEFAULT_OUTPUT_DIR = str(_RESEARCH / "analysis")

# Max chars to send to LLM (to fit within context window)
MAX_TEXT_CHARS = 80000  # ~20K tokens for Thai text


# ─────────────────────────────────────────────────────────────
# LLM Prompt
# ─────────────────────────────────────────────────────────────
ANALYSIS_PROMPT = """คุณเป็นผู้เชี่ยวชาญด้านกฎหมายจัดซื้อจัดจ้างภาครัฐไทย กรุณาวิเคราะห์เอกสารต่อไปนี้และตอบเป็น JSON format ตามโครงสร้างที่กำหนด

## คำสั่ง:
วิเคราะห์เอกสารที่ให้มาแล้วตอบเป็น JSON ดังนี้:

```json
{
  "document_type": "(พระราชบัญญัติ|กฎกระทรวง|ระเบียบ|คู่มือ|หนังสือเวียน|เอกสารวิชาการ|รายงาน|อื่นๆ)",
  "title": "ชื่อเต็มของเอกสาร",
  "short_title": "ชื่อย่อ",
  "year": "พ.ศ. ที่ออก",
  "issuer": "หน่วยงานที่ออก",
  "table_of_contents": [
    {"level": 1, "section_id": "มาตรา/ข้อ/หมวด", "title": "ชื่อหัวข้อ"},
    ...
  ],
  "summary": "สรุปสาระสำคัญ 3-5 ประเด็น (เขียนเป็น paragraph)",
  "key_provisions": [
    {"section_id": "มาตรา/ข้อ", "content_summary": "สรุปเนื้อหา", "relevance": "high|medium|low"}
  ],
  "tor_relevance": {
    "overall_relevance": "high|medium|low",
    "relevant_sections": ["มาตรา/ข้อที่เกี่ยวกับ TOR โดยตรง"],
    "procurement_methods": ["วิธีจัดซื้อที่เกี่ยวข้อง: ประกาศเชิญชวนทั่วไป|คัดเลือก|เฉพาะเจาะจง|ทุกวิธี"],
    "goods_types": ["ประเภทพัสดุที่เกี่ยวข้อง: สินค้า|งานบริการ|งานก่อสร้าง|จ้างที่ปรึกษา|จ้างออกแบบ/ควบคุมงาน|ทุกประเภท"],
    "tor_sections_affected": ["ส่วนของ TOR ที่ได้รับผลกระทบ: ขอบเขตงาน|คุณสมบัติผู้ยื่น|เกณฑ์พิจารณา|ราคากลาง|สัญญา|ค่าปรับ|หลักประกัน|ระยะเวลา|อื่นๆ"]
  },
  "related_documents": ["เอกสารอื่นที่เกี่ยวข้อง"],
  "notes": "หมายเหตุเพิ่มเติม (ถ้ามี)"
}
```

## กฎในการวิเคราะห์:
1. ตอบเป็น JSON เท่านั้น ไม่ต้องมีข้อความอื่นนอก JSON
2. table_of_contents ให้ระบุเฉพาะหัวข้อหลักๆ (ไม่เกิน 30 รายการ)
3. key_provisions ให้เน้นเฉพาะข้อที่เกี่ยวข้องกับการจัดทำ TOR (ไม่เกิน 15 รายการ)
4. relevance = high หมายถึงเกี่ยวข้องโดยตรงกับการร่าง TOR
5. ถ้าเอกสารเป็น OCR อาจมีตัวอักษรผิดบ้าง ให้พยายามตีความให้ถูกต้อง

## เอกสารที่ต้องวิเคราะห์:
"""


# ─────────────────────────────────────────────────────────────
# LLM Clients
# ─────────────────────────────────────────────────────────────
def call_anthropic(text: str, max_retries: int = 3) -> str:
    """Call Anthropic Claude API"""
    import anthropic

    client = anthropic.Anthropic()  # Uses ANTHROPIC_API_KEY env var

    for attempt in range(max_retries):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=8000,
                messages=[
                    {
                        "role": "user",
                        "content": ANALYSIS_PROMPT + text
                    }
                ]
            )
            return message.content[0].text
        except Exception as e:
            if "rate_limit" in str(e).lower() or "overloaded" in str(e).lower():
                wait = (attempt + 1) * 30
                print(f"    [Rate limit] Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise e

    raise Exception("Max retries exceeded for Anthropic API")


def call_openai(text: str, max_retries: int = 3) -> str:
    """Call OpenAI GPT API"""
    from openai import OpenAI

    client = OpenAI()  # Uses OPENAI_API_KEY env var

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=8000,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert in Thai government procurement law. Always respond in valid JSON format."
                    },
                    {
                        "role": "user",
                        "content": ANALYSIS_PROMPT + text
                    }
                ],
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        except Exception as e:
            if "rate_limit" in str(e).lower():
                wait = (attempt + 1) * 30
                print(f"    [Rate limit] Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise e

    raise Exception("Max retries exceeded for OpenAI API")


# ─────────────────────────────────────────────────────────────
# Analysis Logic
# ─────────────────────────────────────────────────────────────
def truncate_text(text: str, max_chars: int = MAX_TEXT_CHARS) -> str:
    """Truncate text to fit LLM context, trying to break at paragraph"""
    if len(text) <= max_chars:
        return text

    # Try to break at a paragraph boundary
    truncated = text[:max_chars]
    last_para = truncated.rfind('\n\n')
    if last_para > max_chars * 0.8:
        truncated = truncated[:last_para]

    return truncated + f"\n\n[... เอกสารถูกตัดที่ {len(truncated):,} ตัวอักษร จากทั้งหมด {len(text):,} ตัวอักษร ...]"


def parse_llm_response(response_text: str) -> dict:
    """Parse LLM response to JSON, handling common issues"""
    # Try direct parse
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass

    # Try extracting JSON from markdown code block
    import re
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding JSON object
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Return error structure
    return {
        "error": "Failed to parse LLM response",
        "raw_response": response_text[:2000]
    }


def analyze_document(text_path: str, output_dir: str, provider: str = "anthropic") -> dict:
    """Analyze a single document"""
    text_path = Path(text_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = text_path.stem
    output_path = output_dir / f"{filename}_structure.json"

    # Skip if already analyzed
    if output_path.exists():
        print(f"    [SKIP] Already analyzed: {filename[:50]}...")
        with open(output_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Read text
    with open(text_path, 'r', encoding='utf-8') as f:
        text = f.read()

    # Truncate if needed
    original_len = len(text)
    text = truncate_text(text)

    # Call LLM
    try:
        if provider == "anthropic":
            response = call_anthropic(text)
        elif provider == "openai":
            response = call_openai(text)
        else:
            raise ValueError(f"Unknown provider: {provider}")

        # Parse response
        analysis = parse_llm_response(response)

    except Exception as e:
        analysis = {
            "error": str(e),
            "document_type": "unknown",
            "title": filename,
        }

    # Add metadata
    analysis["_metadata"] = {
        "source_file": text_path.name,
        "analysis_time": datetime.now().isoformat(),
        "provider": provider,
        "original_char_count": original_len,
        "analyzed_char_count": len(text),
        "truncated": original_len > MAX_TEXT_CHARS,
    }

    # Save
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    return analysis


# ─────────────────────────────────────────────────────────────
# Batch Processing
# ─────────────────────────────────────────────────────────────
def process_all(input_dir: str, output_dir: str, provider: str = "anthropic"):
    """Analyze all text files"""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Get text files (exclude report files starting with _)
    txt_files = sorted([f for f in input_path.glob("*.txt") if not f.name.startswith('_')])

    if not txt_files:
        print(f"[!] No text files found in: {input_dir}")
        return

    print(f"Found {len(txt_files)} text files to analyze")
    print(f"Provider: {provider}")
    print(f"Output: {output_dir}")
    print("=" * 60)

    results = []
    for txt_file in tqdm(txt_files, desc="Analyzing"):
        print(f"\n  → {txt_file.name[:60]}...")
        analysis = analyze_document(str(txt_file), output_dir, provider)
        results.append({
            "file": txt_file.name,
            "document_type": analysis.get("document_type", "unknown"),
            "title": analysis.get("title", txt_file.stem),
            "tor_relevance": analysis.get("tor_relevance", {}).get("overall_relevance", "unknown"),
            "error": analysis.get("error"),
        })

        # Rate limit protection
        time.sleep(2)

    # Generate summary
    generate_summary(results, output_path)


def generate_summary(results: list, output_dir: Path):
    """Generate summary table of all analyses"""
    summary = {
        "analysis_date": datetime.now().isoformat(),
        "total_files": len(results),
        "by_type": {},
        "by_relevance": {"high": [], "medium": [], "low": [], "unknown": []},
        "files": results,
    }

    for r in results:
        doc_type = r.get("document_type", "unknown")
        if doc_type not in summary["by_type"]:
            summary["by_type"][doc_type] = []
        summary["by_type"][doc_type].append(r["file"])

        relevance = r.get("tor_relevance", "unknown")
        if relevance in summary["by_relevance"]:
            summary["by_relevance"][relevance].append(r["file"])
        else:
            summary["by_relevance"]["unknown"].append(r["file"])

    # Save summary JSON
    summary_path = output_dir / "_analysis_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Save readable summary
    txt_path = output_dir / "_analysis_summary.txt"
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("DOCUMENT STRUCTURE ANALYSIS SUMMARY\n")
        f.write(f"วันที่: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"ไฟล์ทั้งหมด: {len(results)}\n\n")

        f.write("─" * 70 + "\n")
        f.write("จำแนกตามประเภทเอกสาร:\n")
        f.write("─" * 70 + "\n")
        for doc_type, files in summary["by_type"].items():
            f.write(f"\n  [{doc_type}] ({len(files)} ไฟล์)\n")
            for fname in files:
                f.write(f"    - {fname}\n")

        f.write("\n" + "─" * 70 + "\n")
        f.write("จำแนกตามความเกี่ยวข้องกับ TOR:\n")
        f.write("─" * 70 + "\n")
        for level in ["high", "medium", "low", "unknown"]:
            files = summary["by_relevance"][level]
            if files:
                f.write(f"\n  [{level.upper()}] ({len(files)} ไฟล์)\n")
                for fname in files:
                    f.write(f"    - {fname}\n")

    print(f"\n{'=' * 60}")
    print("ANALYSIS COMPLETE")
    print(f"  Summary: {summary_path}")
    print(f"{'=' * 60}")


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Analyze document structure using LLM"
    )
    parser.add_argument('--input', '-i', default=DEFAULT_INPUT_DIR,
                        help='Input directory with text files')
    parser.add_argument('--output', '-o', default=DEFAULT_OUTPUT_DIR,
                        help='Output directory for analysis results')
    parser.add_argument('--file', '-f',
                        help='Analyze single text file')
    parser.add_argument('--provider', '-p', default='anthropic',
                        choices=['anthropic', 'openai'],
                        help='LLM provider (default: anthropic)')

    args = parser.parse_args()

    if args.file:
        print(f"Analyzing single file: {args.file}")
        result = analyze_document(args.file, args.output, args.provider)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        process_all(args.input, args.output, args.provider)


if __name__ == "__main__":
    main()
