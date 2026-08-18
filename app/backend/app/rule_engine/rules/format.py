"""Format adherence rules for Thai government TOR documents.

Validates format requirements that account for 10% of the total Quality_Score:
- Thai government document format (proper fonts, structure)
- Section numbering (Thai digits ๑, ๒, ๓ or Arabic 1, 2, 3)
- Date format in Buddhist Era (พ.ศ.)
- Section ordering per procurement law standard

Reference: พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560
"""

from __future__ import annotations

import re

from app.domain.tor_sections import TOR_SECTION_ORDER
from app.rule_engine.engine import Finding, Severity
from app.rule_engine.rules.base import BaseRule

# Thai digits mapping
THAI_DIGITS = "๐๑๒๓๔๕๖๗๘๙"

# Buddhist Era year offset from Gregorian
BE_OFFSET = 543

STANDARD_SECTION_ORDER: list[str] = list(TOR_SECTION_ORDER)

_ASCII_SPACE = frozenset(" \t")


def _ascii_year_at(text: str, index: int) -> str | None:
    """Return four ASCII digits at index, or None. Thai digits are ignored."""
    if index < 0 or index + 4 > len(text):
        return None
    chunk = text[index : index + 4]
    if all("0" <= ch <= "9" for ch in chunk):
        return chunk
    return None


def _match_ce_label(text: str, index: int) -> tuple[int, str] | None:
    """Match ค.ศ. / คศ plus a four-digit ASCII year. Returns (end, matched)."""
    if index >= len(text) or text[index] != "ค":
        return None
    pos = index + 1
    if pos < len(text) and text[pos] == ".":
        pos += 1
    if pos >= len(text) or text[pos] != "ศ":
        return None
    pos += 1
    if pos < len(text) and text[pos] == ".":
        pos += 1
    while pos < len(text) and text[pos] in _ASCII_SPACE:
        pos += 1
    year = _ascii_year_at(text, pos)
    if year is None:
        return None
    end = pos + 4
    return end, text[index:end]


def iter_gregorian_year_matches(content: str) -> list[tuple[int, int, str]]:
    """Find ค.ศ. years and bare 19xx/20xx ASCII years (not nested in a CE label)."""
    ce_spans: list[tuple[int, int]] = []
    matches: list[tuple[int, int, str]] = []
    index = 0
    length = len(content)
    while index < length:
        ce = _match_ce_label(content, index)
        if ce is not None:
            end, matched = ce
            ce_spans.append((index, end))
            matches.append((index, end, matched.strip()))
            index = end
            continue
        index += 1

    index = 0
    while index <= length - 4:
        year = _ascii_year_at(content, index)
        if year is not None and year.startswith(("19", "20")):
            nested = any(start <= index and index + 4 <= end for start, end in ce_spans)
            if not nested:
                matches.append((index, index + 4, year))
            index += 4
            continue
        index += 1
    return matches


# Pattern for proper section numbering (Thai or Arabic digits with period/bracket)
THAI_NUMBERING_PATTERN = re.compile(
    r"^[๑-๙๐][๐-๙]*[\.\)]\s"  # Thai digit followed by period/bracket and space
)

ARABIC_NUMBERING_PATTERN = re.compile(
    r"^[0-9]+[\.\)]\s"  # NOSONAR python:S6353 — \d also matches Thai digits
)

# Mixed Thai/Arabic on one line is detected in SectionNumberingRule via per-line flags.


class ThaiDateFormatRule(BaseRule):
    """Validates that dates use Buddhist Era (พ.ศ.) format.

    Thai government documents must use Buddhist Era dates (พ.ศ.) rather than
    Gregorian (ค.ศ.) dates. This rule checks all section content for Gregorian
    date patterns and flags them.
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check all sections for improper date formats (Gregorian instead of พ.ศ.).

        Args:
            tor_document: TOR document dict with section keys and content.

        Returns:
            Findings for any Gregorian dates found that should be in พ.ศ. format.
        """
        findings: list[Finding] = []

        for section_key in STANDARD_SECTION_ORDER:
            content = tor_document.get(section_key)
            if not content or not isinstance(content, str):
                continue

            for start, end, matched_text in iter_gregorian_year_matches(content):
                # Skip if it's part of a budget/monetary value context
                context_start = max(0, start - 20)
                context_end = min(len(content), end + 20)
                context = content[context_start:context_end]

                # Skip numeric values that are clearly not dates
                if any(
                    indicator in context
                    for indicator in ["บาท", "THB", "฿", "ล้าน", "แสน", "พัน"]
                ):
                    continue

                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        rule_violated="FORMAT_DATE_BE",
                        affected_section=section_key,
                        message=(
                            f"พบรูปแบบวันที่แบบคริสต์ศักราช (ค.ศ.) ในเอกสาร: "
                            f"'{matched_text.strip()}' — "
                            f"เอกสารราชการต้องใช้พุทธศักราช (พ.ศ.)"
                        ),
                        recommended_correction=(
                            "เปลี่ยนเป็นรูปแบบ พ.ศ. โดยบวกปี ค.ศ. ด้วย 543 "
                            "(เช่น 2024 → พ.ศ. 2567)"
                        ),
                    )
                )

        return findings


class SectionNumberingRule(BaseRule):
    """Validates proper and consistent section numbering format.

    Thai government documents should use consistent numbering throughout:
    either Thai digits (๑, ๒, ๓) or Arabic digits (1, 2, 3), but not mixed
    within the same document.
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check sections for proper and consistent numbering format.

        Args:
            tor_document: TOR document dict with section keys and content.

        Returns:
            Findings for inconsistent or improper numbering.
        """
        findings: list[Finding] = []

        thai_numbered_sections: list[str] = []
        arabic_numbered_sections: list[str] = []

        for section_key in STANDARD_SECTION_ORDER:
            content = tor_document.get(section_key)
            if not content or not isinstance(content, str):
                continue

            lines = content.split("\n")
            has_thai = False
            has_arabic = False

            for line in lines:
                stripped = line.strip()
                if THAI_NUMBERING_PATTERN.match(stripped):
                    has_thai = True
                if ARABIC_NUMBERING_PATTERN.match(stripped):
                    has_arabic = True

            if has_thai:
                thai_numbered_sections.append(section_key)
            if has_arabic:
                arabic_numbered_sections.append(section_key)

            # Check for mixed numbering within a single section
            if has_thai and has_arabic:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        rule_violated="FORMAT_NUMBERING_MIXED_SECTION",
                        affected_section=section_key,
                        message=(
                            f"พบการใช้เลขไทยและเลขอารบิกปนกัน "
                            f"ในหัวข้อ {section_key} — "
                            f"ควรใช้รูปแบบเดียวตลอดทั้งหัวข้อ"
                        ),
                        recommended_correction=(
                            "เลือกใช้เลขไทย (๑, ๒, ๓) หรือเลขอารบิก (1, 2, 3) "
                            "อย่างสม่ำเสมอตลอดทั้งหัวข้อ"
                        ),
                    )
                )

        # Check for inconsistent numbering across the document
        if thai_numbered_sections and arabic_numbered_sections:
            findings.append(
                Finding(
                    severity=Severity.SUGGESTION,
                    rule_violated="FORMAT_NUMBERING_INCONSISTENT_DOC",
                    affected_section="document",
                    message=(
                        "พบการใช้เลขไทยและเลขอารบิกไม่สม่ำเสมอข้ามหัวข้อ — "
                        f"หัวข้อที่ใช้เลขไทย: {', '.join(thai_numbered_sections)}, "
                        f"หัวข้อที่ใช้เลขอารบิก: {', '.join(arabic_numbered_sections)}"
                    ),
                    recommended_correction=(
                        "แนะนำให้ใช้รูปแบบการเรียงลำดับเดียวกันตลอดทั้งเอกสาร "
                        "เพื่อความเป็นระเบียบ"
                    ),
                )
            )

        return findings


class SectionOrderingRule(BaseRule):
    """Validates that TOR sections follow the standard ordering.

    Per Thai procurement law format, TOR documents must present sections
    in the prescribed order. Out-of-order sections are flagged.
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check that sections appear in the correct procurement law order.

        Args:
            tor_document: TOR document dict with section keys and content.

        Returns:
            Findings for sections that are out of order.
        """
        findings: list[Finding] = []

        # Get list of present sections in their document order
        # The tor_document may have a 'section_order' key or we infer from keys
        section_order = tor_document.get("section_order")

        if section_order and isinstance(section_order, list):
            # Verify against standard order
            expected_positions: dict[str, int] = {
                key: idx for idx, key in enumerate(STANDARD_SECTION_ORDER)
            }

            # Filter to only sections that are in the standard set
            present_sections = [
                s for s in section_order if s in expected_positions
            ]

            # Check if present sections maintain relative order
            last_position = -1
            for section in present_sections:
                position = expected_positions[section]
                if position < last_position:
                    findings.append(
                        Finding(
                            severity=Severity.WARNING,
                            rule_violated="FORMAT_SECTION_ORDER",
                            affected_section=section,
                            message=(
                                f"หัวข้อ {section} อยู่ผิดลำดับ — "
                                f"ตามรูปแบบมาตรฐานการจัดซื้อจัดจ้าง "
                                f"หัวข้อนี้ควรอยู่ก่อนหัวข้อที่ตามหลัง"
                            ),
                            recommended_correction=(
                                "จัดเรียงหัวข้อตามลำดับมาตรฐาน: "
                                "ความเป็นมา → วัตถุประสงค์ → คุณสมบัติ → "
                                "ขอบเขตงาน → ระยะเวลา → เกณฑ์พิจารณา → "
                                "งบประมาณ → การจ่ายเงิน → บทลงโทษ → "
                                "เอกสารแนบ → สถานที่ส่งมอบ → การตรวจรับ → "
                                "เงื่อนไขอื่นๆ"
                            ),
                        )
                    )
                    break  # Report first out-of-order section
                last_position = position

        return findings


class ThaiDocumentFormatRule(BaseRule):
    """Validates general Thai government document formatting conventions.

    Checks for:
    - Presence of proper document header elements
    - Section headings format (bold, numbered)
    - Minimum content structure per section
    - Proper use of formal Thai language indicators
    """

    # Common formal Thai indicators expected in government documents
    FORMAL_INDICATORS = [
        "ทั้งนี้",
        "โดย",
        "ตาม",
        "แห่ง",
        "เพื่อ",
        "อาศัยอำนาจ",
        "ตามที่",
        "ดังนี้",
        "ดังต่อไปนี้",
    ]

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check general Thai document formatting conventions.

        Args:
            tor_document: TOR document dict with section keys and content.

        Returns:
            Findings for formatting issues in the document.
        """
        findings: list[Finding] = []

        # Check for document header/title presence
        title = tor_document.get("title") or tor_document.get("document_title")
        if not title:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_violated="FORMAT_MISSING_TITLE",
                    affected_section="document",
                    message=(
                        "ไม่พบชื่อเอกสาร TOR — "
                        "เอกสารราชการต้องมีชื่อเรื่องที่ชัดเจน"
                    ),
                    recommended_correction=(
                        "เพิ่มชื่อเอกสาร เช่น "
                        "'ขอบเขตของงาน (Terms of Reference: TOR) "
                        "โครงการ...'"
                    ),
                )
            )

        # Check sections for minimum content structure
        for section_key in STANDARD_SECTION_ORDER:
            content = tor_document.get(section_key)
            if not content or not isinstance(content, str):
                continue

            # Check for extremely short sections (less than 50 chars likely incomplete)
            stripped_content = content.strip()
            if len(stripped_content) < 50:
                findings.append(
                    Finding(
                        severity=Severity.SUGGESTION,
                        rule_violated="FORMAT_SECTION_TOO_SHORT",
                        affected_section=section_key,
                        message=(
                            f"หัวข้อ {section_key} มีเนื้อหาสั้นเกินไป "
                            f"({len(stripped_content)} ตัวอักษร) — "
                            f"อาจไม่ครบถ้วนตามรูปแบบราชการ"
                        ),
                        recommended_correction=(
                            "เพิ่มรายละเอียดให้ครบถ้วนตามรูปแบบมาตรฐาน "
                            "ของเอกสาร TOR ภาครัฐ"
                        ),
                    )
                )

        # Check Background section (s1) has proper formal tone indicators
        background = tor_document.get("s1")
        if background and isinstance(background, str):
            has_formal_indicator = any(
                indicator in background for indicator in self.FORMAL_INDICATORS
            )
            if not has_formal_indicator and len(background.strip()) > 100:
                findings.append(
                    Finding(
                        severity=Severity.SUGGESTION,
                        rule_violated="FORMAT_INFORMAL_TONE",
                        affected_section="s1",
                        message=(
                            "หัวข้อความเป็นมาอาจไม่เป็นภาษาราชการ — "
                            "ไม่พบคำที่ใช้ในเอกสารราชการ เช่น "
                            "'ทั้งนี้', 'ตามที่', 'โดย', 'ดังนี้'"
                        ),
                        recommended_correction=(
                            "ปรับภาษาให้เป็นภาษาราชการ (ภาษาทางการ) "
                            "ตามรูปแบบหนังสือราชการ"
                        ),
                    )
                )

        return findings


# Convenience function to get all format rules
def get_format_rules() -> list[BaseRule]:
    """Return all format adherence rule instances.

    Returns:
        List of BaseRule instances for format validation.
    """
    return [
        ThaiDateFormatRule(),
        SectionNumberingRule(),
        SectionOrderingRule(),
        ThaiDocumentFormatRule(),
    ]
