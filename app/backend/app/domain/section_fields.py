"""Structured TOR subsection fields (mirrors frontend SECTION_FIELDS)."""

from __future__ import annotations

import json
import re

# section_key → [(field_key, thai_label), ...]
SECTION_FIELDS: dict[str, list[tuple[str, str]]] = {
    "s1": [
        ("history", "ประวัติ/สถานการณ์ปัจจุบันของระบบเดิม"),
        ("problems", "ปัญหาที่พบ (ระบุตัวเลข/สถิติ)"),
        ("policy", "นโยบาย/กฎหมายที่เกี่ยวข้อง"),
    ],
    "s2": [
        ("mainObj", "วัตถุประสงค์หลัก (ชัดเจน วัดผลได้)"),
        ("users", "กลุ่มผู้ใช้งานเป้าหมาย"),
        ("kpi", "ตัวชี้วัดความสำเร็จ"),
    ],
    "s3": [
        ("general", "คุณสมบัติทั่วไป"),
        ("paidup", "ทุนจดทะเบียน/มูลค่ากิจการขั้นต่ำ"),
        ("experience", "ผลงาน/ประสบการณ์ที่ต้องการ"),
    ],
    "s5": [
        ("timelineRange", "วันเริ่มต้น - วันสิ้นสุด"),
        ("milestones", "งวดงานหลัก"),
    ],
    "s6": [
        ("budgetAmount", "วงเงินงบประมาณ (บาท)"),
        ("budgetSource", "ที่มาของงบประมาณ"),
    ],
    "s7": [("location", "สถานที่ดำเนินการ")],
    "s8": [
        ("installments", "จำนวนงวดการจ่ายเงิน"),
        ("paymentTerms", "เงื่อนไขการเบิกจ่ายแต่ละงวด"),
    ],
    "s9": [("warranty", "ระยะเวลารับประกัน")],
    "s10": [("penalty", "ค่าปรับกรณีระบบขัดข้อง/ล่าช้า")],
    "s11": [
        ("evalMethod", "วิธีการประเมิน"),
        ("evalWeight", "สัดส่วนคะแนน (ถ้ามีเกณฑ์คุณภาพ)"),
    ],
    "s12": [("docs", "รายการเอกสารที่ต้องยื่นประกอบ")],
    "s13": [("other", "เงื่อนไขอื่น ๆ")],
}

_HEADING = re.compile(r"^#{1,3}[ \t]+([^\r\n]+)")
_LINE_PREFIX = re.compile(r"^(?:[#*_]+[\t ]*)?(?:[0-9๐-๙]+[.)][\t ]*)?")


def field_keys(section_key: str) -> list[str]:
    return [item[0] for item in SECTION_FIELDS.get(section_key, [])]


def field_prompt_block(section_key: str) -> str:
    rows = SECTION_FIELDS.get(section_key)
    if not rows:
        return ""
    lines = [
        "ร่างแยกตามหัวข้อย่อยด้านล่าง ขึ้นต้นแต่ละหัวข้อด้วยบรรทัด ### ตามรหัส",
        "ห้ามรวมเป็นก้อนเดียว ห้ามใส่หัวข้ออื่น",
        "แต่ละหัวข้อย่อยต้องมีหลายย่อหน้า เทียบเอกสารกำหนดขอบเขตงานตัวอย่าง ห้ามสรุปสั้น",
    ]
    for key, label in rows:
        lines.append(f"### {key}")
        lines.append(f"({label})")
    return "\n".join(lines)


def _clean_heading(title: str) -> str:
    text = _LINE_PREFIX.sub("", (title or "").strip())
    return text.strip("*#_ ").rstrip(":：").strip()


def _match_heading(title: str, section_key: str) -> str | None:
    rows = SECTION_FIELDS.get(section_key) or []
    trimmed = _clean_heading(title)
    if not trimmed or len(trimmed) > 80:
        return None
    for key, label in rows:
        short = label.split("(", 1)[0].strip()
        if trimmed in {key, label, short}:
            return key
        if trimmed.startswith(key) or trimmed.startswith(label):
            return key
        if len(trimmed) >= 4 and (label.startswith(trimmed) or short.startswith(trimmed)):
            return key
    return None


def _split_labeled_lines(raw: str, section_key: str) -> dict[str, str]:
    current: str | None = None
    buf: list[str] = []
    out: dict[str, str] = {}
    saw_heading = False
    for line in raw.splitlines():
        found = _match_heading(line.strip(), section_key) if line.strip() else None
        if found:
            saw_heading = True
            if current:
                out[current] = "\n".join(buf).strip()
            current = found
            buf = []
            continue
        buf.append(line)
    if current:
        out[current] = "\n".join(buf).strip()
    if not saw_heading:
        return {}
    return {key: value for key, value in out.items() if value}


def parse_section_fields(section_key: str, text: str) -> dict[str, str]:
    """Parse JSON, ### headings, or a prose blob into structured fields (no combined body)."""
    keys = field_keys(section_key)
    first = keys[0] if keys else "body"
    raw = (text or "").strip()
    if not raw:
        return {}

    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            out: dict[str, str] = {}
            for key in keys or parsed.keys():
                value = str(parsed.get(key) or "").strip()
                if value:
                    out[str(key)] = value
            blob = str(parsed.get("body") or "").strip()
            if blob:
                labeled_blob = _split_labeled_lines(blob, section_key)
                if labeled_blob:
                    for key, value in labeled_blob.items():
                        out.setdefault(key, value)
                elif first not in out:
                    out[first] = blob
            if out:
                return out

    headed: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in raw.splitlines():
        match = _HEADING.match(line.strip())
        if match:
            found = _match_heading(match.group(1).strip(), section_key)
            if found:
                if current:
                    headed[current] = "\n".join(buf).strip()
                current = found
                buf = []
                continue
        buf.append(line)
    if current:
        headed[current] = "\n".join(buf).strip()
    headed = {key: value for key, value in headed.items() if value}
    if headed:
        return headed
    labeled = _split_labeled_lines(raw, section_key)
    if labeled:
        return labeled
    paras = [part.strip() for part in re.split(r"\n\s*\n", raw) if part.strip()]
    if keys and len(paras) >= 2:
        out: dict[str, str] = {}
        last = len(keys) - 1
        for index, key in enumerate(keys):
            if index >= len(paras):
                break
            out[key] = "\n\n".join(paras[index:]) if index == last else paras[index]
        return out
    return {first: raw}


def persist_section_fields(section_key: str, text: str) -> str:
    """JSON object of subsection fields, or empty string."""
    fields = parse_section_fields(section_key, text)
    if not fields:
        return ""
    if section_key not in SECTION_FIELDS and len(fields) == 1 and "body" in fields:
        return fields["body"]
    return json.dumps(fields, ensure_ascii=False)
