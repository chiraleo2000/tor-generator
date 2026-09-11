"""Thai-only drafting helpers shared by Phase 3 chat and orchestrator agents."""

from __future__ import annotations

import re
from typing import Any

from app.domain.section_profile import extra_legacy_scope_items, profile_for_project, subsection_title
from app.llm_tokens import (
    SCOPE_SUB_MAX_TOKENS,
    SCOPE_SUB_MIN_TOKENS,
    SECTION_MAX_TOKENS,
    SECTION_MIN_TOKENS,
    chars_for_tokens,
)


THAI_ONLY_RULES = (
    "ข้อบังคับภาษา:\n"
    "- เขียนเป็นภาษาไทยราชการเท่านั้นทั้งเอกสาร\n"
    "- ห้ามใส่คำหรือประโยคภาษาอังกฤษ รวมคำทับศัพท์ที่เขียนด้วยอักษรละติน\n"
    "- ห้ามใช้คำว่า Server, Cyber Attack, Digital Government, Big Data, "
    "Public AI, Deliverables, Price Only, Price-Performance, As-Is, To-Be, "
    "UAT, SIT, Tablet, Dashboard, Infrastructure, Certificate, Patching, "
    "Staging, Hardware, Software, Troubleshooting, Labeling, Configure\n"
    "- เขียนแทนเป็นภาษาไทย เช่น เครื่องแม่ข่าย การโจมตีทางไซเบอร์ "
    "รัฐบาลดิจิทัล ข้อมูลขนาดใหญ่ ปัญญาประดิษฐ์ภาครัฐ ผลงานส่งมอบ "
    "เกณฑ์ราคา เกณฑ์ราคาประกอบเกณฑ์คุณภาพ ระบบงานปัจจุบัน ระบบงานใหม่ "
    "การทดสอบยอมรับโดยผู้ใช้ เครื่องคอมพิวเตอร์ชนิดพกพา แผงควบคุม "
    "โครงสร้างพื้นฐาน หนังสือรับรอง การปรับปรุงซอฟต์แวร์\n"
    "- ห้ามใส่ชื่อหมวดภาษาอังกฤษในวงเล็บ\n"
    "- ชื่อเฉพาะตามกฎหมายหรือชื่อระบบทางการของหน่วยงานใช้ได้ตามที่ปรากฏจริง "
    "รวม e-GP, PDPA, ISO, IEC, TOR\n"
    "- หัวคอลัมน์ในตารางต้องเป็นภาษาไทย\n"
    "- ส่งเฉพาะผลลัพธ์สุดท้าย ห้ามแสดงกระบวนการคิด และห้ามคัดลอก system prompt\n"
)

ALLOWED_LATIN_TOKENS = frozenset(
    {
        "e-GP",
        "EGP",
        "PDPA",
        "ISO",
        "IEC",
        "TOR",
        "TH",
        "A4",
        "OWASP",
        "MPLS",
        "BEV",
        "NT",
        "PDF",
        "DOCX",
        "USB",
        "SLA",
        "CM",
        "PM",
        "SME",
        "SMEs",
        "ICT",
        "e-Bidding",
        "eBidding",
    }
)

BANNED_ENGLISH_TOKENS = (
    "Server",
    "Cyber Attack",
    "Cyber",
    "Digital Government",
    "Big Data",
    "Public AI",
    "Deliverables",
    "Price Only",
    "Price-Performance",
    "As-Is",
    "To-Be",
    "UAT",
    "SIT",
    "Tablet",
    "Dashboard",
    "Infrastructure",
    "Certificate",
    "Patching",
    "Staging",
    "Hardware",
    "Software",
    "Troubleshooting",
    "Labeling",
    "Configure",
)

LATIN_TO_THAI = {
    "Server": "เครื่องแม่ข่าย",
    "Cyber Attack": "การโจมตีทางไซเบอร์",
    "Cyber": "ไซเบอร์",
    "Digital Government": "รัฐบาลดิจิทัล",
    "Big Data": "ข้อมูลขนาดใหญ่",
    "Public AI": "ปัญญาประดิษฐ์ภาครัฐ",
    "Deliverables": "ผลงานส่งมอบ",
    "Price Only": "เกณฑ์ราคา",
    "Price-Performance": "เกณฑ์ราคาประกอบเกณฑ์คุณภาพ",
    "As-Is": "ระบบงานปัจจุบัน",
    "To-Be": "ระบบงานใหม่",
    "UAT": "การทดสอบยอมรับโดยผู้ใช้",
    "SIT": "การทดสอบบูรณาการระบบ",
    "Tablet": "เครื่องคอมพิวเตอร์ชนิดพกพา",
    "Dashboard": "แผงควบคุม",
    "Infrastructure": "โครงสร้างพื้นฐาน",
    "Certificate": "หนังสือรับรอง",
    "Patching": "การปรับปรุงซอฟต์แวร์",
    "Staging": "สภาพแวดล้อมทดสอบก่อนใช้งานจริง",
    "Hardware": "ครุภัณฑ์คอมพิวเตอร์",
    "Software": "โปรแกรมคอมพิวเตอร์",
    "Troubleshooting": "การแก้ไขปัญหา",
    "Labeling": "การติดป้าย",
    "Configure": "การกำหนดค่า",
}

MIN_SANITIZED_THAI_CHARS = 80


class ThaiOnlyNotAttachedError(ValueError):
    """Raised when a drafting prompt is missing THAI_ONLY_RULES."""


def ensure_thai_only_attached(prompt: str) -> None:
    if THAI_ONLY_RULES not in (prompt or ""):
        raise ThaiOnlyNotAttachedError("THAI_ONLY_RULES missing from drafting prompt")


def attach_thai_only(prompt: str) -> str:
    """Prepend THAI_ONLY_RULES when missing, then fail-closed (Req 7.2)."""
    text = prompt or ""
    if THAI_ONLY_RULES not in text:
        text = f"{THAI_ONLY_RULES}\n{text}"
    ensure_thai_only_attached(text)
    return text


def detect_unauthorized_english(text: str) -> list[str]:
    """Return unauthorized Latin tokens (Req 7.3). Official names are allowed."""
    found: list[str] = []
    for token in BANNED_ENGLISH_TOKENS:
        if re.search(rf"(?i)(?<![A-Za-z]){re.escape(token)}(?![A-Za-z])", text or ""):
            found.append(token)
    allowed = {item.upper() for item in ALLOWED_LATIN_TOKENS}
    for match in re.findall(r"[A-Za-z][A-Za-z0-9\-]*", text or ""):
        if match.upper() in allowed:
            continue
        if match not in found:
            found.append(match)
    return found


def thai_char_count(text: str | None) -> int:
    return sum(1 for char in (text or "") if "\u0e00" <= char <= "\u0e7f")


def sanitize_unauthorized_english(text: str) -> str:
    """Keep Thai TOR prose; replace or drop leftover Latin tokens."""
    out = text or ""
    for src, dest in sorted(LATIN_TO_THAI.items(), key=lambda item: -len(item[0])):
        out = re.sub(
            rf"(?i)(?<![A-Za-z]){re.escape(src)}(?![A-Za-z])",
            dest,
            out,
        )
    allowed = {item.upper() for item in ALLOWED_LATIN_TOKENS}

    def _keep_allowed(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.upper() in allowed:
            return token
        return ""

    out = re.sub(r"[A-Za-z][A-Za-z0-9\-]*", _keep_allowed, out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


SECTION_OWNERSHIP_TABLE = (
    "เจ้าของสาระต่อหมวด (ห้ามซ้ำข้ามหมวด):\n"
    "- ความเป็นมา/บริบทหน่วยงาน — เฉพาะหมวดความเป็นมา\n"
    "- วัตถุประสงค์ (ข้อ «เพื่อ») — เฉพาะหมวดวัตถุประสงค์\n"
    "- คุณสมบัติผู้เสนอราคา/บุคลากร — เฉพาะหมวดคุณสมบัติ\n"
    "- ขอบเขตงาน/สเปก/ผลงาน — เฉพาะหมวดขอบเขต\n"
    "- ระยะเวลา/ตารางงวดส่งมอบ — เฉพาะหมวดระยะเวลา\n"
    "- วงเงิน/ราคากลาง/วิธีจัดซื้อ — เฉพาะหมวดวงเงิน\n"
    "- งวดจ่ายเงิน — เฉพาะหมวดงวดจ่าย\n"
    "- รับประกัน ค่าปรับ เกณฑ์คัดเลือก เงื่อนไข ลิขสิทธิ์ ความลับ — เฉพาะหมวดเจ้าของ\n"
)


def substance_rules(*, min_tokens: int, max_tokens: int) -> str:
    """Prompt block that prioritises substance over forced length."""
    return (
        "ข้อบังคับสาระและขอบเขต:\n"
        "- เขียนเฉพาะสาระที่หมวดนี้ต้องมี จากข้อเท็จจริงในเอกสารขั้นที่ ๐ และบริบทที่ให้\n"
        "- ห้ามขยายด้วยคำซ้ำ สำนวนว่าง หรือรายละเอียดที่ไม่มีในเอกสารต้นทาง\n"
        "- ห้ามคัดลอกย่อหน้าจากหมวดอื่น ห้ามเล่าซ้ำความเป็นมา/ภารกิจหน่วยงานนอกหมวดความเป็นมา\n"
        "- ห้ามใส่รายละเอียดทางเทคนิค/งบ/งวดจ่าย/คุณสมบัติในหมวดที่ไม่ใช่เจ้าของสาระ\n"
        "- อยู่เฉพาะในขอบเขตหมวดนี้ ความยาวพอประมาณตามสาระ ไม่บังคับยาวหลายย่อหน้า\n"
        f"- ใช้พื้นที่ได้ถึง {max_tokens} โทเคน "
        f"(ประมาณ {chars_for_tokens(max_tokens)} ตัวอักษร) เป็นเพดาน ไม่ใช่เป้าขั้นต่ำ\n"
        f"- ขั้นต่ำอ้างอิงประมาณ {min_tokens} โทเคน เมื่อมีข้อมูลเพียงพอ — "
        "อย่าเติมน้ำเพื่อให้ถึง\n"
    )


SUBSTANCE_RULES = substance_rules(
    min_tokens=SECTION_MIN_TOKENS, max_tokens=SECTION_MAX_TOKENS
)
SCOPE_SUB_SUBSTANCE_RULES = substance_rules(
    min_tokens=SCOPE_SUB_MIN_TOKENS, max_tokens=SCOPE_SUB_MAX_TOKENS
)


def section_boundary_hint(section_key: str | None) -> str:
    """One-line scope reminder for a TOR main section."""
    hints = {
        "s1": "หมวดนี้เท่านั้นเล่าบริบทหน่วยงาน ปัญหา และความจำเป็น — ห้ามซ้ำในหมวดอื่น",
        "s2": "หมวดนี้เท่านั้นเขียนข้อ «เพื่อ»/วัตถุประสงค์ — ห้ามเล่าความเป็นมายาวหรือรายละเอียดงาน",
        "s3": "หมวดนี้เท่านั้นกำหนดคุณสมบัติ/บุคลากร — ห้ามใส่สเปกฮาร์ดแวร์หรือขอบเขตงาน",
        "s4": "หมวดนี้เท่านั้นรายละเอียดงาน/สเปก/ผลงาน — ห้ามเล่าความเป็นมาหรืองบประมาณซ้ำ",
        "s5": "หมวดนี้เท่านั้นระยะเวลาและตารางงวดส่งมอบ — ห้ามใส่รายละเอียดงานหรืองวดจ่ายเงิน",
        "s6": "หมวดนี้เท่านั้นวงเงิน ราคากลาง และวิธีจัดซื้อ — ห้ามเล่าขอบเขตงานยาว",
        "s7": "หมวดนี้เท่านั้นสถานที่ดำเนินการ — ห้ามซ้ำขอบเขตงาน",
        "s8": "หมวดนี้เท่านั้นตารางงวดจ่ายเงิน — ห้ามซ้ำรายละเอียดงานจาก s4",
        "s9": "หมวดนี้เท่านั้นเงื่อนไขการรับประกัน",
        "s10": "หมวดนี้เท่านั้นค่าปรับและเงื่อนไข",
        "s11": "หมวดนี้เท่านั้นเกณฑ์คัดเลือกและตารางน้ำหนักคะแนน",
        "s12": "หมวดนี้เท่านั้นเอกสารที่ต้องยื่น",
        "s13": "หมวดนี้เท่านั้นเงื่อนไขอื่น ลิขสิทธิ์ ความลับ",
    }
    if not section_key:
        return ""
    line = hints.get(section_key, "")
    return f"{line}\n" if line else ""

TABLE_FORMAT_HINT = (
    "ถ้ามีรายการหลายแถว ให้ใช้ตารางแบบมาร์กดาวน์ เช่น:\n"
    "| รายการ | จำนวน | หน่วย |\n"
    "| --- | --- | --- |\n"
    "| เครื่องคอมพิวเตอร์แม่ข่าย | ๒ | เครื่อง |\n"
)

PAYMENT_TABLE_TEMPLATE = (
    "| งวดที่ | ผลงานที่ต้องส่งมอบ | ระยะเวลา | ร้อยละ | จำนวนเงิน (บาท) |\n"
    "| --- | --- | --- | --- | --- |\n"
    "| ๑ | … | ภายใน … วัน | … | … |\n"
    "| รวม | | | ๑๐๐ | … |"
)

TIMELINE_TABLE_TEMPLATE = (
    "| งวดที่ | ผลงานที่ต้องส่งมอบ | ภายใน (วัน) |\n"
    "| --- | --- | --- |\n"
    "| ๑ | … | … |"
)

EVALUATION_TABLE_TEMPLATE = (
    "| หัวข้อ | น้ำหนัก (ร้อยละ) | วิธีให้คะแนน |\n"
    "| --- | --- | --- |\n"
    "| ด้านคุณภาพ | … | … |\n"
    "| ด้านราคา | … | … |\n"
    "| รวม | ๑๐๐ | |"
)

LICENSE_ICT_TABLE_TEMPLATE = (
    "| ลำดับ | รายการ | จำนวนสิทธิ์ | ราคาต่อหน่วย (บาท) | ราคารวม (บาท) | "
    "ใช้เกณฑ์กลาง ICT | กรณีไม่ใช้เกณฑ์กลางให้ระบุเหตุผล |\n"
    "| --- | --- | --- | --- | --- | --- | --- |\n"
    "| ๑ | … | … | … | … | ใช้ / ไม่ใช้ | … |\n"
    "| รวม | | | | … | | |"
)

LICENSE_ICT_HEADERS = (
    "ลำดับ",
    "รายการ",
    "จำนวนสิทธิ์",
    "ราคาต่อหน่วย (บาท)",
    "ราคารวม (บาท)",
    "ใช้เกณฑ์กลาง ICT",
    "กรณีไม่ใช้เกณฑ์กลางให้ระบุเหตุผล",
)

_CHECK_YES = frozenset(
    {"", "✔", "✓", "√", "x", "X", "ใช่", "ใช้", "1", "๑", "/"}
)
_CHECK_NO = frozenset({"ไม่ใช้", "ไม่", "–", "-", "—"})
_ROW_SPLIT = re.compile(r"\t+|[ ]{2,}|[|｜]")
_NUM_CELL = re.compile(r"^[0-9๐-๙]+([.,][0-9๐-๙]+)?$")
_MONEY_CELL = re.compile(r"^[0-9๐-๙][0-9๐-๙,]*(\.[0-9๐-๙]+)?$")


def _split_table_cells(line: str) -> list[str]:
    raw = (line or "").strip()
    if not raw:
        return []
    if raw.startswith("|") or raw.endswith("|") or "|" in raw or "｜" in raw:
        cells = [c.strip() for c in raw.strip("|｜").replace("｜", "|").split("|")]
        return [c for c in cells if c is not None]
    return [c.strip() for c in _ROW_SPLIT.split(raw) if c.strip()]


def _is_license_header_row(cells: list[str]) -> bool:
    joined = "".join(cells)
    return "ลำดับ" in joined and "รายการ" in joined


def _is_use_subheader_row(cells: list[str]) -> bool:
    nonempty = [c for c in cells if c.strip()]
    if not nonempty:
        return True
    return all(c in {"ใช้", "ไม่ใช้", "เกณฑ์กลาง ICT", "เกณฑ์กลาง"} for c in nonempty)


def _is_sep_row(cells: list[str]) -> bool:
    if not cells:
        return False
    return all(re.fullmatch(r"[:\-\s]+", c or "") for c in cells)


def _ict_use_value(*candidates: str) -> str:
    for raw in candidates:
        token = (raw or "").strip()
        if not token:
            continue
        if token in _CHECK_YES or any(mark in token for mark in ("", "✔", "✓", "√")):
            return "ใช้"
        if token in _CHECK_NO:
            return "ไม่ใช้"
    return ""


def _looks_like_license_table(text: str) -> bool:
    body = text or ""
    return "ลำดับ" in body and "รายการ" in body and (
        "เกณฑ์กลาง" in body or "ลิขสิทธิ์" in body or "ครุภัณฑ์" in body
    )


def _normalize_license_data_row(cells: list[str]) -> list[str] | None:
    """Map a raw row into the 7-column ICT license shape."""
    if not cells or _is_license_header_row(cells) or _is_use_subheader_row(cells):
        return None
    if _is_sep_row(cells):
        return None
    first = cells[0].strip()
    if first in {"รวม", "รวมทั้งสิ้น", "ยอดรวม"}:
        total = ""
        for cell in reversed(cells[1:]):
            if _MONEY_CELL.match(cell.replace(" ", "")):
                total = cell
                break
        return ["รวม", "", "", "", total, "", ""]
    # Skip title-only lines
    if len(cells) == 1 and not _NUM_CELL.match(first):
        return None
    # Pad / trim toward at least item + qty-ish columns
    padded = list(cells) + [""] * 8
    seq = padded[0]
    name = padded[1]
    qty = padded[2]
    unit = padded[3]
    total = padded[4]
    # Broken dual ICT columns: ... | use-mark | no-mark | reason
    if len(cells) >= 7:
        use = _ict_use_value(padded[5], padded[6])
        reason = padded[7] if len(cells) >= 8 else (padded[6] if use and padded[6] not in _CHECK_YES and padded[6] not in _CHECK_NO and "" not in padded[6] else "")
        if use or any(m in padded[5] + padded[6] for m in ("", "✔", "✓", "√")):
            return [seq, name, qty, unit, total, use or "ใช้", reason]
    use = _ict_use_value(padded[5])
    reason = padded[6]
    if not name and not qty:
        return None
    return [seq, name, qty, unit, total, use, reason]


def _md_row(cells: list[str]) -> str:
    return "| " + " | ".join(c.strip() for c in cells) + " |"


def normalize_license_ict_table(text: str) -> str:
    """Force licenses content into a single 7-column markdown ICT table.

    Accepts tab-separated Word paste, space-aligned plain text, or broken
    pipe tables with separate ใช้/ไม่ใช้ columns. Deduplicates repeated blocks.
    """
    if not (text or "").strip():
        return ""
    lines = text.replace("\r\n", "\n").split("\n")
    preface: list[str] = []
    data_rows: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    found_header = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if re.fullmatch(r"(?i)\[?\s*Table\s*[0-9๐-๙]+\s*\]?", stripped):
            continue
        cells = _split_table_cells(stripped)
        if _is_license_header_row(cells):
            found_header = True
            continue
        if found_header and _is_use_subheader_row(cells):
            continue
        if found_header and _is_sep_row(cells):
            continue
        if found_header:
            row = _normalize_license_data_row(cells)
            if not row:
                # Non-table prose after a table ends the block; allow later tables.
                if not stripped.startswith("|") and "\t" not in line and len(cells) <= 1:
                    found_header = False
                    if stripped and stripped not in {"ใช้", "ไม่ใช้"}:
                        preface.append(stripped)
                continue
            key = tuple(row)
            if key in seen:
                continue
            # Also dedupe by item identity (seq+name+qty+total)
            identity = (row[0], row[1], row[2], row[4])
            if any(
                (r[0], r[1], r[2], r[4]) == identity and r[0] != "รวม" for r in data_rows
            ):
                continue
            seen.add(key)
            data_rows.append(row)
            continue
        # No header yet — title / prose before the table
        if _looks_like_license_table(stripped) and "ลำดับ" in stripped:
            # Single-line header without clear cells
            found_header = True
            continue
        if stripped not in preface and not stripped.startswith("licenses"):
            # Drop section title echo; keep other notes
            if "ครุภัณฑ์" in stripped and "ลิขสิทธิ์" in stripped:
                continue
            preface.append(stripped)

    if not data_rows:
        # Last resort: try whole text as one pipe/TSV block without requiring header pass
        return sanitize_scope_draft_tables(text).strip()

    # Ensure a รวม row when totals exist and none present
    if not any(r[0] == "รวม" for r in data_rows):
        totals = [r[4] for r in data_rows if r[4]]
        if len(totals) == 1:
            data_rows.append(["รวม", "", "", "", totals[0], "", ""])

    parts: list[str] = []
    if preface:
        # Keep short notes only; drop duplicated plain tables left in preface
        notes = [
            p
            for p in preface
            if "ลำดับ" not in p and not _NUM_CELL.match(p.split()[0] if p.split() else "")
        ]
        if notes:
            parts.append("\n".join(notes[:3]))
    parts.append(_md_row(list(LICENSE_ICT_HEADERS)))
    parts.append("| --- | --- | --- | --- | --- | --- | --- |")
    for row in data_rows:
        parts.append(_md_row(row))
    return "\n".join(parts).strip()


PERSONNEL_TABLE_TEMPLATE = (
    "| ตำแหน่ง | คุณวุฒิ | ประสบการณ์ | จำนวน | ระยะเวลา (เดือน) |\n"
    "| --- | --- | --- | --- | --- |\n"
    "| … | … | ไม่น้อยกว่า … ปี | … | … |"
)


# Manual TOR outline numbers the model must never emit (export adds headings).
_MANUAL_HEADING_NUM = re.compile(
    r"(?m)^[\s]*("
    r"[0-9]{1,2}(?:\.[0-9]{1,2}){0,3}"
    r"|[๐-๙]{1,2}(?:\.[๐-๙]{1,2}){0,3}"
    r"|[0-9]{1,2}\.[๐-๙]{1,2}(?:\.[๐-๙]{1,2})?"
    r"|[๐-๙]{1,2}\.[0-9]{1,2}(?:\.[0-9]{1,2})?"
    r")[\s]*[\)\].:：\-–]?\s+"
)
_TABLE_PLACEHOLDER = re.compile(r"(?i)\[?\s*Table\s*[0-9๐-๙]+\s*\]?")
_DUP_HEADER_MARKERS = ("ลำดับ", "รายการ", "เกณฑ์กลาง")


def strip_manual_section_numbers(text: str) -> str:
    """Remove leading outline numbers like 8.1 / 8.๑ from drafted lines."""
    if not text:
        return ""
    lines: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        # Preserve markdown / TSV / spaced table rows — never strip their index col.
        if (
            stripped.startswith("|")
            or "\t" in line
            or (stripped.count("|") >= 2)
            or (
                "  " in stripped
                and bool(_NUM_CELL.match(stripped.split()[0] if stripped.split() else ""))
            )
        ):
            lines.append(line.rstrip())
            continue
        cleaned = _MANUAL_HEADING_NUM.sub("", line, count=1)
        lines.append(cleaned.rstrip())
    return "\n".join(lines).strip()


def sanitize_scope_draft_tables(text: str) -> str:
    """Drop Table-N placeholders and repeated header rows inside markdown tables."""
    if not text:
        return ""
    out = _TABLE_PLACEHOLDER.sub("", text)
    lines = out.replace("\r\n", "\n").split("\n")
    cleaned: list[str] = []
    seen_header = False
    in_table = False
    for line in lines:
        raw = line.strip()
        if raw.startswith("|") and "---" not in raw.replace(" ", ""):
            cells = [c.strip() for c in raw.strip("|").split("|")]
            looks_header = any(marker in "".join(cells) for marker in _DUP_HEADER_MARKERS) and (
                "ลำดับ" in cells[0] or (len(cells) > 1 and cells[0] == "ลำดับ")
            )
            if looks_header and "รายการ" in "".join(cells):
                if seen_header and in_table:
                    continue
                seen_header = True
                in_table = True
            cleaned.append(line.rstrip())
            continue
        if raw.startswith("|") and "---" in raw:
            in_table = True
            cleaned.append(line.rstrip())
            continue
        if not raw.startswith("|"):
            in_table = False
            seen_header = False
        cleaned.append(line.rstrip())
    body = "\n".join(cleaned)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


_SOURCE_CHAPTER_EIGHT = re.compile(
    r"(?m)^[\s]*(?:8|๘)(?:[\.．][0-9๐-๙]{1,2}){1,3}[\s]*[\)\].:：\-–]?\s+"
)

# Method/chapter-8 blob — wrong for every scope sub except functional.
_METHOD_BLOB_MARKERS = (
    "ขอบเขตและวิธีการดำเนินงาน",
    "ข้อกำหนดทั่วไป",
    "การบันทึกและนำเข้าข้อมูล",
    "การประมวลผล",
    "การให้บริการ",
    "การบริหารจัดการ",
    "Back End",
    "8.๑",
    "8.1",
    "๘.๑",
    "8.๒",
    "๘.๒",
    "8.๓",
    "๘.๓",
)

# Markers that strongly belong to another subsection (foreign leakage).
# Keys are canonical semantic names (legacy s4.x is remapped in _norm_scope_key).
_TEST_POLLUTION = (
    "ขอบเขตและวิธีการดำเนินงาน",
    "ข้อกำหนดทั่วไป",
    "การบันทึกและนำเข้าข้อมูล",
    "การบริหารจัดการ",
    "เกณฑ์กลาง ICT",
    "จำนวนสิทธิ์",
)
_LICENSE_POLLUTION = (
    "ขอบเขตและวิธีการดำเนินงาน",
    "ข้อกำหนดทั่วไป",
    "แผนทดสอบ",
    "เกณฑ์ผ่าน",
    "การทดสอบหน่วย",
    "การทดสอบยอมรับ",
)
_SCOPE_FOREIGN_MARKERS: dict[str, tuple[str, ...]] = {
    "testing": _TEST_POLLUTION,
    "licenses": _LICENSE_POLLUTION,
    "system_overview": (
        "เกณฑ์กลาง ICT",
        "แผนทดสอบ",
        "ข้อกำหนดทั่วไป",
        "การบันทึกและนำเข้าข้อมูล",
        "จำนวนสิทธิ์",
    ),
    "functional": (
        "เกณฑ์กลาง ICT",
        "แผนทดสอบหน่วย",
        "การทดสอบยอมรับโดยผู้ใช้",
        "ใช้เกณฑ์กลาง ICT",
        "จำนวนสิทธิ์",
    ),
    "integration": _METHOD_BLOB_MARKERS,
    "standards_security": (
        "ขอบเขตและวิธีการดำเนินงาน",
        "เกณฑ์กลาง ICT",
        "การบันทึกและนำเข้าข้อมูล",
        "แผนทดสอบหน่วย",
    ),
    "deliverable_docs": _METHOD_BLOB_MARKERS,
    "training": _METHOD_BLOB_MARKERS,
    "project_team": _METHOD_BLOB_MARKERS,
    "sla_warranty": _METHOD_BLOB_MARKERS,
    # Other procurement-type headings: treat method-chapter blob as foreign.
    "specification": _METHOD_BLOB_MARKERS,
    "items": _METHOD_BLOB_MARKERS,
    "installation": _METHOD_BLOB_MARKERS,
    "delivery_acceptance": _METHOD_BLOB_MARKERS,
    "documents": _METHOD_BLOB_MARKERS,
    "after_sales": _METHOD_BLOB_MARKERS,
    "general_conditions": _METHOD_BLOB_MARKERS,
    "asset_list": _METHOD_BLOB_MARKERS,
    "cm": _METHOD_BLOB_MARKERS,
    "pm": _METHOD_BLOB_MARKERS,
    "sla": _METHOD_BLOB_MARKERS,
    "helpdesk": _METHOD_BLOB_MARKERS,
    "spare_parts": _METHOD_BLOB_MARKERS,
    "onsite_staff": _METHOD_BLOB_MARKERS,
    "reporting": _METHOD_BLOB_MARKERS,
    "backup": _METHOD_BLOB_MARKERS,
    "service_spec": _METHOD_BLOB_MARKERS,
    "provided_equipment": _METHOD_BLOB_MARKERS,
    "availability": _METHOD_BLOB_MARKERS,
    "noc": _METHOD_BLOB_MARKERS,
    "usage_report": _METHOD_BLOB_MARKERS,
    "lease_maintenance": _METHOD_BLOB_MARKERS,
    "lessee_rights": _METHOD_BLOB_MARKERS,
    "workload": _METHOD_BLOB_MARKERS,
    "workflow": _METHOD_BLOB_MARKERS,
    "quality_standard": _METHOD_BLOB_MARKERS,
    "resources": _METHOD_BLOB_MARKERS,
    "custody": _METHOD_BLOB_MARKERS,
    "progress_report": _METHOD_BLOB_MARKERS,
    "output_delivery": _METHOD_BLOB_MARKERS,
    "methodology": _METHOD_BLOB_MARKERS,
    "population": _METHOD_BLOB_MARKERS,
    "instrument": _METHOD_BLOB_MARKERS,
    "fieldwork": _METHOD_BLOB_MARKERS,
    "analysis": _METHOD_BLOB_MARKERS,
    "expert_review": _METHOD_BLOB_MARKERS,
    "reports": _METHOD_BLOB_MARKERS,
    "expert_team": _METHOD_BLOB_MARKERS,
    "works": _METHOD_BLOB_MARKERS,
    "drawings": _METHOD_BLOB_MARKERS,
    "demolition": _METHOD_BLOB_MARKERS,
    "site_access": _METHOD_BLOB_MARKERS,
    "supervision": _METHOD_BLOB_MARKERS,
    "handover": _METHOD_BLOB_MARKERS,
}


def _norm_scope_key(sub_key: str | None) -> str:
    """Normalize to semantic storage key (e.g. s4.5 → licenses)."""
    key = (sub_key or "").removeprefix("scope.").strip()
    if not key:
        return ""
    if key.startswith("s4."):
        from app.domain.tor_taxonomy import LEGACY_SCOPE_MAP

        mapped = LEGACY_SCOPE_MAP.get(key)
        if mapped:
            return str(mapped).removeprefix("scope.").strip() or key
    return key


def method_hits_safe(body: str) -> int:
    return sum(1 for marker in _METHOD_BLOB_MARKERS if marker in body)


def is_scope_content_wrong_owner(sub_key: str | None, text: str) -> bool:
    """True when a scope subsection draft clearly belongs to another heading."""
    key = _norm_scope_key(sub_key)
    body = text or ""
    if not body.strip() or not key:
        return False
    # Full method chapter is only legal under functional.
    if key != "functional":
        if "ขอบเขตและวิธีการดำเนินงาน" in body:
            return True
        if method_hits_safe(body) >= 2:
            return True
    foreign = _SCOPE_FOREIGN_MARKERS.get(key, _METHOD_BLOB_MARKERS)
    hits = sum(1 for marker in foreign if marker in body)
    if hits >= 2:
        return True
    # Licenses must look like a table / ICT list, not prose method dump.
    if key == "licenses":
        if "ขอบเขตและวิธีการ" in body or "ข้อกำหนดทั่วไป" in body:
            return True
        if body.count("|") < 2 and method_hits_safe(body) >= 1:
            return True
    return False


# Back-compat alias used by older call sites/tests.
def is_testing_content_polluted(text: str) -> bool:
    return is_scope_content_wrong_owner("testing", text)


def strip_source_chapter_eight_numbers(text: str) -> str:
    """Remove 8.x / ๘.x outline prefixes only — keep user 1. / 1.1 numbering."""
    if not text:
        return ""
    lines: list[str] = []
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.strip().startswith("|"):
            lines.append(line.rstrip())
            continue
        lines.append(_SOURCE_CHAPTER_EIGHT.sub("", line, count=1).rstrip())
    return "\n".join(lines).strip()


def testing_fallback_draft(user_feedback: str = "") -> str:
    """Deterministic testing/acceptance outline when LLM leaks method text."""
    note = (user_feedback or "").strip()
    body = (
        "1. การทดสอบหน่วย\n"
        "1.1 ผู้รับจ้างต้องจัดทำการทดสอบหน่วยของโมดูลหลักก่อนบูรณาการระบบ\n"
        "1.2 เกณฑ์ผ่าน: กรณีทดสอบหลักผ่านครบ และมีรายงานผลเป็นหลักฐาน\n"
        "\n"
        "2. การทดสอบบูรณาการระบบ\n"
        "2.1 ทดสอบการเชื่อมโยงระหว่างโมดูลและระบบที่เกี่ยวข้องของผู้ว่าจ้าง\n"
        "2.2 เกณฑ์ผ่าน: การเชื่อมโยงทำงานได้ตามที่กำหนดโดยไม่มีข้อผิดพลาดวิกฤต\n"
        "\n"
        "3. การทดสอบประสิทธิภาพ\n"
        "3.1 ทดสอบภาระงานและเวลาตอบสนองตามข้อกำหนดของผู้ว่าจ้าง\n"
        "3.2 เกณฑ์ผ่าน: ผลวัดอยู่ในเกณฑ์ที่ผู้ว่าจ้างยอมรับ\n"
        "\n"
        "4. การทดสอบความมั่นคงปลอดภัย\n"
        "4.1 ทดสอบการยืนยันตัวตน สิทธิ์ผู้ใช้ และการป้องกันข้อมูลสำคัญ\n"
        "4.2 เกณฑ์ผ่าน: ไม่พบช่องโหว่ระดับสูงที่ยังไม่แก้ไขก่อนขึ้นใช้งานจริง\n"
        "\n"
        "5. การทดสอบยอมรับโดยผู้ใช้\n"
        "5.1 จัดให้ผู้แทนผู้ว่าจ้างทดสอบตามกรณีใช้งานจริง\n"
        "5.2 เกณฑ์ผ่าน: ผู้ว่าจ้างลงนามยอมรับผลงานตามเกณฑ์ที่ตกลง\n"
    )
    if note:
        return (
            f"{body}\n"
            "หมายเหตุตามความคิดเห็นผู้ใช้: จัดลำดับเลขเป็นรูปแบบ 1. / 1.1 / 1.2 "
            f"และปรับรายละเอียดให้สอดคล้องคำสั่ง — {note[:500]}"
        )
    return body


def scope_subsection_fallback_draft(
    sub_key: str | None,
    title: str = "",
    user_feedback: str = "",
) -> str:
    """Deterministic outline for any scope subsection when LLM output is unusable."""
    key = _norm_scope_key(sub_key)
    if key == "testing":
        return testing_fallback_draft(user_feedback)
    if key == "licenses":
        note = (user_feedback or "").strip()
        table = (
            "| ลำดับ | รายการ | จำนวนสิทธิ์ | ราคาต่อหน่วย (บาท) | ราคารวม (บาท) | "
            "ใช้เกณฑ์กลาง ICT | กรณีไม่ใช้เกณฑ์กลางให้ระบุเหตุผล |\n"
            "| --- | --- | --- | --- | --- | --- | --- |\n"
            "| 1 | (ระบุรายการจากเอกสารต้นทาง) | | | | ใช้ | |\n"
            "| รวม | | | | | | |"
        )
        if note:
            return f"{table}\n\nหมายเหตุตามความคิดเห็นผู้ใช้: {note[:500]}"
        return table
    label = (title or key or "หัวข้อย่อย").strip()
    note = (user_feedback or "").strip()
    body = (
        f"1. {label}\n"
        f"1.1 ระบุสาระหลักของหัวข้อ «{label}» จากเอกสารขั้นที่ ๐ ให้ตรวจรับได้\n"
        f"1.2 ระบุเงื่อนไขหรือผลลัพธ์ที่ต้องส่งมอบภายใต้หัวข้อนี้\n"
        f"\n"
        f"2. รายละเอียดดำเนินงาน\n"
        f"2.1 แจกแจงข้อย่อยตามข้อเท็จจริงที่มี โดยไม่ดึงหัวข้ออื่นมาปน\n"
        f"2.2 หากเอกสารต้นทางไม่มีรายละเอียด ให้ระบุเฉพาะส่วนที่ยืนยันได้\n"
    )
    if note:
        return (
            f"{body}\n"
            "หมายเหตุตามความคิดเห็นผู้ใช้: จัดลำดับเป็น 1. / 1.1 / 1.2 "
            f"และปรับตามคำสั่ง — {note[:500]}"
        )
    return body


def polish_scope_subsection_draft(text: str, sub_key: str | None = None) -> str:
    """Post-process one scope subsection after the LLM returns."""
    key = _norm_scope_key(sub_key)
    # Normalize license tables before stripping outline numbers — TSV rows start
    # with 1/2/3 which would otherwise be eaten as heading numbers.
    if key == "licenses" or _looks_like_license_table(text or ""):
        polished = normalize_license_ict_table(text or "")
        polished = sanitize_unauthorized_english(polished)
        polished = sanitize_scope_draft_tables(polished)
        if key and is_scope_content_wrong_owner(key, polished):
            return ""
        return polished.strip()
    polished = sanitize_unauthorized_english(text or "")
    # Keep 1. / 1.1 outlines for every scope sub; only strip leaked chapter-8 nums.
    polished = strip_source_chapter_eight_numbers(polished)
    if key and is_scope_content_wrong_owner(key, polished):
        return ""
    polished = sanitize_scope_draft_tables(polished)
    return polished.strip()


def scope_sub_ownership_block(sub_key: str, title: str) -> str:
    """Hard ownership rules so each heading keeps only its own substance."""
    key = _norm_scope_key(sub_key)
    common = (
        f"=== เจ้าของสาระของหัวข้อ «{title}» ===\n"
        "ก่อนร่าง จำแนกประโยคจากเอกสารขั้นที่ ๐ ว่าเป็นของหัวข้อนี้จริงหรือไม่\n"
        "คัดเฉพาะสาระที่ตรงหัวข้อนี้ ห้ามคัดลอกทั้งก้อนจากหัวข้ออื่น\n"
        "ถ้าต้องใส่ลำดับข้อ ให้ใช้รูปแบบ 1. / 1.1 / 1.2 เท่านั้น "
        "ห้ามพิมพ์เลขหมวดต้นทาง เช่น ๘.๑ ๘.๑.๑ 8.1 4.2\n"
        "ห้ามพิมพ์ [Table 1] หรือป้าย Table เป็นเนื้อหา\n"
    )
    if key == "testing":
        return (
            common
            + "หัวข้อนี้มีเฉพาะแผนการทดสอบ ประเภทการทดสอบ "
            "(หน้าที่ การเชื่อมโยง ประสิทธิภาพ ความมั่นคงปลอดภัย การยอมรับโดยผู้ใช้) "
            "ขั้นตอน เกณฑ์ผ่าน/ไม่ผ่าน และหลักฐานการตรวจรับ\n"
            "ห้ามใส่ขอบเขตและวิธีการดำเนินงาน ข้อกำหนดทั่วไป การบันทึกข้อมูล "
            "การประมวลผล การให้บริการ หรือการบริหารจัดการแบ็กเอนด์ "
            "— สาระเหล่านั้นอยู่ที่หัวข้อหน้าที่การทำงาน/ภาพรวมระบบ\n"
            "ถ้าเอกสารต้นทางไม่มีแผนทดสอบ ให้เขียนเฉพาะเกณฑ์การยอมรับสั้น ๆ จากข้อเท็จจริงที่มี "
            "ห้ามยกทั้งหมวด ๘ มาวาง\n"
        )
    if key == "functional":
        return (
            common
            + "หัวข้อนี้เป็นเจ้าของขอบเขตและวิธีการดำเนินงาน ข้อกำหนดทั่วไป "
            "การบันทึก/นำเข้า การประมวลผล การให้บริการ และการบริหารจัดการระบบ\n"
            "เรียบเรียงเป็นข้อย่อยด้วยย่อหน้าหรือรายการสั้น ห้ามใส่เลข ๘.๑ / 8.1\n"
            "ห้ามใส่แผนทดสอบหรือเกณฑ์ยอมรับแบบละเอียด — อยู่ที่หัวข้อการทดสอบ\n"
        )
    if key == "licenses":
        return (
            common
            + "หัวข้อนี้เป็นตารางครุภัณฑ์/ลิขสิทธิ์ซอฟต์แวร์เท่านั้น\n"
            "ผลลัพธ์ต้องเป็นตารางมาร์กดาวน์ที่ใช้เครื่องหมาย | คั่นคอลัมน์เท่านั้น "
            "ห้ามใช้แท็บ ช่องว่างจัดคอลัมน์ หรือตารางแบบข้อความธรรมดา\n"
            "ถ้าเอกสารมีตารางเกณฑ์กลาง ICT ให้คัดลอกแถวข้อมูลครบ "
            "ใช้ตารางมาร์กดาวน์คอลัมน์เดียวชุดนี้เท่านั้น:\n"
            f"{LICENSE_ICT_TABLE_TEMPLATE}\n"
            "คอลัมน์ «ใช้เกณฑ์กลาง ICT» ใส่คำว่า ใช้ หรือ ไม่ใช้ อย่างใดอย่างหนึ่ง "
            "ห้ามแยกเป็นสองคอลัมน์ «ใช้|ไม่ใช้» และห้ามซ้ำแถวหัวตาราง\n"
            "ห้ามใส่รายละเอียดฟังก์ชันระบบหรือแผนทดสอบในหัวข้อนี้\n"
        )
    if key == "system_overview":
        return (
            common
            + "หัวข้อนี้สรุปภาพรวม สถาปัตยกรรม สภาพแวดล้อม ผู้ใช้และปริมาณข้อมูล\n"
            "ห้ามแจกแจงฟังก์ชันทีละข้อยาว ๆ และห้ามใส่ตารางลิขสิทธิ์\n"
        )
    return (
        common
        + "เขียนเฉพาะสาระของหัวข้อนี้จากเอกสารต้นทาง ไม่ดึงหัวข้อข้างเคียงมาปน\n"
    )


_STORAGE_TO_STYLE_SEMANTIC = {
    "s1": "background",
    "s2": "objective",
    "s3": "qualification",
    "s4": "scope",
    "s5": "schedule",
    "s6": "budget",
    "s7": "location",
    "s8": "payment",
    "s9": "warranty",
    "s10": "penalty",
    "s11": "evaluation",
    "s13": "other_conditions",
    "s15": "ip_ownership",
    "s16": "confidentiality",
    "s17": "responsible_unit",
}


def _append_if_matches(
    section_key: str | None, keys: set[str | None], lines: list[str], *chunks: str
) -> None:
    if section_key not in keys:
        return
    lines.extend(chunks)


def _append_scope_hints(section_key: str | None, profile, lines: list[str]) -> None:
    if section_key not in {None, "s4", "scope"}:
        return
    from app.domain.tor_taxonomy import hint_for

    for item in profile.scope_subsections:
        extra = hint_for(item.semantic_key)
        if extra:
            lines.append(f"- {item.title}: {extra}")
    lines.append("หมวดขอบเขตใช้ชื่อหัวข้อย่อยตามโปรไฟล์เท่านั้น ห้ามสร้างหัวข้อนอกโปรไฟล์")
    lines.append(f"ตารางรายการ: {TABLE_FORMAT_HINT}")


def _append_qualification_hints(section_key: str | None, cat: str, lines: list[str]) -> None:
    if section_key not in {None, "s3", "qualification"}:
        return
    from app.domain.tor_taxonomy import QUALIFICATION_HINTS, qualification_subsections

    for key in qualification_subsections(cat):
        extra = QUALIFICATION_HINTS.get(key, "")
        if extra:
            lines.append(f"- {extra}")
    lines.append(f"ตารางบุคลากรเมื่อโปรไฟล์มี:\n{PERSONNEL_TABLE_TEMPLATE}")


def official_tor_style_block(
    category: str | None = None, section_key: str | None = None
) -> str:
    """Shared official-TOR style rules for agents and chat drafting."""
    from app.domain.section_profile import profile_for_project
    from app.domain.tor_taxonomy import CANONICAL_PHRASES, CONTRACTOR_TERM, OWNER_TERM, hint_for

    profile = profile_for_project(category)
    cat = profile.category
    contractor = CONTRACTOR_TERM.get(cat, "ผู้รับจ้าง")
    owner = OWNER_TERM.get(cat, "ผู้ว่าจ้าง")
    lines = [
        SECTION_OWNERSHIP_TABLE.rstrip(),
        f"รูปแบบราชการ ประเภทงาน {profile.label}: เรียกคู่สัญญาว่า «{contractor}» "
        f"เรียกหน่วยงานว่า «{owner}» ห้ามสลับคำเรียก",
        "ห้ามพิมพ์เลขหมวดนำหน้าชื่อหัวข้อ (ทั้งเลขไทยและอารบิก) "
        "ระบบส่งออกเป็นผู้ใส่ชื่อหัวข้อตามโปรไฟล์ "
        "ห้ามพิมพ์ป้ายช่องข้อมูล รหัสอังกฤษ หรือ hint เป็นหัวข้อ "
        "(ห้าม ประวัติ/สถานการณ์ปัจจุบันของระบบเดิม, ปัญหาที่พบ (ระบุตัวเลข/สถิติ), ### history)",
        "ห้ามคำอังกฤษ เช่น Server, Cyber Attack, Digital Government, Big Data, "
        "Public AI, Deliverables, UAT, SIT, Dashboard",
        "ห้ามมาร์กดาวน์หนาเป็นป้ายฟิลด์ เช่น **ชื่อ:**",
        "สำนวนที่ใช้: นับถัดจากวันลงนามในสัญญา ; หรือเทียบเท่า ; "
        "จำนวนเงินเป็นตัวเลขแล้วตามด้วยตัวอักษรในวงเล็บ",
        "ตัวเลขในเนื้อหา วันที่ และตารางใช้เลขไทยได้",
    ]
    semantic = _STORAGE_TO_STYLE_SEMANTIC.get(section_key or "", section_key)
    section_hint = hint_for(semantic or "") if semantic else ""
    if section_hint:
        lines.append(f"แนวทางหมวดนี้: {section_hint}")
    _append_scope_hints(section_key, profile, lines)
    _append_qualification_hints(section_key, cat, lines)
    _append_if_matches(
        section_key,
        {None, "s1", "background"},
        lines,
        "หมวดความเป็นมาเขียนเล่าเรื่องต่อเนื่องไม่มีหัวข้อย่อย "
        "ปิดท้ายด้วย «จึงมีความจำเป็นต้อง…»",
    )
    _append_if_matches(
        section_key,
        {None, "s2", "objectives"},
        lines,
        "หมวดวัตถุประสงค์ต้องครบสามส่วนใน JSON: "
        "mainObj (ข้อ «เพื่อ…»), users (กลุ่มผู้ใช้เป้าหมาย), "
        "kpi (ตัวชี้วัดที่วัดได้) — ห้ามปล่อย users หรือ kpi ว่างถ้าเอกสารมี",
    )
    _append_if_matches(
        section_key,
        {None, "s5", "schedule"},
        lines,
        f"ตารางระยะเวลาบังคับ:\n{TIMELINE_TABLE_TEMPLATE}",
        f"ถ้อยคำมาตรฐาน: {CANONICAL_PHRASES['duration_start']}",
    )
    _append_if_matches(
        section_key,
        {None, "s8", "payment"},
        lines,
        f"ตารางงวดจ่ายบังคับ:\n{PAYMENT_TABLE_TEMPLATE}",
        f"ถ้อยคำมาตรฐาน: {CANONICAL_PHRASES['acceptance']}",
    )
    _append_if_matches(
        section_key,
        {None, "s11", "evaluation"},
        lines,
        f"ตารางเกณฑ์คัดเลือกบังคับ:\n{EVALUATION_TABLE_TEMPLATE}",
    )
    lines.extend(
        f"ใช้ถ้อยคำนี้ตรงตามตัวอักษรห้ามดัดแปลง: {phrase}"
        for phrase in (
            CANONICAL_PHRASES.get("duration_start"),
            CANONICAL_PHRASES.get("or_better"),
            CANONICAL_PHRASES.get("no_extra_cost"),
        )
        if phrase
    )
    return "\n".join(lines) + "\n"


def scope_overview_from_subs(subs: dict[str, str], category: str | None = None) -> str:
    """Short top-level s4 text — details live in profile subsections."""
    profile = profile_for_project(category)
    lead = ""
    for item in profile.scope_subsections:
        lead = str(subs.get(item.storage_key) or subs.get(item.semantic_key) or "").strip()
        if lead:
            break
    if not lead:
        for value in subs.values():
            lead = str(value or "").strip()
            if lead:
                break
    if not lead:
        return ""
    if len(lead) > 360:
        lead = lead[:360].rstrip() + "…"
    return f"{lead}\n\n(รายละเอียดอยู่ในหัวข้อย่อยขอบเขตของงานตามประเภทโครงการ)"


def merge_scope_from_subs(subs: dict[str, str], category: str | None = None) -> str:
    profile = profile_for_project(category)
    parts: list[str] = []
    for item in profile.scope_subsections:
        text = str(subs.get(item.storage_key) or subs.get(item.semantic_key) or "").strip()
        if not text:
            continue
        parts.append(f"{item.title}\n{text}")
    for extra in extra_legacy_scope_items(subs, category):
        parts.append(f"{extra['title']}\n{extra['content']}")
    return "\n\n".join(parts)


def scope_sub_prompt(
    sub_key: str,
    slot_map: dict[str, Any],
    rag_context: str = "",
    category: str | None = None,
    *,
    current_draft: str | None = None,
    user_feedback: str | None = None,
) -> str:
    title = subsection_title(sub_key, category, sub_key)
    from app.services.intake_service import slot_content

    facts = slot_content(slot_map, sub_key).strip()
    parent = slot_content(slot_map, "s4").strip()
    key = _norm_scope_key(sub_key)
    feedback = (user_feedback or "").strip()
    prior = (current_draft or "").strip()
    # When revising, keep the slot facts as intake-only if the slot was overwritten
    # with editor draft+instruction mash — prefer explicit current_draft.
    if prior and feedback and facts.startswith("ร่างใหม่เฉพาะ"):
        facts = ""
    parts = [
        f"{'แก้ไข' if feedback else 'ร่าง'}หัวข้อย่อย «{title}» ของหมวดขอบเขตของงาน",
        "",
        "คิดก่อนเขียน: คัดเฉพาะประโยคที่เป็นของหัวข้อนี้จากเอกสารต้นทาง "
        "ถ้าประโยคอยู่ในหัวข้ออื่นของเอกสารต้นทาง ให้ข้าม — ห้ามยกทั้งหมวดมาวาง",
        "แก้เฉพาะหัวข้อย่อยนี้เท่านั้น ห้ามแก้หรือกล่าวถึงหัวข้อย่อยอื่น",
        "",
        THAI_ONLY_RULES,
        official_tor_style_block(category, "s4"),
        scope_sub_ownership_block(sub_key, title),
    ]
    intake = slot_content(slot_map, "_project_intake").strip()
    if prior:
        parts.append(f"=== ร่างปัจจุบันของหัวข้อนี้ที่ต้องปรับปรุง ===\n{prior[:12000]}")
    if feedback:
        parts.append(
            "=== ความคิดเห็นจากผู้ใช้ (ต้องปฏิบัติตามอย่างเคร่งครัด) ===\n"
            f"{feedback[:4000]}\n"
            "ร่างข้อความใหม่ทั้งก้อนของหัวข้อนี้ให้สอดคล้องความคิดเห็น "
            "คงสาระที่ถูกต้องของร่างเดิมไว้ และห้ามขยายไปหัวข้ออื่น"
        )
    if facts and facts != prior:
        parts.append(f"ข้อมูลจากขั้นวิเคราะห์สำหรับหัวข้อนี้:\n{facts[:10000]}")
    elif not prior and intake:
        parts.append(
            "เอกสารขั้นที่ ๐ (คัดเฉพาะที่ยืนยันว่าเป็นสาระของหัวข้อนี้เท่านั้น "
            "ห้ามคัดลอกหัวข้ออื่น):\n"
            + intake[:3500]
        )
    elif not prior and parent:
        parts.append(f"ข้อมูลขอบเขตงานรวม (คัดเฉพาะส่วนที่เกี่ยวกับ «{title}»):\n{parent[:4000]}")
    if rag_context:
        parts.append(f"บริบทกฎหมาย:\n{rag_context[:3000]}")
    from app.domain.tor_draft_hints import hint_for

    hint = hint_for(sub_key, category)
    if hint:
        parts.append(f"แนวทางความครบถ้วนจากตัวอย่าง TOR: {hint}")
    if key == "licenses":
        parts.append(
            "ผลลัพธ์ต้องมีตารางมาร์กดาวน์ตามแม่แบบด้านบน "
            "มีแถวข้อมูลจริงจากเอกสาร และแถวรวมถ้าเอกสารมี"
        )
    if key == "testing":
        parts.append(
            "ผลลัพธ์สั้น ชัด วัดผลได้ เป็นรายการประเภทการทดสอบและเกณฑ์ผ่าน "
            "ความยาวไม่เกินประมาณหนึ่งหน้า ไม่ใช่คัดลอกข้อกำหนดระบบทั้งหมวด"
        )
    parts.append(SCOPE_SUB_SUBSTANCE_RULES)
    parts.append(
        "เขียนเนื้อหาหัวข้อย่อยนี้เป็นภาษาไทยเท่านั้น "
        "ให้ครบสาระตามข้อมูลที่มี ไม่เติมน้ำ ไม่ซ้ำหมวดอื่น "
        "ไม่ต้องใส่ชื่อหัวข้อย่อยซ้ำ ห้ามพิมพ์รหัสหัวข้อย่อยหรือป้ายช่องข้อมูลเป็นหัวข้อ"
    )
    return "\n".join(parts)


_PIPE_ROW = re.compile(r"^\|.+\|$")
_SEP_ROW = re.compile(r"^\|[\s\-:|]+\|$")


def _is_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    return bool(
        _PIPE_ROW.match(lines[index].strip())
        and _SEP_ROW.match(lines[index + 1].strip())
    )


def _consume_table(
    lines: list[str], start: int
) -> tuple[list[list[str]] | None, int]:
    if not _is_table_start(lines, start):
        return None, start
    rows: list[list[str]] = []
    i = start
    while i < len(lines) and _PIPE_ROW.match(lines[i].strip()):
        raw = lines[i].strip()
        if _SEP_ROW.match(raw):
            i += 1
            continue
        cells = [c.strip() for c in raw.strip("|").split("|")]
        rows.append(cells)
        i += 1
    return rows, i


def split_content_blocks(text: str) -> list[tuple[str, list[list[str]] | str]]:
    """Split prose into ('para', text) or ('table', rows) blocks for exporters/UI."""
    lines = text.replace("\r\n", "\n").split("\n")
    blocks: list[tuple[str, list[list[str]] | str]] = []
    i = 0
    para_buf: list[str] = []

    def flush_para() -> None:
        nonlocal para_buf
        body = "\n".join(para_buf).strip()
        if body:
            blocks.append(("para", body))
        para_buf = []

    while i < len(lines):
        rows, next_i = _consume_table(lines, i)
        if rows is not None:
            flush_para()
            if rows:
                blocks.append(("table", rows))
            i = next_i
            continue
        para_buf.append(lines[i].rstrip())
        i += 1
    flush_para()
    return blocks
