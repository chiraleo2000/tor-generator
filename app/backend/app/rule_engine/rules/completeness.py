"""Completeness validation rules for TOR documents.

Uses Section_Profile of the project's procurement category.
"""

from __future__ import annotations

from app.domain.section_profile import MissingSectionProfile, profile_for_project, require_profile
from app.domain.tor_sections import CRITICAL_SECTIONS_MIN_LENGTH, MINIMUM_CONTENT_LENGTH
from app.rule_engine.engine import Finding, Severity
from app.rule_engine.rules.base import BaseRule, focus_section

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
            has_subsection = bool(str(sections.get(item.storage_key) or "").strip())
            if not has_subsection and isinstance(s4_content, dict):
                has_subsection = bool(
                    str(
                        s4_content.get(item.storage_key)
                        or s4_content.get(item.semantic_key)
                        or ""
                    ).strip()
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
    if not evaluation.strip():
        return False
    if "คุณภาพ" not in evaluation and "ประกอบ" not in evaluation:
        return False
    return "ร้อยละ" not in evaluation and "น้ำหนัก" not in evaluation


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
