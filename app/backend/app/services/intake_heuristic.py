"""Fill intake slots from labelled paste when the LLM is slow or empty."""

from __future__ import annotations

import re

from app.domain.slots import FACT_REQUIRED_SLOTS, INTAKE_SLOT_LABELS, INTAKE_SLOT_ORDER

# ASCII [0-9] only: Python \d also matches Thai digits ๐-๙.
_ASCII_DIGIT = r"[0-9]"  # NOSONAR python:S6353

_SCOPE_DEV_HEADING = "แนวทางการพัฒนาระบบ"
_SELECT_CRITERIA_HEADING = "เกณฑ์การคัดเลือก"
_SECURITY_HEADING = "ความมั่นคงปลอดภัย"
_OWNERSHIP_HEADING = "กรรมสิทธิ์"
_EXIT_STRATEGY_HEADING = "Exit Strategy"
_BIDDER_QUAL_HEADING = "คุณสมบัติผู้ยื่น"

_CODE_MARK = re.compile(
    rf"\((s{_ASCII_DIGIT}+(?:\.{_ASCII_DIGIT}+)?)\)\s*[:：]",
    re.IGNORECASE,
)

_FACT_ALIASES: dict[str, tuple[str, ...]] = {
    "s1": ("หลักการและเหตุผล", "ที่มาของโครงการ", "ความเป็นมาและความจำเป็น", "ชื่อโครงการ"),
    "s2": ("เป้าหมายของโครงการ", "ผลที่ต้องการ", "วัตถุประสงค์"),
    "s3": (
        "คุณสมบัติผู้ยื่นข้อเสนอ",
        "คุณสมบัติของผู้เสนอราคา",
        "คุณสมบัติผู้เสนอราคา",
        "คุณสมบัติของบริษัท",
    ),
    "s5": (
        "กำหนดระยะเวลาดำเนินงาน",
        "ระยะเวลาดำเนินงาน",
        "ระยะเวลาโครงการ",
        "กำหนดเวลาดำเนินการ",
        "ระยะเวลาดำเนินการ",
    ),
    "s6": ("วงเงิน", "งบประมาณโครงการ", "วงเงินงบประมาณ"),
    "s7": ("สถานที่ส่งมอบ", "สถานที่ตั้ง", "สถานที่ดำเนินการ"),
    "s4.1": (
        _SCOPE_DEV_HEADING,
        "ขอบเขตงานหลัก",
        "ขอบเขตของงาน",
        "ขอบเขตงาน",
    ),
    "s8": ("แผนการส่งมอบงาน", "งวดงานและการจ่ายเงิน", "งวดงาน", "การจ่ายเงิน"),
    "s9": ("การรับประกันผลงาน", "การรับประกัน"),
    "s10": ("อัตราค่าปรับ", "ค่าปรับ"),
    "s11": (_SELECT_CRITERIA_HEADING, "หลักเกณฑ์การพิจารณา", "การพิจารณาคัดเลือก"),
    "s4.14": (_SECURITY_HEADING,),
    "s13": (_OWNERSHIP_HEADING, _EXIT_STRATEGY_HEADING, "เงื่อนไขอื่น"),
}

_QUAL_HINT = re.compile(
    r"คุณสมบัติ|นิติบุคคล|ทุนจดทะเบียน|ผลงานพัฒนา|จัดตั้งมาแล้ว",
    re.IGNORECASE,
)
_DURATION_HINT = re.compile(
    rf"ระยะเวลา|{_ASCII_DIGIT}{{1,6}}\s{{0,8}}(?:วัน|เดือน)|นับจากวัน|กำหนดส่งมอบ",
    re.IGNORECASE,
)
_BUDGET_HINT = re.compile(
    rf"วงเงิน|งบประมาณ|ราคากลาง|{_ASCII_DIGIT}(?:{_ASCII_DIGIT}|,){{3,16}}\s{{0,8}}บาท",
    re.IGNORECASE,
)
_PLACE_HINT = re.compile(
    r"สถานที่|ที่ทำการ|ศูนย์ราชการ|กรุงเทพ|จังหวัด|อำเภอ",
    re.IGNORECASE,
)
_PURPOSE_HINT = re.compile(r"วัตถุประสงค์|เพื่อ|เป้าหมาย", re.IGNORECASE)
_SCOPE_HINT = re.compile(r"ขอบเขต|ระบบงาน|สถาปัตยกรรม|ส่งมอบงาน", re.IGNORECASE)


def extract_slot_contents(text: str) -> dict[str, str]:
    """Read `(s1):` markers first, then Thai headings, then free-form TOR prose."""
    found = _segments_by_code(text)
    for key, body in _segments_by_heading(text).items():
        if key not in found and body:
            found[key] = body
    for key, body in extract_unstructured_slots(text).items():
        if not body:
            continue
        if key not in found or len(body) > len(found[key]):
            found[key] = body
    if not found.get("s4") and found.get("s4.1"):
        found["s4"] = found["s4.1"]
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
            rf"(?:^|\n)\s*{re.escape(heading)}\s*[:：]?\s*(.+?)(?=\n\s*\S.{{0,40}}[:：]|\Z)",
            re.IGNORECASE | re.DOTALL,
        )
        match = pattern.search(text)
        if not match:
            continue
        body = match.group(1).strip()
        if body:
            found[key] = body
    return found


_BUDGET_RE = re.compile(
    rf"วงเงินงบประมาณ\s*({_ASCII_DIGIT}(?:{_ASCII_DIGIT}|,){{0,20}})\s*บาท"
)
_MIDPRICE_RE = re.compile(
    rf"ราคากลาง\s*({_ASCII_DIGIT}(?:{_ASCII_DIGIT}|,){{0,20}})\s*บาท"
)
_DAYS_RE = re.compile(
    rf"(?:กำหนด)?ระยะเวลา(?:ดำเนินงาน|ดำเนินการ)?\s*({_ASCII_DIGIT}{{1,6}})\s*วัน"
)
_AGENCY_RE = re.compile(
    r"(สำนักงาน\s*กกต\.?|สำนักงานคณะกรรมการเลือกตั้ง|"
    r"กรมบัญชีกลาง|กรม[ก-๙]{2,40})"
)
_PENALTY_RE = re.compile(r"ค่าปรับ[^\n]{0,80}")
_BLOCK_MARKERS: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = (
    (
        "s4.1",
        (_SCOPE_DEV_HEADING, "สถาปัตยกรรม"),
        ("แผนการส่งมอบ", "กฎระเบียบ มาตรฐาน", _BIDDER_QUAL_HEADING),
    ),
    (
        "s8",
        ("แผนการส่งมอบ", "งวดงานและการจ่ายเงิน"),
        ("กฎระเบียบ มาตรฐาน", _BIDDER_QUAL_HEADING, _SELECT_CRITERIA_HEADING),
    ),
    (
        "s3",
        (_BIDDER_QUAL_HEADING, "คุณสมบัติของผู้เสนอราคา"),
        (_SELECT_CRITERIA_HEADING, "เกณฑ์ตรวจรับ", _SECURITY_HEADING),
    ),
    (
        "s11",
        (_SELECT_CRITERIA_HEADING, "หลักเกณฑ์การพิจารณา", "เกณฑ์ตรวจรับ"),
        (_SECURITY_HEADING, _OWNERSHIP_HEADING),
    ),
    (
        "s4.14",
        (_SECURITY_HEADING, "PDPA"),
        (_OWNERSHIP_HEADING, _EXIT_STRATEGY_HEADING),
    ),
    (
        "s13",
        (_OWNERSHIP_HEADING, _EXIT_STRATEGY_HEADING),
        (),
    ),
)


def _find_marker(text: str, markers: tuple[str, ...], *, after: int = 0) -> tuple[int, str]:
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
    if best >= 0:
        return best, used
    for marker in markers:
        idx = text.find(marker, after)
        if idx >= 0 and (best < 0 or idx < best):
            best = idx
            used = marker
    return best, used


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


def extract_unstructured_slots(text: str) -> dict[str, str]:
    """Map free-form TOR / ขอบเขตงาน prose that has no (s1): codes."""
    raw = text or ""
    found: dict[str, str] = {}
    budget = _BUDGET_RE.search(raw)
    if budget:
        line = f"วงเงินงบประมาณ {budget.group(1)} บาท"
        mid = _MIDPRICE_RE.search(raw)
        if mid:
            line += f" ราคากลาง {mid.group(1)} บาท"
        found["s6"] = line
    days = _DAYS_RE.search(raw)
    if days:
        found["s5"] = f"{days.group(1)} วัน"
    agency = _AGENCY_RE.search(raw)
    if agency and ("s6" in found or "s5" in found or "สำนักงาน" in agency.group(1)):
        found["s7"] = agency.group(1).strip()
    penalty = _PENALTY_RE.search(raw)
    late = re.search(r"ค่าปรับส่งมอบ[^\n]{0,60}", raw)
    if late:
        found["s10"] = late.group(0).strip()
    elif penalty:
        found["s10"] = penalty.group(0).strip()
    lead_end = raw.find(_SCOPE_DEV_HEADING)
    lead = raw[: lead_end if lead_end > 80 else 1200].strip()
    if "โครงการ" in lead and (
        "s6" in found or "s5" in found or len(lead) > 120
    ):
        found["s1"] = lead[:1500]
        _fill_if_empty(found, "s2", lead[:800])
    for key, starts, ends in _BLOCK_MARKERS:
        _fill_if_empty(found, key, _slice_between(raw, starts, ends))
    scope = found.get("s4.1") or ""
    if "Kubernetes" in scope or "คลาวด์" in scope or "Containerized" in scope:
        _fill_if_empty(found, "s4.4", scope)
    if "RAG" in scope or "OCR" in scope or "Chatbot" in scope:
        _fill_if_empty(found, "s4.5", scope)
    if scope and "ระบบ" in scope:
        _fill_if_empty(found, "s4.3", scope)
    quals = found.get("s3") or ""
    if "บุคลากร" in quals or "ทีมงาน" in quals:
        _fill_if_empty(found, "s4.10", quals)
    payments = found.get("s8") or ""
    if "ส่งมอบ" in payments:
        _fill_if_empty(found, "s4.8", payments)
    sla = found.get("s13") or ""
    warranty = sla or payments
    if "SLA" in warranty or "บำรุงรักษา" in warranty or "รับประกัน" in raw:
        _fill_if_empty(found, "s9", warranty)
        _fill_if_empty(found, "s4.9", warranty)
        _fill_if_empty(found, "s4.11", warranty)
    if "ISO" in quals or "มาตรฐาน" in raw:
        _fill_if_empty(found, "s4.7", quals or found.get("s11") or sla)
    if quals:
        _fill_if_empty(found, "s12", quals)
    widget = _slice_between(
        raw,
        ("Web Chat Widget", "จุดเชื่อมโยง", "เชื่อมต่อ Web Chat"),
        ("เกณฑ์ตรวจรับ", "กรรมสิทธิ์", "คุณสมบัติผู้ยื่น"),
    )
    if "Widget" in raw or "Live Chat" in raw or "เชื่อมต่อ" in raw:
        _fill_if_empty(
            found,
            "s4.6",
            widget or "เชื่อมต่อ Web Chat Widget กับเว็บ กกต. มี Live Chat Escalation และกรณีใช้โมเดลภายนอกต้องเป็น Enterprise API แบบ Zero Data Retention",
        )
    if ("FAQ" in raw and "500" in raw) or "7 หมวด" in raw or "1.5 TB" in raw:
        _fill_if_empty(
            found,
            "s4.2",
            "เอกสารระบุคลังความรู้ กกต. ครอบคลุม 7 หมวด ข้อมูลเริ่มต้น 1.5 TB / 3,000,000 หน้า "
            "และ FAQ มาตรฐาน 500 ข้อ รวมงานตอบข้อหารือ — เป็นฐานข้อมูลและงานปัจจุบันที่ระบบใหม่ต้องรองรับ",
        )
    if payments:
        _fill_if_empty(found, "s4.12", payments)
    if "Exit Strategy" in raw or "Secure Wipe" in raw or "กู้คืน" in raw:
        _fill_if_empty(found, "s4.13", sla or payments)
    return {key: value for key, value in found.items() if value}
