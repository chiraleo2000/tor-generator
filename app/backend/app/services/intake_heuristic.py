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
    "s1": ("หลักการและเหตุผล", "ที่มาของโครงการ", "ความเป็นมาและความจำเป็น"),
    "s2": ("เป้าหมายของโครงการ", "ผลที่ต้องการ"),
    "s5": ("ระยะเวลาโครงการ", "กำหนดเวลาดำเนินการ"),
    "s6": ("วงเงิน", "งบประมาณโครงการ"),
    "s7": ("สถานที่ส่งมอบ", "สถานที่ตั้ง"),
    "s4.1": ("ขอบเขตงานหลัก", "ขอบเขตงาน"),
}


def extract_slot_contents(text: str) -> dict[str, str]:
    """Read `(s1):` markers first, then Thai headings for empty keys."""
    found = _segments_by_code(text)
    if len(found) >= 2:
        return found
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


def _overlay_one_slot(current: dict, value: dict) -> dict | None:
    content = str(value.get("content") or "").strip()
    status = value.get("status")
    sources = list(value.get("sources") or [])
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
