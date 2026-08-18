"""Completeness validation rules for TOR documents.

Validates that TOR documents contain all 13 required sections as defined
by Thai procurement law (พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560),
that required subsections are present, and that content meets minimum length.

If required sections are missing, scoring is halted and a list of missing
sections is returned before proceeding with further validation (Req 6.9).
"""

from __future__ import annotations

from app.domain.tor_sections import (
    CRITICAL_SECTIONS_MIN_LENGTH,
    MINIMUM_CONTENT_LENGTH,
    SCOPE_REQUIRED_SUBSECTIONS,
    TOR_SECTION_LABELS_BILINGUAL,
)
from app.rule_engine.engine import Finding, Severity
from app.rule_engine.rules.base import BaseRule

TOR_REQUIRED_SECTIONS: dict[str, str] = TOR_SECTION_LABELS_BILINGUAL


class MissingSectionsHalt(Exception):
    """Raised when required sections are missing, signaling scoring should halt.

    Attributes:
        missing_sections: Dict of section_key -> section_name for missing sections.
        findings: Findings for the missing sections.
    """

    def __init__(
        self, missing_sections: dict[str, str], findings: list[Finding]
    ) -> None:
        self.missing_sections = missing_sections
        self.findings = findings
        super().__init__(
            f"Missing required sections: {', '.join(missing_sections.keys())}"
        )


class SectionPresenceRule(BaseRule):
    """Validate that all 13 required TOR sections are present.

    If required sections are missing, this rule raises MissingSectionsHalt
    to signal that scoring should be halted (Requirement 6.9).
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check that all 13 required sections exist in the document.

        Args:
            tor_document: Dict with section_key -> content mapping.

        Returns:
            List of findings for missing sections.

        Raises:
            MissingSectionsHalt: If any required section is missing,
                signaling that scoring should halt.
        """
        findings: list[Finding] = []
        missing: dict[str, str] = {}

        sections = tor_document.get("sections", tor_document)

        for section_key, section_name in TOR_REQUIRED_SECTIONS.items():
            content = sections.get(section_key)
            if content is None or (isinstance(content, str) and content.strip() == ""):
                missing[section_key] = section_name
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_violated="COMPLETENESS_SECTION_MISSING",
                        affected_section=section_key,
                        message=f"ไม่พบหัวข้อที่จำเป็น: {section_name}",
                        recommended_correction=(
                            f"กรุณาเพิ่มเนื้อหาในหัวข้อ {section_name}"
                        ),
                    )
                )

        if missing:
            raise MissingSectionsHalt(missing_sections=missing, findings=findings)

        return findings


class RequiredSubsectionsRule(BaseRule):
    """Validate that required subsections are present within sections.

    Specifically checks that Scope of Work (s4) has the mandatory subsections
    (work details and deliverables).
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check that required subsections exist.

        Args:
            tor_document: Dict with section_key -> content mapping.
                Subsections can be specified as 's4.1', 's4.2', etc.
                or as a nested dict under 's4' with keys '4.1', '4.2', etc.

        Returns:
            List of findings for missing subsections.
        """
        findings: list[Finding] = []
        sections = tor_document.get("sections", tor_document)

        # Check Scope of Work subsections
        s4_content = sections.get("s4")

        for subsection_key, subsection_name in SCOPE_REQUIRED_SUBSECTIONS.items():
            has_subsection = False

            # Check if subsection exists as top-level key (e.g., "s4.1")
            if sections.get(subsection_key):
                has_subsection = True
            # Check if s4 is a dict containing subsection keys
            elif isinstance(s4_content, dict):
                # Try both "s4.1" and "4.1" formats
                short_key = subsection_key.replace("s", "", 1)  # "4.1"
                sub_key = subsection_key.split(".")[-1]  # "1"
                if (
                    s4_content.get(subsection_key)
                    or s4_content.get(short_key)
                    or s4_content.get(sub_key)
                ):
                    has_subsection = True

            if not has_subsection:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        rule_violated="COMPLETENESS_SUBSECTION_MISSING",
                        affected_section="s4",
                        message=(
                            f"ไม่พบหัวข้อย่อยที่จำเป็นใน"
                            f"ขอบเขตของงาน: {subsection_name}"
                        ),
                        recommended_correction=(
                            f"กรุณาเพิ่มหัวข้อย่อย {subsection_name} "
                            f"ในขอบเขตของงาน"
                        ),
                    )
                )

        return findings


class MinimumContentRule(BaseRule):
    """Validate that sections contain meaningful content above minimum length.

    Each section must have at least MINIMUM_CONTENT_LENGTH characters,
    and critical sections have higher minimums as specified in
    CRITICAL_SECTIONS_MIN_LENGTH.
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check that sections meet minimum content length requirements.

        Args:
            tor_document: Dict with section_key -> content mapping.

        Returns:
            List of findings for sections with insufficient content.
        """
        findings: list[Finding] = []
        sections = tor_document.get("sections", tor_document)

        for section_key in TOR_REQUIRED_SECTIONS:
            content = sections.get(section_key)
            if content is None:
                # Missing sections are handled by SectionPresenceRule
                continue

            # Get content as string
            if isinstance(content, dict):
                # If section is a dict (e.g., scope with subsections),
                # join all values for length check
                text = " ".join(
                    str(v) for v in content.values() if v is not None
                )
            else:
                text = str(content)

            text = text.strip()

            # Get minimum length for this section
            min_length = CRITICAL_SECTIONS_MIN_LENGTH.get(
                section_key, MINIMUM_CONTENT_LENGTH
            )

            if len(text) < min_length:
                section_name = TOR_REQUIRED_SECTIONS[section_key]
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        rule_violated="COMPLETENESS_CONTENT_TOO_SHORT",
                        affected_section=section_key,
                        message=(
                            f"เนื้อหาในหัวข้อ {section_name} สั้นเกินไป "
                            f"(ความยาว {len(text)} อักขระ, "
                            f"ขั้นต่ำ {min_length} อักขระ)"
                        ),
                        recommended_correction=(
                            f"กรุณาเพิ่มรายละเอียดในหัวข้อ {section_name} "
                            f"ให้มีความยาวอย่างน้อย {min_length} อักขระ"
                        ),
                    )
                )

        return findings
