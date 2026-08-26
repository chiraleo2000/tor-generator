"""Fill intake slots from labelled paste when the LLM is slow or empty."""

from __future__ import annotations

import re

from app.domain.slots import FACT_REQUIRED_SLOTS, INTAKE_SLOT_LABELS, INTAKE_SLOT_ORDER

# ASCII [0-9] only: Python \d also matches Thai digits ๐-๙.
_CODE_MARK = re.compile(
    r"\((s[0-9]+(?:\.[0-9]+)?)\)\s*[:：]",  # NOSONAR python:S6353
    re.IGNORECASE,
)

_FACT_ALIASES: dict[str, tuple[str, ...]] = {
    "s1": ("หลักการและเหตุผล", "ที่มาของโครงการ", "ความเป็นมาและความจำเป็น", "ชื่อโครงการ"),
    "s2": ("เป้าหมายของโครงการ", "ผลที่ต้องการ", "วัตถุประสงค์"),
    "s3": ("คุณสมบัติของผู้เสนอราคา", "คุณสมบัติผู้เสนอราคา", "คุณสมบัติของบริษัท"),
    "s5": ("ระยะเวลาโครงการ", "กำหนดเวลาดำเนินการ", "ระยะเวลาดำเนินการ"),
    "s6": ("วงเงิน", "งบประมาณโครงการ", "วงเงินงบประมาณ"),
    "s7": ("สถานที่ส่งมอบ", "สถานที่ตั้ง", "สถานที่ดำเนินการ"),
    "s4.1": ("ขอบเขตงานหลัก", "ขอบเขตของงาน", "ขอบเขตงาน"),
    "s8": ("งวดงานและการจ่ายเงิน", "งวดงาน", "การจ่ายเงิน"),
    "s9": ("การรับประกันผลงาน", "การรับประกัน"),
    "s10": ("อัตราค่าปรับ", "ค่าปรับ"),
    "s11": ("หลักเกณฑ์การพิจารณา", "การพิจารณาคัดเลือก"),
}

_QUAL_HINT = re.compile(
    r"คุณสมบัติ|นิติบุคคล|ทุนจดทะเบียน|ผลงานพัฒนา|จัดตั้งมาแล้ว",
    re.IGNORECASE,
)
_DURATION_HINT = re.compile(
    r"ระยะเวลา|[0-9]+\s*วัน|[0-9]+\s*เดือน|นับจากวัน|กำหนดส่งมอบ",
    re.IGNORECASE,
)
_BUDGET_HINT = re.compile(
    r"วงเงิน|งบประมาณ|ราคากลาง|[0-9][0-9,]{3,}\s*บาท",
    re.IGNORECASE,
)
_PLACE_HINT = re.compile(
    r"สถานที่|ที่ทำการ|ศูนย์ราชการ|กรุงเทพ|จังหวัด|อำเภอ",
    re.IGNORECASE,
)
_PURPOSE_HINT = re.compile(r"วัตถุประสงค์|เพื่อ|เป้าหมาย", re.IGNORECASE)
_SCOPE_HINT = re.compile(r"ขอบเขต|ระบบงาน|สถาปัตยกรรม|ส่งมอบงาน", re.IGNORECASE)


def extract_slot_contents(text: str) -> dict[str, str]:
    """Read `(s1):` markers first, then Thai headings for empty keys."""
    found = _segments_by_code(text)
    for key, body in _segments_by_heading(text).items():
        if key not in found and body:
            found[key] = body
    return found


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


def _overlay_one_slot(current: dict, value: dict) -> dict | None:
    content = str(value.get("content") or "").strip()
    status = value.get("status")
    sources = list(value.get("sources") or [])
    current_content = str(current.get("content") or "").strip()
    current_filled = current.get("status") == "filled" and bool(current_content)
    # Prefer paste/heuristic facts — LLM often mis-assigns (e.g. quals → s5).
    if current_filled and status == "filled":
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
        replacement = _overlay_one_slot(current, value)
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
    allowed = set(INTAKE_SLOT_ORDER)
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


def _segments_by_heading(text: str) -> dict[str, str]:
    headings: list[tuple[str, str]] = [
        (key, label) for key, label in INTAKE_SLOT_LABELS.items() if label
    ]
    for key, aliases in _FACT_ALIASES.items():
        headings.extend((key, alias) for alias in aliases)
    headings.sort(key=lambda item: len(item[1]), reverse=True)
    found: dict[str, str] = {}
    for key, heading in headings:
        if key in found:
            continue
        pattern = re.compile(
            rf"(?:^|\n)\s*{re.escape(heading)}\s*[:：]\s*(.+?)(?=\n\s*\S.{{0,40}}[:：]|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(text)
        if not match:
            continue
        body = match.group(1).strip()
        if body:
            found[key] = body
    return found
