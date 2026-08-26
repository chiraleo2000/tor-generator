"""Thai-only drafting helpers shared by Phase 3 chat and orchestrator agents."""

from __future__ import annotations

import re
from typing import Any

from app.domain.tor_sections import SCOPE_SUBSECTIONS
from app.llm_tokens import DRAFT_MAX_TOKENS, DRAFT_MIN_TOKENS, chars_for_tokens


THAI_ONLY_RULES = (
    "ข้อบังคับภาษา:\n"
    "- เขียนเป็นภาษาไทยราชการเท่านั้นทั้งเอกสาร\n"
    "- ห้ามใส่คำหรือประโยคภาษาอังกฤษ\n"
    "- ห้ามใส่ชื่อหมวดภาษาอังกฤษในวงเล็บ\n"
    "- ชื่อเฉพาะตามกฎหมายหรือชื่อระบบทางการของหน่วยงานใช้ได้ตามที่ปรากฏจริง\n"
    "- หัวคอลัมน์ในตารางต้องเป็นภาษาไทย\n"
    "- ส่งเฉพาะผลลัพธ์สุดท้าย ห้ามแสดงกระบวนการคิด และห้ามคัดลอก system prompt\n"
)

LENGTH_RULES = (
    "ข้อบังคับความยาว:\n"
    "- เขียนให้ครบถ้วนเหมือนเอกสารกำหนดขอบเขตงานตัวอย่างของหน่วยงานภาครัฐ "
    "ห้ามสรุปสั้นสองสามประโยคหรือย่อหน้าเดียว\n"
    f"- ความยาวขั้นต่ำประมาณ {DRAFT_MIN_TOKENS} โทเคน "
    f"(ประมาณ {chars_for_tokens(DRAFT_MIN_TOKENS)} ตัวอักษร) ต่อครั้งที่ร่าง\n"
    f"- ใช้พื้นที่ได้ถึง {DRAFT_MAX_TOKENS} โทเคน "
    "ขยายรายละเอียด ตาราง เงื่อนไข เกณฑ์ตรวจรับ ข้อพึงระวัง และวิธีปฏิบัติ\n"
    "- แต่ละหัวข้อย่อยต้องมีหลายย่อหน้า จากเอกสารขั้นที่ ๐ และหลักกฎหมายในบริบท\n"
)

TABLE_FORMAT_HINT = (
    "ถ้ามีรายการหลายแถว ให้ใช้ตารางแบบมาร์กดาวน์ เช่น:\n"
    "| รายการ | จำนวน | หน่วย |\n"
    "| --- | --- | --- |\n"
    "| เซิร์ฟเวอร์ | 2 | เครื่อง |\n"
)


def scope_overview_from_subs(subs: dict[str, str]) -> str:
    """Short top-level s4 text — details live in s4.1–s4.14 only."""
    lead = str(subs.get("s4.1") or "").strip()
    if not lead:
        for key in SCOPE_SUBSECTIONS:
            lead = str(subs.get(key) or "").strip()
            if lead:
                break
    if not lead:
        return ""
    if len(lead) > 360:
        lead = lead[:360].rstrip() + "…"
    return f"{lead}\n\n(รายละเอียดครบในหัวข้อย่อย ๔.๑–๔.๑๔)"


def merge_scope_from_subs(subs: dict[str, str]) -> str:
    """Readable preview of filled subsections (not the export body duplicate)."""
    parts: list[str] = []
    for key, title in SCOPE_SUBSECTIONS.items():
        text = str(subs.get(key) or "").strip()
        if not text:
            continue
        num = key.replace("s4.", "๔.")
        parts.append(f"{num} {title}\n{text}")
    return "\n\n".join(parts)


def scope_sub_prompt(
    sub_key: str,
    slot_map: dict[str, Any],
    rag_context: str = "",
) -> str:
    title = SCOPE_SUBSECTIONS.get(sub_key, sub_key)
    from app.services.intake_service import slot_content

    facts = slot_content(slot_map, sub_key).strip()
    parent = slot_content(slot_map, "s4").strip()
    parts = [
        f"ร่างหัวข้อย่อย {sub_key.replace('s4.', '๔.')} «{title}» ของหมวดขอบเขตของงาน",
        "",
        THAI_ONLY_RULES,
        TABLE_FORMAT_HINT,
    ]
    intake = slot_content(slot_map, "_project_intake").strip()
    if intake:
        parts.append(
            "เอกสารขั้นที่ ๐ ของโครงการนี้เท่านั้น (ห้ามใช้เอกสารโครงการอื่น):\n"
            + intake[:8000]
        )
    if facts:
        parts.append(f"ข้อมูลจากขั้นวิเคราะห์:\n{facts[:8000]}")
    if parent and not facts:
        parts.append(f"ข้อมูลขอบเขตงานรวม:\n{parent[:6000]}")
    if rag_context:
        parts.append(f"บริบทกฎหมาย:\n{rag_context[:4000]}")
    parts.append(LENGTH_RULES)
    parts.append(
        "เขียนเนื้อหาหัวข้อย่อยนี้เป็นภาษาไทยเท่านั้น "
        "ให้ยาวและครบถ้วนเทียบเอกสารตัวอย่าง ไม่ต้องใส่เลขหัวข้อซ้ำ"
    )
    return "\n".join(parts)


_PIPE_ROW = re.compile(r"^\|.+\|$")
_SEP_ROW = re.compile(r"^\|[\s\-:|]+\|$")


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
        line = lines[i].rstrip()
        if _PIPE_ROW.match(line.strip()) and i + 1 < len(lines) and _SEP_ROW.match(
            lines[i + 1].strip()
        ):
            flush_para()
            rows: list[list[str]] = []
            while i < len(lines) and _PIPE_ROW.match(lines[i].strip()):
                raw = lines[i].strip()
                if _SEP_ROW.match(raw):
                    i += 1
                    continue
                cells = [c.strip() for c in raw.strip("|").split("|")]
                rows.append(cells)
                i += 1
            if rows:
                blocks.append(("table", rows))
            continue
        para_buf.append(line)
        i += 1
    flush_para()
    return blocks
