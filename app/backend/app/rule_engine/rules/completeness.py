"""Completeness validation rules for TOR documents.

Uses Section_Profile of the project's procurement category.
"""

from __future__ import annotations

import re

from app.domain.section_profile import MissingSectionProfile, profile_for_project, require_profile
from app.domain.tor_sections import CRITICAL_SECTIONS_MIN_LENGTH, MINIMUM_CONTENT_LENGTH
from app.rule_engine.engine import KIND_RISK, Finding, Severity
from app.rule_engine.rules.base import BaseRule, focus_section

_BLANK_PATTERN = re.compile(r"\[(?=[^\]]{0,80}ระบุ)[^\]]{0,80}\]")
_SCOPE_ADMISSIONS = (
    "ไม่มีรายละเอียดเชิงฟังก์ชัน",
    "เนื่องจากข้อมูลเจ้าของสาระ",
)
_MAX_DETAIL_FINDINGS = 8

TOR_REQUIRED_SECTIONS: dict[str, str] = {
    item.storage_key: item.title
    for item in profile_for_project("buy_goods").main_sections
    if item.required
}


class MissingSectionsHalt(Exception):
    def __init__(
        self, missing_sections: dict[str, str], findings: list[Finding]
    ) -> None:
        self.missing_sections = missing_sections
        self.findings = findings
        super().__init__(
            f"Missing required sections: {', '.join(missing_sections.keys())}"
        )


def _category(tor_document: dict) -> str | None:
    return str(tor_document.get("project_type") or tor_document.get("procurement_category") or "")


def _sections(tor_document: dict) -> dict:
    return tor_document.get("sections", tor_document)


def _profile_missing_halt(exc: MissingSectionProfile) -> MissingSectionsHalt:
    return MissingSectionsHalt(
        missing_sections={"profile": str(exc)},
        findings=[
            Finding(
                severity=Severity.ERROR,
                rule_violated="COMPLETENESS_PROFILE_MISSING",
                affected_section="profile",
                message=str(exc),
                recommended_correction="เลือกหมวดใหญ่ประเภทการจัดซื้อจัดจ้างที่มี Section_Profile",
            )
        ],
    )


def _s4_has_body(sections: dict, profile: object) -> bool:
    nested = sections.get("s4")
    if isinstance(nested, dict) and any(str(value or "").strip() for value in nested.values()):
        return True
    for sub in getattr(profile, "scope_subsections", ()):
        if str(sections.get(sub.storage_key) or "").strip():
            return True
    return False


def _section_content_empty(sections: dict, profile: object, item: object) -> bool:
    storage_key = item.storage_key
    content = sections.get(storage_key)
    empty = content is None or (isinstance(content, str) and content.strip() == "")
    if storage_key == "s4" and empty:
        return not _s4_has_body(sections, profile)
    return empty


def _missing_section_finding(item: object) -> Finding:
    return Finding(
        severity=Severity.ERROR,
        rule_violated="COMPLETENESS_SECTION_MISSING",
        affected_section=item.storage_key,
        message=f"ไม่พบหัวข้อที่จำเป็น: {item.title}",
        recommended_correction=f"กรุณาเพิ่มเนื้อหาในหัวข้อ {item.title}",
    )


class SectionPresenceRule(BaseRule):
    def validate(self, tor_document: dict) -> list[Finding]:
        findings: list[Finding] = []
        missing: dict[str, str] = {}
        try:
            profile = require_profile(_category(tor_document) or "buy_goods")
        except MissingSectionProfile as exc:
            raise _profile_missing_halt(exc) from exc

        sections = _sections(tor_document)
        focus = focus_section(tor_document)
        for item in profile.main_sections:
            if not item.required or (focus and item.storage_key != focus):
                continue
            if not _section_content_empty(sections, profile, item):
                continue
            missing[item.storage_key] = item.title
            findings.append(_missing_section_finding(item))
        if missing:
            raise MissingSectionsHalt(missing_sections=missing, findings=findings)
        return findings


class RequiredSubsectionsRule(BaseRule):
    def validate(self, tor_document: dict) -> list[Finding]:
        findings: list[Finding] = []
        if focus_section(tor_document) not in {None, "s4"}:
            return findings
        profile = profile_for_project(_category(tor_document) or "buy_goods")
        sections = _sections(tor_document)
        s4_content = sections.get("s4")
        required = [item for item in profile.scope_subsections if item.required]
        for item in required:
            candidates = (
                item.storage_key,
                item.semantic_key,
                f"s4.{item.storage_key}",
            )
            has_subsection = any(str(sections.get(key) or "").strip() for key in candidates)
            if not has_subsection and isinstance(s4_content, dict):
                has_subsection = any(
                    str(s4_content.get(key) or "").strip() for key in candidates
                )
            if not has_subsection:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        rule_violated="COMPLETENESS_SUBSECTION_MISSING",
                        affected_section="s4",
                        message=f"ไม่พบหัวข้อย่อยที่จำเป็นในขอบเขตของงาน: {item.title}",
                        recommended_correction=f"กรุณาเพิ่มหัวข้อย่อย {item.title} ในขอบเขตของงาน",
                    )
                )
        return findings


class MinimumContentRule(BaseRule):
    def validate(self, tor_document: dict) -> list[Finding]:
        findings: list[Finding] = []
        profile = profile_for_project(_category(tor_document) or "buy_goods")
        sections = _sections(tor_document)
        focus = focus_section(tor_document)
        for item in profile.main_sections:
            if focus and item.storage_key != focus:
                continue
            content = sections.get(item.storage_key)
            if content is None:
                continue
            if isinstance(content, dict):
                text = " ".join(str(v) for v in content.values() if v is not None)
            else:
                text = str(content)
            text = text.strip()
            min_length = CRITICAL_SECTIONS_MIN_LENGTH.get(
                item.storage_key, MINIMUM_CONTENT_LENGTH
            )
            if len(text) < min_length:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        rule_violated="COMPLETENESS_CONTENT_TOO_SHORT",
                        affected_section=item.storage_key,
                        message=(
                            f"เนื้อหาในหัวข้อ {item.title} สั้นเกินไป "
                            f"(ความยาว {len(text)} อักขระ, ขั้นต่ำ {min_length} อักขระ)"
                        ),
                        recommended_correction=(
                            f"กรุณาเพิ่มรายละเอียดในหัวข้อ {item.title} "
                            f"ให้มีความยาวอย่างน้อย {min_length} อักขระ"
                        ),
                    )
                )
        return findings


def _append_payment_finding(findings: list[Finding], sections: dict, focus: str | None) -> None:
    payment = str(sections.get("s8") or "")
    if focus not in {None, "s8"} or not payment.strip():
        return
    if "งวดที่" in payment and "ร้อยละ" in payment:
        return
    findings.append(
        Finding(
            severity=Severity.WARNING,
            rule_violated="COMPLETENESS_PAYMENT_TABLE",
            affected_section="s8",
            message="หมวดงวดจ่ายต้องมีตารางงวดที่และร้อยละรวมหนึ่งร้อย",
            recommended_correction="ใส่ตารางงวดที่ / ผลงานส่งมอบ / ร้อยละ ของวงเงิน",
        )
    )


def _needs_weight_table(evaluation: str) -> bool:
    """Weight tables apply to quality-price scoring, not pass/fail then price."""
    text = evaluation.strip()
    if not text:
        return False
    if "ร้อยละ" in text or "น้ำหนัก" in text:
        return False
    quality_price = any(
        token in text
        for token in ("ราคาประกอบคุณภาพ", "เกณฑ์คุณภาพ", "คะแนนคุณภาพ")
    )
    if not quality_price:
        return False
    return "ผ่านหรือไม่ผ่าน" not in text


def _append_evaluation_finding(findings: list[Finding], sections: dict, focus: str | None) -> None:
    evaluation = str(sections.get("s11") or "")
    if focus not in {None, "s11"} or not _needs_weight_table(evaluation):
        return
    findings.append(
        Finding(
            severity=Severity.WARNING,
            rule_violated="COMPLETENESS_EVAL_WEIGHT_TABLE",
            affected_section="s11",
            message="เกณฑ์คุณภาพต้องระบุสัดส่วนน้ำหนักหรือร้อยละ",
            recommended_correction="ใส่ตารางน้ำหนักคะแนนคุณภาพและราคา",
        )
    )


def _personnel_table_missing(qualifications: str) -> bool:
    if not qualifications.strip():
        return False
    lowered = qualifications.lower()
    return (
        "บุคลากร" not in qualifications
        and "man" not in lowered
        and "อัตรากำลัง" not in qualifications
    )


def _append_personnel_finding(
    findings: list[Finding],
    sections: dict,
    focus: str | None,
    category: str,
) -> None:
    qualifications = str(sections.get("s3") or "")
    if focus not in {None, "s3"} or category != "hire_develop":
        return
    if not _personnel_table_missing(qualifications):
        return
    findings.append(
        Finding(
            severity=Severity.WARNING,
            rule_violated="COMPLETENESS_PERSONNEL_TABLE",
            affected_section="s3",
            message="งานจ้างพัฒนาควรระบุตารางบุคลากรหรือปริมาณงาน",
            recommended_correction="เพิ่มตำแหน่ง วุฒิ และปริมาณงานของทีมงาน",
        )
    )


def _soc_table_missing(soc: str) -> bool:
    if not soc.strip():
        return True
    return "เปรียบเทียบ" not in soc and "ข้อกำหนด" not in soc


def _append_soc_finding(
    findings: list[Finding],
    sections: dict,
    focus: str | None,
    category: str,
) -> None:
    soc = str(sections.get("s12") or "")
    if focus not in {None, "s12"} or category != "hire_maintain" or not _soc_table_missing(soc):
        return
    findings.append(
        Finding(
            severity=Severity.WARNING,
            rule_violated="COMPLETENESS_SOC_TABLE",
            affected_section="s12",
            message="งานบำรุงรักษาต้องมีเงื่อนไขการยื่นข้อเสนอหรือตารางเปรียบเทียบข้อกำหนด",
            recommended_correction="เพิ่มตารางเปรียบเทียบข้อกำหนดเป็นข้อหลัก",
        )
    )


class RequiredTablesRule(BaseRule):
    """Gold tables: payment %, evaluation weights, personnel, and SoC when the type needs them."""

    def validate(self, tor_document: dict) -> list[Finding]:
        findings: list[Finding] = []
        category = _category(tor_document) or "buy_goods"
        sections = _sections(tor_document)
        focus = focus_section(tor_document)
        _append_payment_finding(findings, sections, focus)
        _append_evaluation_finding(findings, sections, focus)
        _append_personnel_finding(findings, sections, focus, category)
        _append_soc_finding(findings, sections, focus, category)
        return findings


def _is_section_key(key: str) -> bool:
    return key.startswith("s") and len(key) > 1 and key[1].isdigit()


def _section_in_focus(key: str, focus: str | None) -> bool:
    if focus is None:
        return True
    return key == focus or key.startswith(f"{focus}.")


def _section_texts(tor_document: dict) -> list[tuple[str, str]]:
    sections = _sections(tor_document)
    focus = focus_section(tor_document)
    rows: list[tuple[str, str]] = []
    for key, value in sections.items():
        if not isinstance(key, str) or not _is_section_key(key):
            continue
        if not _section_in_focus(key, focus):
            continue
        if isinstance(value, dict):
            text = " ".join(str(item) for item in value.values() if item is not None)
        else:
            text = str(value or "")
        if text.strip():
            rows.append((key, text))
    return rows


def _blank_samples(text: str) -> list[str]:
    return [match.group(0) for match in _BLANK_PATTERN.finditer(text)]


def _blank_finding(section_key: str, samples: list[str]) -> Finding:
    shown = ", ".join(samples[:4])
    return Finding(
        severity=Severity.WARNING,
        rule_violated="COMPLETENESS_UNFILLED_BLANK",
        affected_section=section_key,
        message=f"หัวข้อ {section_key} ยังเว้นช่องที่ต้องกรอกค่าจริง: {shown}",
        recommended_correction="แทนที่ช่องในวงเล็บเหลี่ยมด้วยจำนวน สถานที่ หรือเงื่อนไขที่ใช้ในสัญญาได้",
        finding_kind=KIND_RISK,
        risk_type="content",
        excerpt=samples[0][:180],
    )


def _is_table_separator(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    return bool(cells) and all(set(cell) <= set("-: ") and "-" in cell for cell in cells if cell)


def _table_lacks_substance(rows: list[str]) -> bool:
    if not rows:
        return True
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        for cell in cells:
            if cell in {"", "รวม", "-", "—"}:
                continue
            if any(char.isdigit() for char in cell) or len(cell) >= 4:
                return False
    return True


def _has_empty_table(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if not line.startswith("|") or not _is_table_separator(line) or index == 0:
            continue
        if not lines[index - 1].startswith("|"):
            continue
        rows: list[str] = []
        cursor = index + 1
        while cursor < len(lines) and lines[cursor].startswith("|"):
            rows.append(lines[cursor])
            cursor += 1
        if _table_lacks_substance(rows):
            return True
    return False


def _empty_table_finding(section_key: str) -> Finding:
    return Finding(
        severity=Severity.WARNING,
        rule_violated="COMPLETENESS_EMPTY_TABLE",
        affected_section=section_key,
        message=f"หัวข้อ {section_key} มีตารางที่ยังไม่มีรายการหรือตัวเลข",
        recommended_correction="เติมรายการ จำนวน และราคาในตารางให้ครบก่อนใช้เป็นขอบเขตงาน",
        finding_kind=KIND_RISK,
        risk_type="content",
    )


def _admission_phrase(text: str) -> str:
    for phrase in _SCOPE_ADMISSIONS:
        if phrase in text:
            return phrase
    return ""


def _admission_finding(section_key: str, phrase: str) -> Finding:
    return Finding(
        severity=Severity.WARNING,
        rule_violated="COMPLETENESS_SCOPE_UNWRITTEN",
        affected_section=section_key,
        message=(
            f"หัวข้อ {section_key} ยังไม่ได้เขียนขอบเขตงาน "
            f"ข้อความระบุว่า{phrase}"
        ),
        recommended_correction="เขียนฟังก์ชัน ปริมาณงาน และผลส่งมอบที่ตรวจรับได้แทนคำอธิบายว่ายังไม่มีรายละเอียด",
        finding_kind=KIND_RISK,
        risk_type="content",
        excerpt=phrase,
    )


class UnfilledDetailRule(BaseRule):
    """Flag blanks, empty tables, and scope text that admits it was not written."""

    def validate(self, tor_document: dict) -> list[Finding]:
        findings: list[Finding] = []
        for section_key, text in _section_texts(tor_document):
            if len(findings) >= _MAX_DETAIL_FINDINGS:
                break
            samples = _blank_samples(text)
            if samples:
                findings.append(_blank_finding(section_key, samples))
                continue
            phrase = _admission_phrase(text)
            if phrase:
                findings.append(_admission_finding(section_key, phrase))
                continue
            if _has_empty_table(text):
                findings.append(_empty_table_finding(section_key))
        return findings
