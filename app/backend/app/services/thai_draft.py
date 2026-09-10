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

PERSONNEL_TABLE_TEMPLATE = (
    "| ตำแหน่ง | คุณวุฒิ | ประสบการณ์ | จำนวน | ระยะเวลา (เดือน) |\n"
    "| --- | --- | --- | --- | --- |\n"
    "| … | … | ไม่น้อยกว่า … ปี | … | … |"
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
) -> str:
    title = subsection_title(sub_key, category, sub_key)
    from app.services.intake_service import slot_content

    facts = slot_content(slot_map, sub_key).strip()
    parent = slot_content(slot_map, "s4").strip()
    parts = [
        f"ร่างหัวข้อย่อย «{title}» ของหมวดขอบเขตของงาน",
        "",
        THAI_ONLY_RULES,
        official_tor_style_block(category, "s4"),
    ]
    intake = slot_content(slot_map, "_project_intake").strip()
    if intake:
        parts.append(
            "เอกสารขั้นที่ ๐ ของโครงการนี้เท่านั้น (ห้ามใช้เอกสารโครงการอื่น):\n"
            + intake[:4000]
        )
    if facts:
        parts.append(f"ข้อมูลจากขั้นวิเคราะห์:\n{facts[:8000]}")
    if parent and not facts:
        parts.append(f"ข้อมูลขอบเขตงานรวม:\n{parent[:6000]}")
    if rag_context:
        parts.append(f"บริบทกฎหมาย:\n{rag_context[:4000]}")
    from app.domain.tor_draft_hints import hint_for

    hint = hint_for(sub_key, category)
    if hint:
        parts.append(f"แนวทางความครบถ้วนจากตัวอย่าง TOR: {hint}")
    parts.append(SCOPE_SUB_SUBSTANCE_RULES)
    parts.append(
        "เขียนเนื้อหาหัวข้อย่อยนี้เป็นภาษาไทยเท่านั้น "
        "ให้ครบสาระตามข้อมูลที่มี ไม่เติมน้ำ ไม่ซ้ำหมวดอื่น "
        "ไม่ต้องใส่เลขหัวข้อซ้ำ ห้ามพิมพ์รหัสหัวข้อย่อยหรือป้ายช่องข้อมูลเป็นหัวข้อ"
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
