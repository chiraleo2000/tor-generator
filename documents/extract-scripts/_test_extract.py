# -*- coding: utf-8 -*-
import sys
from pathlib import Path

sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_tor_content import extract_tor_content_from_file

_RAW = Path(__file__).resolve().parents[1] / "research" / "raw_text"
result = extract_tor_content_from_file(
    str(_RAW / "ระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560.txt")
)

print(f"Total sections: {result['total_sections']}")
print(f"TOR relevant: {result['tor_relevant_sections']}\n")

for area_key in [
    "tor_preparation",
    "evaluation_criteria",
    "qualifications",
    "timeline_process",
    "contract_penalty",
    "guarantee",
]:
    sections = [s for s in result["focus_areas"][area_key] if "note" not in s]
    print(f"=== {area_key} ({len(sections)} sections) ===")
    for s in sections[:3]:
        print(f"  {s['section_id']}: {s['content'][:120]}...")
    if len(sections) > 3:
        print(f"  ... +{len(sections) - 3} more")
    print()
