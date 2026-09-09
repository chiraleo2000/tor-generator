"""Completeness validation rules for TOR documents.

Uses Section_Profile of the project's procurement category.
"""

from __future__ import annotations

from app.domain.section_profile import MissingSectionProfile, profile_for_project, require_profile
from app.domain.tor_sections import CRITICAL_SECTIONS_MIN_LENGTH, MINIMUM_CONTENT_LENGTH
from app.rule_engine.engine import Finding, Severity
from app.rule_engine.rules.base import BaseRule

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


class SectionPresenceRule(BaseRule):
    def validate(self, tor_document: dict) -> list[Finding]:
        findings: list[Finding] = []
        missing: dict[str, str] = {}
        try:
            profile = require_profile(_category(tor_document) or "buy_goods")
        except MissingSectionProfile as exc:
            raise MissingSectionsHalt(
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
            ) from exc

        sections = _sections(tor_document)
        for item in profile.main_sections:
            if not item.required:
                continue
            content = sections.get(item.storage_key)
            empty = content is None or (isinstance(content, str) and content.strip() == "")
            if item.storage_key == "s4" and empty:
                nested = sections.get("s4")
                if isinstance(nested, dict) and any(str(v or "").strip() for v in nested.values()):
                    empty = False
                else:
                    for sub in profile.scope_subsections:
                        if str(sections.get(sub.storage_key) or "").strip():
                            empty = False
                            break
            if empty:
                missing[item.storage_key] = item.title
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_violated="COMPLETENESS_SECTION_MISSING",
                        affected_section=item.storage_key,
                        message=f"ไม่พบหัวข้อที่จำเป็น: {item.title}",
                        recommended_correction=f"กรุณาเพิ่มเนื้อหาในหัวข้อ {item.title}",
                    )
                )
        if missing:
            raise MissingSectionsHalt(missing_sections=missing, findings=findings)
        return findings


class RequiredSubsectionsRule(BaseRule):
    def validate(self, tor_document: dict) -> list[Finding]:
        findings: list[Finding] = []
        profile = profile_for_project(_category(tor_document) or "buy_goods")
        sections = _sections(tor_document)
        s4_content = sections.get("s4")
        required = [item for item in profile.scope_subsections if item.required]
        filled = 0
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
            if has_subsection:
                filled += 1
            else:
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
        for item in profile.main_sections:
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
