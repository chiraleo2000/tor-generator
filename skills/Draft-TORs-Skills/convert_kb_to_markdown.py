"""
Convert knowledge-base JSON files to Markdown for AI tool skills.

Usage:
    python convert_kb_to_markdown.py

This script reads the 7 topic JSON files from documents/knowledge-base/ and creates
clean markdown versions in each platform's skill folder.
"""

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KB_DIR = ROOT / "documents" / "knowledge-base"
SKILLS_DIR = Path(__file__).parent  # skills/Draft-TORs-Skills

# Topic folders with their combined JSON files
TOPICS = {
    "contract_penalty": "สัญญาและค่าปรับ",
    "definitions": "นิยามและประเภท",
    "evaluation_criteria": "เกณฑ์การพิจารณา",
    "guarantee": "หลักประกัน",
    "procurement_methods": "วิธีจัดซื้อจัดจ้าง",
    "qualifications": "คุณสมบัติผู้ยื่นข้อเสนอ",
    "timeline_process": "ระยะเวลาและกระบวนการ",
}

# Output directories (platform skill packs under skills/)
SKILLS_ROOT = ROOT / "skills"
OUTPUT_DIRS = [
    SKILLS_ROOT / "Draft-TORs-Skills" / "claude" / "tor-procurement" / "references" / "knowledge",
    SKILLS_ROOT / "Draft-TORs-Skills" / "chatgpt" / "tor-procurement" / "knowledge",
    SKILLS_ROOT / "Draft-TORs-Skills" / "gemini-notebooklm" / "sources",
    SKILLS_ROOT / "Draft-TORs-Skills" / "hermes-agent" / "tor-procurement" / "references" / "knowledge",
    SKILLS_ROOT / "check-TORs-Skills" / "claude" / "tor-review" / "references",
    SKILLS_ROOT / "check-TORs-Skills" / "chatgpt" / "tor-review" / "knowledge",
    SKILLS_ROOT / "check-TORs-Skills" / "gemini-notebooklm" / "sources",
    SKILLS_ROOT / "check-TORs-Skills" / "hermes-agent" / "tor-review" / "references",
]

MAX_SECTIONS = 8  # Max sections per topic to keep files manageable
MAX_CHARS_PER_SECTION = 2000  # Truncate very long sections


def load_topic(topic_key):
    """Load a topic's combined JSON file."""
    topic_dir = KB_DIR / topic_key
    json_file = topic_dir / f"_{topic_key}_combined.json"
    if not json_file.exists():
        return None
    with open(json_file, "r", encoding="utf-8") as f:
        return json.load(f)


def deduplicate_sections(sections):
    """Remove duplicate sections (same section_id + same content)."""
    seen = set()
    unique = []
    for s in sections:
        key = (s.get("section_id", ""), s.get("content", "")[:200])
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def convert_to_markdown(data, topic_key, thai_name):
    """Convert JSON data to markdown format."""
    lines = []
    lines.append(f"# {thai_name}")
    lines.append(f"> Source: knowledge-base/{topic_key}/_{topic_key}_combined.json")
    lines.append(f"> Sources: {', '.join(data.get('sources', [])[:5])}")
    lines.append("")

    sections = data.get("sections", [])
    sections = deduplicate_sections(sections)

    # Take most important sections (first N unique ones)
    for i, section in enumerate(sections[:MAX_SECTIONS]):
        section_id = section.get("section_id", f"Section {i+1}")
        content = section.get("content", "")

        # Clean up content
        content = content.replace("[...ตัดที่ 3000 ตัวอักษร...]", "")
        content = content.strip()

        # Truncate very long sections
        if len(content) > MAX_CHARS_PER_SECTION:
            content = content[:MAX_CHARS_PER_SECTION] + "\n\n[...truncated...]"

        lines.append(f"## {section_id}")
        lines.append("")
        lines.append(content)
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    print("Converting knowledge-base to markdown for AI tool skills...")

    for topic_key, thai_name in TOPICS.items():
        print(f"  Processing: {topic_key} ({thai_name})")
        data = load_topic(topic_key)
        if data is None:
            print(f"    WARNING: No data found for {topic_key}")
            continue

        md_content = convert_to_markdown(data, topic_key, thai_name)
        filename = f"kb_{topic_key}.md"

        for output_dir in OUTPUT_DIRS:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / filename
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(md_content)

        print(f"    Written to {len(OUTPUT_DIRS)} locations ({filename})")

    # Also copy decision rules and reference summary
    print("  Copying decision rules and reference summary...")
    decision_files = [
        KB_DIR / "04-decision-rules" / "method_selection.json",
        KB_DIR / "04-decision-rules" / "template_selection.json",
        KB_DIR / "04-decision-rules" / "document_checklist.json",
    ]
    ref_file = KB_DIR / "05-reference-summary" / "tor_reference_complete.md"

    import shutil
    for output_dir in OUTPUT_DIRS:
        for src in decision_files:
            if src.exists():
                shutil.copy2(src, output_dir / src.name)
        if ref_file.exists():
            shutil.copy2(ref_file, output_dir / ref_file.name)

    print("Done! Knowledge-base files distributed to all platform skill folders.")


if __name__ == "__main__":
    main()
