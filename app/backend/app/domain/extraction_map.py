"""Map extracted TOR text onto canonical s1–s13 keys (Phase 0 auto-map)."""

from __future__ import annotations

import re

from app.domain.tor_sections import TOR_SECTION_LABELS, TOR_SECTION_ORDER

_HEADING_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"ความเป็นมา"), "s1"),
    (re.compile(r"วัตถุประสงค์"), "s2"),
    (re.compile(r"คุณสมบัติ"), "s3"),
    (re.compile(r"ขอบเขต"), "s4"),
    (re.compile(r"ระยะเวลา"), "s5"),
    (re.compile(r"วงเงิน|งบประมาณ"), "s6"),
    (re.compile(r"สถานที่"), "s7"),
    (re.compile(r"งวดงาน|จ่ายเงิน"), "s8"),
    (re.compile(r"รับประกัน"), "s9"),
    (re.compile(r"ค่าปรับ"), "s10"),
    (re.compile(r"เกณฑ์พิจารณา|หลักเกณฑ์การพิจารณา"), "s11"),
    (re.compile(r"เอกสารและหลักฐาน|เอกสารที่ผู้เสนอราคา"), "s12"),
    (re.compile(r"เงื่อนไขอื่น"), "s13"),
]


def _map_by_headings(text: str) -> dict[str, str]:
    lines = text.replace("\r\n", "\n").split("\n")
    buckets: dict[str, list[str]] = {key: [] for key in TOR_SECTION_ORDER}
    current = "s1"
    saw_heading = False

    for raw in lines:
        stripped = raw.strip()
        matched_key: str | None = None
        numbered = re.match(
            r"^(?:ส่วนที่[ \t]{0,8})?([0-9]{1,2})[.)、][ \t]+([^\n]{1,200})$",  # NOSONAR python:S6353
            stripped,
        )
        candidate = numbered.group(2) if numbered else stripped
        for pattern, key in _HEADING_PATTERNS:
            heading_like = bool(numbered) or len(candidate) < 40
            if heading_like and pattern.search(candidate) and len(candidate) < 80:
                matched_key = key
                break
        if matched_key:
            current = matched_key
            saw_heading = True
            continue
        buckets[current].append(raw)

    mapped = {
        key: "\n".join(chunk).strip()
        for key, chunk in buckets.items()
        if "\n".join(chunk).strip()
    }
    if not saw_heading and mapped.get("s1") and len(mapped) == 1:
        return {"s1": text.strip()}
    return mapped


def _slots_for_review(text: str) -> dict[str, str]:
    from app.services.intake_heuristic import extract_slot_contents

    heur = extract_slot_contents(text)
    parent = {key: heur[key] for key in TOR_SECTION_ORDER if heur.get(key)}
    if heur.get("s4.1") and "s4" not in parent:
        parent["s4"] = heur["s4.1"]
    return parent


def map_extracted_text(text: str) -> dict[str, str]:
    """Split extracted TOR text into canonical section keys using headings."""
    if not text or not text.strip():
        return {}
    mapped = _map_by_headings(text)
    parent = _slots_for_review(text)
    collapsed = not mapped or (set(mapped) == {"s1"})
    if collapsed and len(parent) > 1:
        return _flatten_mapped_sections(parent)
    if not mapped:
        return _flatten_mapped_sections(parent or {"s1": text.strip()})
    merged = dict(mapped)
    for key, body in parent.items():
        current = merged.get(key) or ""
        if not current or len(body) > len(current):
            merged[key] = body
    return _flatten_mapped_sections(merged)


_MINISTRY_KEYWORDS = (
    "กรมสรรพากร",
    "กรมบัญชีกลาง",
    "กรมป้องกันและบรรเทาสาธารณภัย",
    "กรุงเทพมหานคร",
    "กระทรวงดิจิทัล",
    "กระทรวงการคลัง",
    "สำนักนายกรัฐมนตรี",
)

# ASCII [0-9] only: Python \d also matches Thai digits ๐-๙.
_MONEY_RE = re.compile(
    r"([0-9]{1,3}(?:,[0-9]{3})+|[0-9]{5,12})\s*(?:บาท)?"  # NOSONAR python:S6353
)
_PERCENT_RE = re.compile(r"([0-9]{1,3})\s*%")  # NOSONAR python:S6353
_PROJECT_NAME_RE = re.compile(
    r"(?:โครงการ|จ้าง|จัดซื้อจัดจ้าง|จัดหา)[^\n]{8,120}"
)


def infer_wizard_fields(mapped: dict[str, str]) -> dict[str, str | int]:
    """Derive Step 1 fields from mapped sections."""
    fields: dict[str, str | int] = {}
    location = mapped.get("s7", "").strip()
    if location:
        fields["location"] = location.split("\n", 1)[0][:255]
    duration = re.search(r"([0-9]{1,4})\s*วัน", mapped.get("s5", ""))  # NOSONAR python:S6353
    if duration:
        fields["duration_days"] = int(duration.group(1))
    budget = infer_review_budget("", mapped)
    if budget is not None:
        fields["budget"] = budget
    return fields


def infer_review_budget(text: str, mapped: dict[str, str] | None = None) -> int | None:
    """First positive baht amount from prose or mapped s6/s1 (standalone review)."""
    blobs = [text or ""]
    if mapped:
        blobs.append(mapped.get("s6") or "")
        blobs.append(mapped.get("s1") or "")
    for blob in blobs:
        value = extract_nlp_fields(blob).get("budget")
        if isinstance(value, int) and value > 0:
            return value
    return None


def _flatten_mapped_sections(mapped: dict[str, str]) -> dict[str, str]:
    from app.domain.section_text import section_plain_text

    flattened: dict[str, str] = {}
    for key, body in mapped.items():
        plain = section_plain_text(body, key)
        flattened[key] = plain or body
    return flattened


def extract_nlp_fields(text: str) -> dict[str, object]:
    """Rule-based field extraction used by Phase 0 mapping-box (doc 08)."""
    blob = text or ""
    fields: dict[str, object] = {}
    name_match = _PROJECT_NAME_RE.search(blob)
    if name_match:
        fields["projectName"] = name_match.group(0).strip()[:500]
    for ministry in _MINISTRY_KEYWORDS:
        if ministry in blob:
            fields["ministry"] = ministry
            break
    amounts = [int(m.group(1).replace(",", "")) for m in _MONEY_RE.finditer(blob)]
    if amounts:
        budget = max(amounts)
        fields["budget"] = budget
        fields["paidupSuggest"] = f"ไม่น้อยกว่า {int(budget * 0.25):,} บาท (25% ของงบประมาณที่สกัดได้)"
    timeline = re.search(r"ระยะเวลา[^\n]{0,80}", blob)
    if timeline:
        fields["timeline"] = timeline.group(0).strip()
    problem = re.search(r"ปัญหา[^\n]{8,160}", blob)
    if problem:
        fields["problem"] = problem.group(0).strip()
    percents = [int(m.group(1)) for m in _PERCENT_RE.finditer(blob) if int(m.group(1)) <= 100]
    if percents:
        fields["paymentPercents"] = percents[:8]
        fields["paymentPercentsText"] = "พบสัดส่วนงวดจ่ายเงินในเอกสาร: " + ", ".join(
            f"{p}%" for p in percents[:8]
        )
    if "เกณฑ์ราคาประกอบ" in blob or "ราคาประกอบเกณฑ์คุณภาพ" in blob:
        fields["evaluationMethod"] = "เกณฑ์ราคาประกอบเกณฑ์คุณภาพ"
    elif "เกณฑ์คุณภาพ" in blob:
        fields["evaluationMethod"] = "เกณฑ์คุณภาพเท่านั้น"
    elif "เกณฑ์ราคา" in blob:
        fields["evaluationMethod"] = "เกณฑ์ราคา (Price)"
    return fields


def mapping_rows(extracted: dict[str, object]) -> list[dict[str, str]]:
    """Build mapping-box rows with matched/partial tags."""
    catalog = (
        ("projectName", "ชื่อโครงการ (หมวด 1)"),
        ("ministry", "หน่วยงาน"),
        ("budget", "วงเงินงบประมาณ (หมวด 6)"),
        ("problem", "ปัญหา/ความเป็นมา (หมวด 1)"),
        ("timeline", "ระยะเวลา (หมวด 5)"),
        ("evaluationMethod", "เกณฑ์การพิจารณา (หมวด 11)"),
        ("paidupSuggest", "ทุนจดทะเบียนแนะนำ (หมวด 3)"),
        ("paymentPercentsText", "งวดจ่ายเงิน (หมวด 8)"),
    )
    rows: list[dict[str, str]] = []
    for key, label in catalog:
        value = extracted.get(key)
        if value is None or value == "":
            rows.append({"field": key, "label": label, "value": "", "tag": "partial"})
            continue
        display = f"{value:,} บาท" if key == "budget" and isinstance(value, int) else str(value)
        rows.append({"field": key, "label": label, "value": display, "tag": "matched"})
    if not any(row["tag"] == "matched" for row in rows):
        return [
            {
                "field": "none",
                "label": "ไม่พบข้อมูลที่จับคู่ได้จากไฟล์นี้",
                "value": "",
                "tag": "partial",
            }
        ]
    return rows


def section_preview(mapped: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "key": key,
            "title": TOR_SECTION_LABELS[key],
            "content": mapped.get(key, ""),
        }
        for key in TOR_SECTION_ORDER
        if mapped.get(key)
    ]
