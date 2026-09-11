"""Fill intake slots from labelled paste when the LLM is slow, empty, or offline.

Heuristics extract real document text by headings/codes — they are a gap-fill
fallback after Phase 0→1 LLM analysis, not a substitute for reading the pack.
"""

from __future__ import annotations

import re

from app.domain.slots import (
    FACT_REQUIRED_SLOTS,
    INTAKE_SLOT_LABELS,
    extract_key_allowlist,
)
from app.domain.section_profile import LEGACY_SCOPE_TITLES, profile_for_project
from app.domain.tor_sections import SCOPE_SUBSECTIONS

# ASCII [0-9] only: Python \d also matches Thai digits ๐-๙.
_ASCII_DIGIT = r"[0-9]"  # NOSONAR python:S6353
_THAI_OR_ASCII_DIGIT = r"[0-9๐-๙]"
# Form headings often look like "๓.๒ วัตถุประสงค์" or "8.๑ ข้อกำหนด".
_NUM_PREFIX = rf"(?:{_THAI_OR_ASCII_DIGIT}+(?:\.{_THAI_OR_ASCII_DIGIT}+)*\.?\t*\s*)?"

_SCOPE_DEV_HEADING = "แนวทางการพัฒนาระบบ"
_SELECT_CRITERIA_HEADING = "เกณฑ์การคัดเลือก"
_SECURITY_HEADING = "ความมั่นคงปลอดภัยและ"
_OWNERSHIP_HEADING = "กรรมสิทธิ์"
_EXIT_STRATEGY_HEADING = "Exit Strategy"
_BIDDER_QUAL_HEADING = "คุณสมบัติผู้ยื่น"
_RATIONALE_HEADING = "หลักการและเหตุผล"
_PURPOSE_HEADING = "วัตถุประสงค์"
_EXPENSE_HEADING = "ค่าใช้จ่าย"
_SCOPE_METHOD_HEADING = "ขอบเขตและวิธีการดำเนินงาน"
_CURRENT_SYSTEM_DETAIL_HEADING = "รายละเอียดระบบงานปัจจุบัน"
_CURRENT_SYSTEM_HEADING = "ระบบงานที่มีในปัจจุบัน"
_SOFTWARE_LIST_HEADING = "รายการ Software"
_SOFTWARE_PROPOSED_HEADING = "รายการ Software ที่เสนอ"
_WORK_PLAN_HEADING = "แผนการดำเนินงาน"
_EXPECTED_BENEFIT_HEADING = "ประโยชน์ที่คาดว่าจะได้รับ"
_AGENCY_HEAD_LABEL = "หัวหน้าส่วนราชการ"
_SCOPE_HEADING = "ขอบเขต"
_DURATION_HEADING = "ระยะเวลา"
_DURATION_WORK_HEADING = "ระยะเวลาดำเนินงาน"
_STAFF_COST_HEADING = "ค่าใช้จ่ายบุคลากร"
_STAFF_COST_DEV_HEADING = "ค่าใช้จ่ายบุคลากรสำหรับการพัฒนาระบบ"
_DELIVERY_PLAN_HEADING = "แผนการส่งมอบงาน"
_SCOPE_OF_WORK_HEADING = "ขอบเขตของงาน"
_PROJECT_TYPE_LABEL = "ประเภทโครงการ"
_EQUIPMENT_LIST_HEADING = "รายการครุภัณฑ์คอมพิวเตอร์"
_SECURITY_TOPIC = "ความมั่นคงปลอดภัย"
_HARDWARE_TOPIC = "ฮาร์ดแวร์"

_CODE_MARK = re.compile(
    rf"\((s{_ASCII_DIGIT}+(?:\.{_ASCII_DIGIT}+)?|[a-z][a-z0-9_]{{1,32}})\)\s*[:：]",
    re.IGNORECASE,
)

_FACT_ALIASES: dict[str, tuple[str, ...]] = {
    "s1": (
        _RATIONALE_HEADING,
        "ที่มาของโครงการ",
        "ความเป็นมาและความจำเป็น",
        "ความเป็นมา",
    ),
    "s2": ("เป้าหมายของโครงการ", "ผลที่ต้องการ", _PURPOSE_HEADING),
    "s3": (
        "คุณสมบัติผู้ยื่นข้อเสนอ",
        "คุณสมบัติของผู้เสนอราคา",
        "คุณสมบัติผู้เสนอราคา",
        "คุณสมบัติของบริษัท",
    ),
    "s5": (
        "กำหนดระยะเวลาดำเนินงาน",
        _DURATION_WORK_HEADING,
        "ระยะเวลาโครงการ",
        "กำหนดเวลาดำเนินการ",
        "ระยะเวลา/แผนการดำเนินการ",
        "ระยะเวลาดำเนินการ",
    ),
    "s6": (
        "งบประมาณรวม",
        "วงเงิน",
        "งบประมาณโครงการ",
        "วงเงินงบประมาณ",
        _EXPENSE_HEADING,
    ),
    "s7": (
        "ชื่อสถานที่ตั้ง",
        "สถานที่ส่งมอบ",
        "สถานที่ตั้ง",
        "สถานที่ดำเนินการ",
    ),
    "s4.1": (
        _SCOPE_METHOD_HEADING,
        _SCOPE_DEV_HEADING,
        "ขอบเขตงานหลัก",
        _SCOPE_OF_WORK_HEADING,
        "ขอบเขตงาน",
    ),
    "s4.2": (
        _CURRENT_SYSTEM_DETAIL_HEADING,
        _CURRENT_SYSTEM_HEADING,
        "ระบบงานปัจจุบัน",
    ),
    "s4.4": (
        _EQUIPMENT_LIST_HEADING,
        "ข้อกำหนดด้านฮาร์ดแวร์",
        "คอมพิวเตอร์แท็บเล็ต",
    ),
    "s4.5": (
        _SOFTWARE_PROPOSED_HEADING,
        "ข้อกำหนดด้านซอฟต์แวร์",
        _SOFTWARE_LIST_HEADING,
    ),
    "s4.6": (
        "จุดเชื่อมโยงระบบ",
        "การเชื่อมโยงข้อมูล",
    ),
    "s4.8": (_DELIVERY_PLAN_HEADING, "ผลงานส่งมอบ", _WORK_PLAN_HEADING),
    "s4.10": (
        _STAFF_COST_DEV_HEADING,
        "บุคลากรผู้ใช้งานคอมพิวเตอร์",
        "บุคลากร ทีมงาน",
    ),
    "s4.13": (
        "สำรองและกู้คืนข้อมูล",
        "แผนสำรอง",
        "กู้คืนระบบ",
    ),
    "s8": (_DELIVERY_PLAN_HEADING, "งวดงานและการจ่ายเงิน", "งวดงาน", "การจ่ายเงิน"),
    "s9": ("การรับประกันผลงาน", "การรับประกัน"),
    "s10": ("อัตราค่าปรับ", "ค่าปรับ"),
    "s11": (_SELECT_CRITERIA_HEADING, "หลักเกณฑ์การพิจารณา", "การพิจารณาคัดเลือก"),
    "s4.14": (_SECURITY_HEADING, "PDPA", "คุ้มครองข้อมูลส่วนบุคคล"),
    "s13": (_OWNERSHIP_HEADING, _EXIT_STRATEGY_HEADING, "เงื่อนไขอื่น", _EXPECTED_BENEFIT_HEADING),
    # Semantic storage keys (Section_Profile) — same Thai headings as TOR prose.
    "functional": (
        "ขอบเขตระบบงานและหน้าที่การทำงาน",
        "หน้าที่การทำงานที่ต้องพัฒนา",
        "ขอบเขตระบบงาน",
        "งานหลักและกิจกรรม",
        _SCOPE_METHOD_HEADING,
        _SCOPE_DEV_HEADING,
    ),
    "testing": (
        "การทดสอบระบบและเกณฑ์การยอมรับ",
        "การทดสอบระบบ",
        "เกณฑ์การยอมรับ",
        "แผนการทดสอบ",
        "UAT",
    ),
    "deliverable_docs": (
        "เอกสารระบบและซอร์สโค้ด",
        "เอกสารที่ต้องส่งมอบ",
        "ผลงานส่งมอบ",
        "ซอร์สโค้ด",
        _DELIVERY_PLAN_HEADING,
        _WORK_PLAN_HEADING,
    ),
    "integration": (
        "การเชื่อมโยงระบบและการโอนย้ายข้อมูล",
        "การเชื่อมโยงระบบ",
        "จุดเชื่อมโยงระบบ",
        "การโอนย้ายข้อมูล",
    ),
    "items": (
        "รายการครุภัณฑ์",
        "รายละเอียดคุณลักษณะเฉพาะ",
        "รายการสิ่งของ",
        "คุณลักษณะเฉพาะ",
    ),
    "specification": (
        "ข้อกำหนดด้านเทคนิค",
        "ข้อกำหนดด้านฮาร์ดแวร์",
        _EQUIPMENT_LIST_HEADING,
    ),
    "licenses": (
        "ครุภัณฑ์และลิขสิทธิ์ซอฟต์แวร์ที่ต้องจัดหา",
        "ลิขสิทธิ์ซอฟต์แวร์",
        "ข้อกำหนดด้านซอฟต์แวร์",
        "เกณฑ์กลาง ICT",
        _SOFTWARE_LIST_HEADING,
        _SOFTWARE_PROPOSED_HEADING,
    ),
    "standards_security": (
        _SECURITY_HEADING,
        _SECURITY_TOPIC,
        "มาตรฐานและข้อกำหนด",
        "PDPA",
    ),
    "project_team": (
        "บุคลากรประจำโครงการ",
        "ทีมงานโครงการ",
        _STAFF_COST_DEV_HEADING,
        "บุคลากร ทีมงาน",
    ),
    "training": (
        "การฝึกอบรมและการถ่ายทอดความรู้",
        "การฝึกอบรม",
        "ถ่ายทอดความรู้",
    ),
    "system_overview": (
        "ภาพรวมและสถาปัตยกรรม",
        "สถาปัตยกรรมของระบบ",
        "ภาพรวมระบบ",
    ),
    "asset_list": (
        "รายการทรัพย์สินที่ต้องบำรุงรักษา",
        "รายการครุภัณฑ์ที่จ้างบำรุงรักษา",
        "ขอบเขตทรัพย์สิน",
    ),
    "service_spec": (
        "ขอบเขตและข้อกำหนดการให้บริการ",
        "รายละเอียดบริการที่เช่า",
        "ข้อกำหนดการให้บริการ",
    ),
    "methodology": (
        "วิธีการดำเนินงาน",
        "แนวทางการดำเนินงาน",
        "ระเบียบวิธี",
    ),
    "workload": (
        "ปริมาณงาน",
        "ขอบเขตปริมาณงาน",
        "รายละเอียดปริมาณงาน",
    ),
    "works": (
        "รายการงานก่อสร้าง",
        "รายละเอียดงานปรับปรุง",
        "ขอบเขตงานก่อสร้าง",
    ),
}

# Cap noisy heading captures for fact slots (forms often lack clean stop markers).
_FACT_BODY_CAPS: dict[str, int] = {
    "s1": 5000,
    "s2": 3500,
    "s5": 400,
    "s6": 500,
    "s7": 400,
    "s4.1": 12000,
    "functional": 12000,
    "items": 12000,
    "deliverable_docs": 8000,
    "testing": 6000,
    "specification": 8000,
    "methodology": 8000,
    "works": 8000,
    "service_spec": 8000,
    "workload": 6000,
    "asset_list": 8000,
}

_QUAL_HINT = re.compile(
    r"คุณสมบัติ|นิติบุคคล|ทุนจดทะเบียน|ผลงานพัฒนา|จัดตั้งมาแล้ว",
    re.IGNORECASE,
)
_DURATION_HINT = re.compile(
    rf"{_DURATION_HEADING}|{_ASCII_DIGIT}{{1,6}}\s{{0,8}}(?:วัน|เดือน)|นับจากวัน|กำหนดส่งมอบ",
    re.IGNORECASE,
)
_BUDGET_HINT = re.compile(
    rf"วงเงิน|งบประมาณ|ราคากลาง|{_ASCII_DIGIT}(?:{_ASCII_DIGIT}|,){{3,16}}\s{{0,8}}บาท",
    re.IGNORECASE,
)
_PLACE_HINT = re.compile(
    r"สถานที่|ที่ทำการ|ศูนย์ราชการ|กรุงเทพ|จังหวัด|อำเภอ|มหาวิทยาลัย",
    re.IGNORECASE,
)
_PURPOSE_HINT = re.compile(rf"{_PURPOSE_HEADING}|เพื่อ|เป้าหมาย", re.IGNORECASE)
_SCOPE_HINT = re.compile(rf"{_SCOPE_HEADING}|ระบบงาน|สถาปัตยกรรม|ส่งมอบงาน", re.IGNORECASE)


def extract_slot_contents(text: str) -> dict[str, str]:
    """Read `(s1):` markers first, then Thai headings, then free-form TOR prose."""
    found = _segments_by_code(text)
    _merge_missing(found, _segments_by_heading(text))
    _merge_missing(found, _segments_by_inline_labels(text))
    _merge_prefer_longer(found, extract_unstructured_slots(text))
    _apply_compact_facts(text, found)
    _trim_fact_slots(found)
    return found


def _merge_missing(found: dict[str, str], incoming: dict[str, str]) -> None:
    for key, body in incoming.items():
        if key not in found and body:
            found[key] = body


def _merge_prefer_longer(found: dict[str, str], incoming: dict[str, str]) -> None:
    for key, body in incoming.items():
        if not body:
            continue
        if key not in found or _prefer_longer(key, body, found.get(key, "")):
            found[key] = body


def _apply_compact_place(text: str, found: dict[str, str], compact: dict[str, str]) -> None:
    place = compact.get("s7")
    if not place:
        return
    if _PLACE_LINE_RE.search(text or ""):
        found["s7"] = place
        return
    if not found.get("s7") or "กรมของ" in (found.get("s7") or ""):
        found["s7"] = place


def _apply_compact_facts(text: str, found: dict[str, str]) -> None:
    # Always re-assert compact money/duration; place only when authoritative.
    compact: dict[str, str] = {}
    _extract_fact_regexes(text or "", compact)
    if compact.get("s5"):
        found["s5"] = compact["s5"]
    if compact.get("s6"):
        found["s6"] = compact["s6"]
    _apply_compact_place(text, found, compact)
    if not found.get("s4") and found.get("s4.1"):
        found["s4"] = found["s4.1"]


def facts_are_complete(slot_map: dict) -> bool:
    for key in FACT_REQUIRED_SLOTS:
        slot = slot_map.get(key) or {}
        if not isinstance(slot, dict):
            return False
        if slot.get("status") != "filled":
            return False
        if not str(slot.get("content") or "").strip():
            return False
    return True


def guess_slot_for_answer(text: str) -> str | None:
    """Route a free-form answer to the most likely slot (facts + common legal)."""
    raw = text.strip()
    if len(raw) < 4:
        return None
    if _QUAL_HINT.search(raw) and not _DURATION_HINT.search(raw):
        return "s3"
    if _BUDGET_HINT.search(raw) and not _PURPOSE_HINT.search(raw[:40]):
        return "s6"
    if _DURATION_HINT.search(raw) and not _QUAL_HINT.search(raw):
        return "s5"
    if _PLACE_HINT.search(raw) and len(raw) < 400:
        return "s7"
    if _SCOPE_HINT.search(raw) and len(raw) > 80:
        return "s4.1"
    if _PURPOSE_HINT.search(raw) and len(raw) > 20:
        return "s2"
    return None


def looks_like_qualifications(text: str) -> bool:
    return bool(_QUAL_HINT.search(text or "")) and not bool(_DURATION_HINT.search(text or ""))


def looks_like_duration(text: str) -> bool:
    return bool(_DURATION_HINT.search(text or ""))


def _looks_like_compact_fact(key: str, text: str) -> bool:
    body = (text or "").strip()
    if not body:
        return False
    if key == "s6":
        return bool(_BUDGET_RE.search(body)) and len(body) < 160
    if key == "s5":
        return bool(re.search(rf"^{_ASCII_DIGIT}{{1,6}}\s*วัน$", body)) or (
            len(body) <= 40 and "วัน" in body and "แผนการ" not in body
        )
    if key == "s7":
        return len(body) <= 120 and not _has_any(
            body, _AGENCY_HEAD_LABEL, "ผู้รับผิดชอบ", "ผู้ประสานงาน"
        )
    return False


def _prefer_longer(key: str, incoming: str, current: str) -> bool:
    """Prefer longer body except when a compact fact line beats a heading spill."""
    if key in {"s5", "s6", "s7"}:
        incoming_compact = _looks_like_compact_fact(key, incoming)
        current_compact = _looks_like_compact_fact(key, current)
        if incoming_compact and not current_compact:
            return True
        if current_compact and not incoming_compact:
            return False
    return len(incoming) > len(current)


def _trim_fact_slots(found: dict[str, str]) -> None:
    for key, cap in _FACT_BODY_CAPS.items():
        body = found.get(key)
        if body and len(body) > cap:
            found[key] = body[:cap].rstrip()
    place = found.get("s7") or ""
    if _AGENCY_HEAD_LABEL in place:
        found["s7"] = place.split(_AGENCY_HEAD_LABEL, 1)[0].strip()[:200]
    purpose = found.get("s2") or ""
    if "ต้องเขียนให้ครบ" in purpose:
        idx = purpose.find("3.2.1")
        if idx < 0:
            idx = purpose.find("เพื่อ")
        if idx > 0:
            found["s2"] = purpose[idx:].strip()


def _overlay_one_slot(current: dict, value: dict, *, slot_key: str = "") -> dict | None:
    content = str(value.get("content") or "").strip()
    status = value.get("status")
    sources = list(value.get("sources") or [])
    current_content = str(current.get("content") or "").strip()
    current_filled = current.get("status") == "filled" and bool(current_content)
    # Prefer paste/heuristic facts — LLM often mis-assigns (e.g. quals → s5).
    if current_filled and status == "filled":
        if (
            slot_key
            and slot_key not in FACT_REQUIRED_SLOTS
            and len(content) > max(len(current_content) + 80, int(len(current_content) * 1.25))
        ):
            return {"content": content, "status": "filled", "sources": sources}
        return None
    if status == "filled" and content:
        return {"content": content, "status": "filled", "sources": sources}
    if status == "reference_only" and content and current.get("status") != "filled":
        return {"content": content, "status": "reference_only", "sources": sources}
    return None


def overlay_filled_slots(base: dict, incoming: dict) -> dict:
    merged = {key: dict(value) if isinstance(value, dict) else value for key, value in base.items()}
    for key, value in incoming.items():
        if key not in merged or not isinstance(value, dict):
            continue
        current = merged.get(key) if isinstance(merged.get(key), dict) else {}
        replacement = _overlay_one_slot(current, value, slot_key=key)
        if replacement is not None:
            merged[key] = replacement
    return merged


def repair_misplaced_slots(slot_map: dict) -> dict:
    """Fix common LLM mix-ups (vendor quals dumped into duration, etc.)."""
    repaired = {key: dict(value) if isinstance(value, dict) else value for key, value in slot_map.items()}
    s5 = repaired.get("s5") if isinstance(repaired.get("s5"), dict) else {}
    s5_text = str(s5.get("content") or "").strip()
    if (
        s5.get("status") == "filled"
        and s5_text
        and looks_like_qualifications(s5_text)
        and not looks_like_duration(s5_text)
    ):
        s3 = repaired.get("s3") if isinstance(repaired.get("s3"), dict) else {}
        s3_empty = not (s3.get("status") == "filled" and str(s3.get("content") or "").strip())
        if s3_empty:
            repaired["s3"] = {
                "content": s5_text,
                "status": "filled",
                "sources": list(s5.get("sources") or []),
            }
        repaired["s5"] = {"content": "", "status": "gap", "sources": []}
    return repaired


def _segments_by_code(text: str) -> dict[str, str]:
    matches = list(_CODE_MARK.finditer(text))
    segments: dict[str, str] = {}
    allowed = extract_key_allowlist()
    for index, match in enumerate(matches):
        key = match.group(1).lower()
        if key not in allowed:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            segments[key] = body
    return segments


def _heading_catalog() -> list[tuple[str, str]]:
    headings: list[tuple[str, str]] = [
        (key, label) for key, label in INTAKE_SLOT_LABELS.items() if label
    ]
    headings.extend((key, title) for key, title in LEGACY_SCOPE_TITLES.items() if title)
    headings.extend((key, title) for key, title in SCOPE_SUBSECTIONS.items() if title)
    for cat in (
        "hire_develop",
        "hire_maintain",
        "lease_service",
        "buy_goods",
        "construction",
        "hire_consult",
        "hire_service",
    ):
        for key, title in profile_for_project(cat).slot_labels().items():
            if title:
                headings.append((key, title))
    for key, aliases in _FACT_ALIASES.items():
        headings.extend((key, alias) for alias in aliases)
    headings.sort(key=lambda item: len(item[1]), reverse=True)
    return headings


def _spans_overlap(start: int, end: int, used: list[tuple[int, int]]) -> bool:
    return any(start < other_end and end > other_start for other_start, other_end in used)


def _segments_by_inline_labels(text: str) -> dict[str, str]:
    """Split a single paragraph that uses 'หัวข้อ:' labels without newlines."""
    used: list[tuple[int, int]] = []
    hits: list[tuple[int, int, str]] = []
    for key, heading in _heading_catalog():
        pattern = re.compile(re.escape(heading) + r"\s*[:：]")
        for match in pattern.finditer(text):
            start, end = match.start(), match.end()
            if _spans_overlap(start, end, used):
                continue
            used.append((start, end))
            hits.append((start, end, key))
    hits.sort(key=lambda item: item[0])
    found: dict[str, str] = {}
    for index, (_start, end, key) in enumerate(hits):
        if key in found:
            continue
        stop = hits[index + 1][0] if index + 1 < len(hits) else len(text)
        body = text[end:stop].strip()
        if body:
            found[key] = body
    return found


_NEXT_SECTION = re.compile(
    rf"\n\s*{_NUM_PREFIX}"
    rf"(?:{_RATIONALE_HEADING}|{_PURPOSE_HEADING}|เป้าหมาย|ตัวชี้วัด|{_SCOPE_HEADING}|"
    rf"{_CURRENT_SYSTEM_HEADING}|รายละเอียดของระบบงานใหม่|{_CURRENT_SYSTEM_DETAIL_HEADING}|"
    rf"{_DURATION_HEADING}|{_WORK_PLAN_HEADING}|{_EXPENSE_HEADING}|งบประมาณรวม|{_EXPECTED_BENEFIT_HEADING}|"
    rf"คุณสมบัติ|{_SELECT_CRITERIA_HEADING}|{_SECURITY_TOPIC}|{_OWNERSHIP_HEADING}|{_EXIT_STRATEGY_HEADING}|"
    rf"{_SCOPE_DEV_HEADING}|แผนการส่งมอบ|สอดคล้องกับแผน|"
    rf"รายการครุภัณฑ์|{_SOFTWARE_LIST_HEADING}|{_STAFF_COST_HEADING}|"
    r"ข้อกำหนดทั่วไป|การบันทึกและนำเข้า|การประมวลผล|การให้บริการ|"
    r"การบริหารจัดการ|การฝึกอบรม)"
)


def _segments_by_heading(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, heading in _heading_catalog():
        if key in found:
            continue
        pattern = re.compile(
            rf"(?:^|\n)\s*{_NUM_PREFIX}{re.escape(heading)}\s*[:：]?\s*",
            re.IGNORECASE,
        )
        match = pattern.search(text)
        if not match:
            continue
        start = match.end()
        stop_match = _NEXT_SECTION.search(text, start)
        end = stop_match.start() if stop_match else len(text)
        # Also stop at classic "Label:" lines for TOR packs.
        colon_stop = re.search(
            r"\n\s*\S.{0,40}[:：]",
            text[start:end],
        )
        if colon_stop:
            end = start + colon_stop.start()
        body = text[start:end].strip()
        if body:
            found[key] = body
    return found


_BUDGET_RE = re.compile(
    rf"(?:วงเงินงบประมาณ|งบประมาณรวม|วงเงิน)\s*"
    rf"(?:[.\s…._]{{0,40}})?"
    rf"({_ASCII_DIGIT}(?:{_ASCII_DIGIT}|,){{2,20}})\s*"
    rf"(?:[.\s…._]{{0,20}})?"
    rf"บาท"
)
_MIDPRICE_RE = re.compile(
    rf"ราคากลาง\s*[:：]?\s*({_ASCII_DIGIT}(?:{_ASCII_DIGIT}|,){{0,20}})\s*บาท"
)
_DAYS_RE = re.compile(
    rf"จำนวน\s*({_ASCII_DIGIT}{{1,6}})\s*วัน|"
    rf"(?:กำหนด)?{_DURATION_HEADING}(?:ดำเนินงาน|ดำเนินการ)?\s*[:：]?\s*"
    rf"(?:จำนวน\s*)?({_ASCII_DIGIT}{{1,6}})\s*วัน"
)
_AGENCY_RE = re.compile(
    r"(สำนักงานเศรษฐกิจการเกษตร|"
    r"สำนักงาน\s*กกต\.?|"
    r"สำนักงานคณะกรรมการเลือกตั้ง|"
    r"กรมบัญชีกลาง|"
    r"สำนักงาน[ก-๙A-Za-z]{2,40}|"
    r"กรม(?!ของ)[ก-๙]{2,40})"
)
_PROJECT_NAME_RE = re.compile(r"ชื่อโครงการ[.\s…]*([^\n]+)")
_PLACE_LINE_RE = re.compile(r"(?:ชื่อสถานที่ตั้ง|สถานที่ตั้ง)\s*([^\n]+)")
_PENALTY_RE = re.compile(r"ค่าปรับ[^\n]{0,80}")
_ACCEPTANCE_CRITERIA = "เกณฑ์ตรวจรับ"
_BLOCK_MARKERS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "s1",
        (_RATIONALE_HEADING, "ที่มาของโครงการ", "ความเป็นมาและความจำเป็น"),
        (_PURPOSE_HEADING, "เป้าหมาย", "ตัวชี้วัด", _SCOPE_HEADING),
    ),
    (
        "s2",
        (_PURPOSE_HEADING,),
        ("เป้าหมาย", "ตัวชี้วัด", "สอดคล้องกับแผน", _SCOPE_HEADING),
    ),
    (
        "s4.1",
        (_SCOPE_METHOD_HEADING, _SCOPE_DEV_HEADING, _SCOPE_OF_WORK_HEADING),
        (
            "การฝึกอบรม",
            "ระยะเวลา/แผน",
            _DURATION_WORK_HEADING,
            _EXPENSE_HEADING,
            "งบประมาณรวม",
            _BIDDER_QUAL_HEADING,
            _EXPECTED_BENEFIT_HEADING,
        ),
    ),
    (
        "s4.2",
        (_CURRENT_SYSTEM_HEADING, _CURRENT_SYSTEM_DETAIL_HEADING),
        ("รายละเอียดของระบบงานใหม่", _RATIONALE_HEADING, _SCOPE_HEADING),
    ),
    (
        "s4.4",
        (_EQUIPMENT_LIST_HEADING, "คอมพิวเตอร์แท็บเล็ต แบบที่"),
        (_SOFTWARE_LIST_HEADING, _STAFF_COST_HEADING, _SCOPE_HEADING, "ซอฟต์แวร์"),
    ),
    (
        "s4.5",
        (_SOFTWARE_PROPOSED_HEADING, _SOFTWARE_LIST_HEADING),
        (_STAFF_COST_HEADING, _SCOPE_HEADING, _HARDWARE_TOPIC),
    ),
    (
        "s8",
        ("แผนการส่งมอบ", "งวดงานและการจ่ายเงิน", _WORK_PLAN_HEADING),
        ("กฎระเบียบ มาตรฐาน", _BIDDER_QUAL_HEADING, _SELECT_CRITERIA_HEADING, _EXPENSE_HEADING),
    ),
    (
        "s3",
        (_BIDDER_QUAL_HEADING, "คุณสมบัติของผู้เสนอราคา"),
        (_SELECT_CRITERIA_HEADING, _ACCEPTANCE_CRITERIA, _SECURITY_TOPIC),
    ),
    (
        "s11",
        (_SELECT_CRITERIA_HEADING, "หลักเกณฑ์การพิจารณา", _ACCEPTANCE_CRITERIA),
        (_SECURITY_TOPIC, _OWNERSHIP_HEADING),
    ),
    (
        "s4.14",
        (_SECURITY_HEADING, "PDPA", "คุ้มครองข้อมูลส่วนบุคคล"),
        (_OWNERSHIP_HEADING, _EXIT_STRATEGY_HEADING),
    ),
    (
        "s13",
        (_OWNERSHIP_HEADING, _EXIT_STRATEGY_HEADING, _EXPECTED_BENEFIT_HEADING),
        (),
    ),
)


def _find_marker_line(text: str, markers: tuple[str, ...], *, after: int = 0) -> tuple[int, str]:
    best = -1
    used = ""
    for marker in markers:
        line_at = text.find("\n" + marker, after)
        if line_at >= 0:
            idx = line_at + 1
            if best < 0 or idx < best:
                best = idx
                used = marker
            continue
        if after == 0 and text.startswith(marker):
            return 0, marker
    return best, used


def _find_marker_substring(text: str, markers: tuple[str, ...], *, after: int = 0) -> tuple[int, str]:
    best = -1
    used = ""
    for marker in markers:
        idx = text.find(marker, after)
        if idx >= 0 and (best < 0 or idx < best):
            best = idx
            used = marker
    return best, used


def _find_marker(text: str, markers: tuple[str, ...], *, after: int = 0) -> tuple[int, str]:
    best, used = _find_marker_line(text, markers, after=after)
    if best >= 0:
        return best, used
    return _find_marker_substring(text, markers, after=after)


def _slice_between(
    text: str, starts: tuple[str, ...], ends: tuple[str, ...]
) -> str:
    begin, used = _find_marker(text, starts)
    if begin < 0:
        return ""
    rest = text[begin:]
    cut = len(rest)
    skip = max(len(used), 1)
    for marker in ends:
        idx, _found = _find_marker(rest, (marker,), after=skip)
        if 0 <= idx < cut:
            cut = idx
    return rest[:cut].strip()


def _fill_if_empty(found: dict[str, str], key: str, body: str) -> None:
    text = (body or "").strip()
    if key in found or not text:
        return
    found[key] = text


def _has_any(text: str, *needles: str) -> bool:
    return any(needle in text for needle in needles)


def _extract_budget(raw: str, found: dict[str, str]) -> None:
    budget = _BUDGET_RE.search(raw)
    if not budget:
        return
    line = f"วงเงินงบประมาณ {budget.group(1)} บาท"
    mid = _MIDPRICE_RE.search(raw)
    if mid:
        line += f" ราคากลาง {mid.group(1)} บาท"
    found["s6"] = line


def _pick_duration_match(raw: str):
    # Prefer duration near the form's timeline heading, not random "N วัน".
    days = None
    for match in _DAYS_RE.finditer(raw):
        start = max(0, match.start() - 40)
        window = raw[start : match.end()]
        if _DURATION_HEADING not in window and "แผนการดำเนินการ" not in window and "จำนวน" not in match.group(0):
            continue
        if "อบรม" in window or "ภายใน" in window:
            continue
        days = match
        if _DURATION_HEADING in window:
            break
    return days


def _extract_duration(raw: str, found: dict[str, str]) -> None:
    days = _pick_duration_match(raw)
    if not days:
        return
    day_val = days.group(1) or days.group(2)
    if day_val:
        found["s5"] = f"{day_val} วัน"


def _extract_place(raw: str, found: dict[str, str]) -> None:
    place = _PLACE_LINE_RE.search(raw)
    if place:
        found["s7"] = place.group(1).strip()[:200]
        return
    agency = _AGENCY_RE.search(raw)
    if agency and "s7" not in found:
        found["s7"] = agency.group(1).strip()


def _extract_penalty(raw: str, found: dict[str, str]) -> None:
    penalty = _PENALTY_RE.search(raw)
    late = re.search(r"ค่าปรับส่งมอบ[^\n]{0,60}", raw)
    if late:
        found["s10"] = late.group(0).strip()
    elif penalty:
        found["s10"] = penalty.group(0).strip()


def _project_name_body(match: re.Match[str]) -> str:
    name = match.group(1).strip()
    if _PROJECT_TYPE_LABEL in name:
        name = name.split(_PROJECT_TYPE_LABEL, 1)[0].strip()
    return name[:500]


def _extract_lead_s1(raw: str, found: dict[str, str]) -> None:
    project = _PROJECT_NAME_RE.search(raw)
    if project and _RATIONALE_HEADING not in raw[:1200]:
        _fill_if_empty(found, "s1", _project_name_body(project))
    if "s1" in found:
        return
    lead_end = raw.find(_SCOPE_DEV_HEADING)
    if lead_end < 0:
        lead_end = raw.find(_SCOPE_METHOD_HEADING)
    if lead_end < 0:
        lead_end = raw.find(_RATIONALE_HEADING)
    lead = raw[: lead_end if lead_end > 80 else min(1500, len(raw))].strip()
    # Skip Thai budget-form cover sheets; keep TOR prose leads like ECT packs.
    if (
        "โครงการ" in lead
        and len(lead) > 80
        and "แบบฟอร์มเสนอขอตั้งงบประมาณ" not in lead[:160]
    ):
        found["s1"] = lead[:1500]
        _fill_if_empty(found, "s2", lead[:800])


def _extract_fact_regexes(raw: str, found: dict[str, str]) -> None:
    _extract_budget(raw, found)
    _extract_duration(raw, found)
    _extract_place(raw, found)
    _extract_penalty(raw, found)
    _extract_lead_s1(raw, found)


def _extract_linkage_slot(raw: str, found: dict[str, str]) -> None:
    # Integration / linkage — only from real document text (no sample fallbacks).
    widget = _slice_between(
        raw,
        ("Web Chat Widget", "จุดเชื่อมโยง", "เชื่อมต่อ Web Chat"),
        (_ACCEPTANCE_CRITERIA, _OWNERSHIP_HEADING, _BIDDER_QUAL_HEADING, _EXPENSE_HEADING),
    )
    if widget and _has_any(widget, "Widget", "Live Chat", "จุดเชื่อมโยง", "Web Chat"):
        _fill_if_empty(found, "s4.6", widget)
        return
    if not _has_any(raw, "เชื่อมโยงกับฐานข้อมูล", "เชื่อมโยงข้อมูล", "Open data, API"):
        return
    link_bits = []
    for needle in (
        "เชื่อมโยงกับฐานข้อมูลการเกษตร",
        "เชื่อมโยง และทำงานภายใต้ฐานข้อมูล",
        "Open data, API และ Web service",
        "Web service",
    ):
        idx = raw.find(needle)
        if idx >= 0:
            link_bits.append(raw[idx : idx + 220].strip())
    if link_bits:
        _fill_if_empty(found, "s4.6", " ".join(link_bits)[:1200])


def _extract_block_markers(raw: str, found: dict[str, str]) -> None:
    for key, starts, ends in _BLOCK_MARKERS:
        body = _slice_between(raw, starts, ends)
        if not body:
            continue
        if key in found and len(found[key]) >= len(body):
            continue
        if key in {"s5", "s6", "s7"} and key in found:
            continue
        found[key] = body
    _extract_linkage_slot(raw, found)


def _enrich_scope_hardware_software(scope: str, found: dict[str, str]) -> None:
    if _has_any(scope, "Kubernetes", "คลาวด์", "Containerized"):
        _fill_if_empty(found, "s4.4", scope)
    if _has_any(scope, "แท็บเล็ต", _HARDWARE_TOPIC, "เครื่องแม่ข่าย"):
        _fill_if_empty(found, "s4.4", scope)
    if _has_any(scope, "RAG", "OCR", "Chatbot", "ซอฟต์แวร์", "ลิขสิทธิ์", "Web Application"):
        _fill_if_empty(found, "s4.5", scope)
    if scope and "ระบบ" in scope:
        _fill_if_empty(found, "s4.3", scope)


def _enrich_staff_slot(raw: str, found: dict[str, str], quals: str) -> None:
    if not (_has_any(quals, "บุคลากร", "ทีมงาน") or "ผู้จัดการโครงการ" in raw):
        return
    staff = _slice_between(
        raw,
        (_STAFF_COST_DEV_HEADING, "ตำแหน่งบุคลากร", "ผู้จัดการโครงการ"),
        ("ค่าใช้จ่ายที่เกิดขึ้นทุกเดือน", "ค่าใช้จ่ายอื่นๆ", _SCOPE_HEADING, _DURATION_HEADING),
    )
    _fill_if_empty(found, "s4.10", staff or quals)


def _enrich_warranty_slots(raw: str, found: dict[str, str], warranty: str) -> None:
    if not (_has_any(warranty, "SLA", "บำรุงรักษา") or "รับประกัน" in raw):
        return
    _fill_if_empty(found, "s9", warranty)
    _fill_if_empty(found, "s4.9", warranty)
    _fill_if_empty(found, "s4.11", warranty)


def _enrich_staff_and_delivery(raw: str, found: dict[str, str]) -> None:
    quals = found.get("s3") or ""
    payments = found.get("s8") or ""
    sla = found.get("s13") or ""
    _enrich_staff_slot(raw, found, quals)
    if "ส่งมอบ" in payments or _WORK_PLAN_HEADING in raw:
        _fill_if_empty(found, "s4.8", payments or found.get("s4.8", ""))
    _enrich_warranty_slots(raw, found, sla or payments)
    if "ISO" in quals or ("มาตรฐาน" in raw and _SELECT_CRITERIA_HEADING in raw):
        _fill_if_empty(found, "s4.7", quals or found.get("s11") or sla)
    if quals:
        _fill_if_empty(found, "s12", quals)
    if payments:
        _fill_if_empty(found, "s4.12", payments)


def _enrich_backup_and_current(raw: str, found: dict[str, str]) -> None:
    sla = found.get("s13") or ""
    payments = found.get("s8") or ""
    if _has_any(raw, _EXIT_STRATEGY_HEADING, "Secure Wipe", "กู้คืน", "สำรองและกู้คืน"):
        backup = _slice_between(
            raw,
            ("สำรองและกู้คืนข้อมูล", _EXIT_STRATEGY_HEADING, "กู้คืน"),
            (_OWNERSHIP_HEADING, "ค่าปรับ", "ประโยชน์"),
        )
        _fill_if_empty(found, "s4.13", backup or sla or payments)
    # Current-systems table often lists many existing apps.
    if _CURRENT_SYSTEM_HEADING in raw or "ระบบประมวลผลภาวะเศรษฐกิจและสังคมครัวเรือน" in raw:
        current = found.get("s4.2") or ""
        if len(current) < 80:
            snippet = _slice_between(
                raw,
                (_CURRENT_SYSTEM_HEADING, _CURRENT_SYSTEM_DETAIL_HEADING, "- ระบบสารสนเทศ"),
                ("รายละเอียดของระบบงานใหม่", _RATIONALE_HEADING, "ขอบเขตและวิธีการ"),
            )
            _fill_if_empty(found, "s4.2", snippet)


def _enrich_scope_subs(raw: str, found: dict[str, str]) -> None:
    _enrich_scope_hardware_software(found.get("s4.1") or "", found)
    _enrich_staff_and_delivery(raw, found)
    _enrich_backup_and_current(raw, found)


def extract_unstructured_slots(text: str) -> dict[str, str]:
    """Map free-form TOR / ขอบเขตงาน prose that has no (s1): codes."""
    raw = text or ""
    found: dict[str, str] = {}
    _extract_fact_regexes(raw, found)
    _extract_block_markers(raw, found)
    _enrich_scope_subs(raw, found)
    return {key: value for key, value in found.items() if value}


_DEV_PACK_MARKERS = (
    "พัฒนาระบบ",
    "จ้างพัฒนา",
    "ระบบสารสนเทศ",
    "เว็บไซต์",
    "เว็บแอป",
    "web application",
    "software development",
)
_HW_PACK_MARKERS = (
    "เครื่องแม่ข่าย",
    "เครื่องคอมพิวเตอร์",
    "แท็บเล็ต",
    _HARDWARE_TOPIC,
    "ครุภัณฑ์คอมพิวเตอร์",
    "server",
    "hardware",
    "tablet",
)
_GOODS_ONLY_TYPES = frozenset({"buy_goods", "general", ""})


def pack_mixes_develop_and_hardware(text: str) -> bool:
    raw = text or ""
    lowered = raw.lower()
    has_dev = any(marker in raw or marker in lowered for marker in _DEV_PACK_MARKERS)
    has_hw = any(marker in raw or marker in lowered for marker in _HW_PACK_MARKERS)
    return has_dev and has_hw


def suggest_procurement_category(text: str, current: str | None = None) -> str | None:
    """Prefer hire_develop when a pack mixes system development with servers/hardware."""
    if not pack_mixes_develop_and_hardware(text):
        return None
    mapped = (current or "").strip()
    if mapped in _GOODS_ONLY_TYPES:
        return "hire_develop"
    return None
