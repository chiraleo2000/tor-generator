"""Legal compliance rules for TOR validation.

Validates TOR documents against พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560.

Rules implemented:
- VendorPaidUpCapitalRule: Verifies vendor capital = floor(budget / 4)
- PenaltyRateRule: Validates penalty rates are 0.01%–0.20% per day, minimum 100 baht/day
- BrandLockFairnessRule: Flags proprietary brand names without "or equivalent" clause
- RequiredLegalReferencesRule: Checks for required พ.ร.บ. 2560 references and clauses
"""

from __future__ import annotations

import math
import re

from app.rule_engine.engine import Finding, Severity
from app.rule_engine.rules.base import BaseRule

# Required legal references that should appear in a compliant TOR
REQUIRED_LEGAL_REFERENCES: list[str] = [
    "พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560",
    "พระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560",
]

# Alternative short forms that are also acceptable
ACCEPTABLE_SHORT_REFERENCES: list[str] = [
    "พ.ร.บ. จัดซื้อจัดจ้าง 2560",
    "พ.ร.บ. จัดซื้อจัดจ้าง พ.ศ. 2560",
    "พ.ร.บ.การจัดซื้อจัดจ้างฯ พ.ศ. 2560",
    "พ.ร.บ.จัดซื้อจัดจ้างฯ 2560",
]

# Required clauses that must be present for legal compliance
REQUIRED_CLAUSES: list[dict[str, str]] = [
    {
        "id": "vendor_qualifications",
        "description": "คุณสมบัติผู้เสนอราคา",
        "section": "s3",
    },
    {
        "id": "scope_of_work",
        "description": "ขอบเขตของงาน",
        "section": "s4",
    },
    {
        "id": "penalty_clause",
        "description": "ค่าปรับ",
        "section": "s10",
    },
    {
        "id": "warranty_clause",
        "description": "การรับประกัน",
        "section": "s9",
    },
]

# Penalty rate bounds per procurement regulations
PENALTY_RATE_MIN_PERCENT: float = 0.01  # 0.01% per day
PENALTY_RATE_MAX_PERCENT: float = 0.20  # 0.20% per day
PENALTY_MIN_BAHT_PER_DAY: float = 100.0  # Minimum 100 baht/day

# Pattern to detect brand names (common patterns)
BRAND_PATTERNS: list[re.Pattern[str]] = [
    # Common IT brand names
    re.compile(
        r"\b(Microsoft|Apple|Google|Samsung|Dell|HP|Hewlett.?Packard|Lenovo|Cisco"
        r"|Oracle|SAP|IBM|Adobe|Huawei|Sony|LG|ASUS|Acer|Intel|AMD|NVIDIA"
        r"|Canon|Epson|Brother|Xerox|Ricoh|Fuji|Toshiba|Panasonic|NEC"
        r"|Fortinet|Palo Alto|Juniper|VMware|Citrix)\b",
        re.IGNORECASE,
    ),
    # Thai transliteration patterns for common brands
    re.compile(
        r"(ไมโครซอฟท์|แอปเปิ้ล|กูเกิล|ซัมซุง|เดลล์|เลโนโว|ซิสโก้"
        r"|ออราเคิล|หัวเว่ย|โซนี่|แอลจี|แคนนอน|เอปสัน)",
    ),
]

# Equivalence phrases that indicate fair specification
EQUIVALENCE_PHRASES: list[str] = [
    "หรือเทียบเท่า",
    "หรือยี่ห้ออื่นที่เทียบเท่า",
    "หรือเทียบเคียง",
    "or equivalent",
    "or equal",
    "หรือคุณสมบัติเทียบเท่า",
    "หรือที่มีคุณสมบัติเทียบเท่า",
]


class VendorPaidUpCapitalRule(BaseRule):
    """Validate that vendor paid-up capital requirement equals floor(budget / 4).

    Per พ.ร.บ. 2560, the minimum paid-up capital for vendors must equal
    the project budget divided by 4, rounded down to the nearest integer baht.

    Validates: Requirements 6.2
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check vendor paid-up capital against budget.

        Args:
            tor_document: Must contain 'budget' (int) and optionally
                'vendor_capital' (int) for the stated capital requirement.

        Returns:
            List of findings if capital requirement is missing or incorrect.
        """
        findings: list[Finding] = []

        budget = tor_document.get("budget")
        if budget is None:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_violated="LEGAL_CAPITAL_NO_BUDGET",
                    affected_section="metadata",
                    message="ไม่พบข้อมูลงบประมาณ ไม่สามารถตรวจสอบทุนจดทะเบียนได้",
                    recommended_correction="ระบุงบประมาณในข้อมูลโครงการ",
                )
            )
            return findings

        if not isinstance(budget, (int, float)) or budget <= 0:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_violated="LEGAL_CAPITAL_INVALID_BUDGET",
                    affected_section="metadata",
                    message="งบประมาณต้องเป็นจำนวนบวก",
                    recommended_correction="แก้ไขงบประมาณให้เป็นจำนวนเต็มบวก",
                )
            )
            return findings

        expected_capital = compute_vendor_capital(budget)
        vendor_capital = tor_document.get("vendor_capital")

        if vendor_capital is None:
            # Check if vendor qualifications section mentions capital
            s3_content = tor_document.get("s3", "")
            if isinstance(s3_content, str) and "ทุนจดทะเบียน" not in s3_content:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        rule_violated="LEGAL_CAPITAL_NOT_SPECIFIED",
                        affected_section="s3",
                        message=(
                            f"ไม่พบการกำหนดทุนจดทะเบียนในคุณสมบัติผู้เสนอราคา "
                            f"ควรกำหนดไม่น้อยกว่า {expected_capital:,.0f} บาท "
                            f"(งบประมาณ {budget:,.0f} ÷ 4)"
                        ),
                        recommended_correction=(
                            f"เพิ่มเงื่อนไข: ผู้เสนอราคาต้องมีทุนจดทะเบียน "
                            f"ไม่น้อยกว่า {expected_capital:,.0f} บาท"
                        ),
                    )
                )
        else:
            # Explicit vendor_capital provided — verify it matches
            if not isinstance(vendor_capital, (int, float)):
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_violated="LEGAL_CAPITAL_INVALID_VALUE",
                        affected_section="s3",
                        message="ทุนจดทะเบียนที่กำหนดต้องเป็นตัวเลข",
                        recommended_correction=(
                            f"กำหนดทุนจดทะเบียน = {expected_capital:,.0f} บาท"
                        ),
                    )
                )
            elif int(vendor_capital) != expected_capital:
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_violated="LEGAL_CAPITAL_MISMATCH",
                        affected_section="s3",
                        message=(
                            f"ทุนจดทะเบียนที่กำหนด ({int(vendor_capital):,.0f} บาท) "
                            f"ไม่ตรงกับเกณฑ์ที่กำหนด "
                            f"(งบประมาณ {budget:,.0f} ÷ 4 = {expected_capital:,.0f} บาท)"
                        ),
                        recommended_correction=(
                            f"แก้ไขทุนจดทะเบียนเป็น {expected_capital:,.0f} บาท"
                        ),
                    )
                )

        return findings


class PenaltyRateRule(BaseRule):
    """Validate penalty rates are within legal bounds.

    Per procurement regulations:
    - Penalty rate must be between 0.01% and 0.20% per day
    - Minimum penalty amount is 100 baht per day

    Validates: Requirements 6.8
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check penalty rate against legal bounds.

        Args:
            tor_document: May contain 'penalty_rate_percent' (float, per day)
                and 'penalty_min_baht_per_day' (float). Also checks s10 content.

        Returns:
            List of findings if penalty rates are out of bounds.
        """
        findings: list[Finding] = []

        penalty_rate = tor_document.get("penalty_rate_percent")
        penalty_min_baht = tor_document.get("penalty_min_baht_per_day")

        # Check if penalty section exists
        s10_content = tor_document.get("s10", "")
        has_penalty_section = bool(s10_content and str(s10_content).strip())

        if penalty_rate is None and not has_penalty_section:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_violated="LEGAL_PENALTY_MISSING",
                    affected_section="s10",
                    message="ไม่พบการกำหนดอัตราค่าปรับในเอกสาร TOR",
                    recommended_correction=(
                        "เพิ่มข้อกำหนดค่าปรับ: อัตราร้อยละ 0.01–0.20 ต่อวัน "
                        "ขั้นต่ำ 100 บาทต่อวัน"
                    ),
                )
            )
            return findings

        if penalty_rate is not None:
            if not isinstance(penalty_rate, (int, float)):
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_violated="LEGAL_PENALTY_INVALID_TYPE",
                        affected_section="s10",
                        message="อัตราค่าปรับต้องเป็นตัวเลข",
                        recommended_correction="ระบุอัตราค่าปรับเป็นตัวเลข (ร้อยละต่อวัน)",
                    )
                )
            else:
                if penalty_rate < PENALTY_RATE_MIN_PERCENT:
                    findings.append(
                        Finding(
                            severity=Severity.ERROR,
                            rule_violated="LEGAL_PENALTY_RATE_TOO_LOW",
                            affected_section="s10",
                            message=(
                                f"อัตราค่าปรับ ({penalty_rate:.4f}% ต่อวัน) "
                                f"ต่ำกว่าอัตราขั้นต่ำ ({PENALTY_RATE_MIN_PERCENT}% ต่อวัน)"
                            ),
                            recommended_correction=(
                                f"ปรับอัตราค่าปรับให้ไม่น้อยกว่า {PENALTY_RATE_MIN_PERCENT}% ต่อวัน"
                            ),
                        )
                    )
                elif penalty_rate > PENALTY_RATE_MAX_PERCENT:
                    findings.append(
                        Finding(
                            severity=Severity.ERROR,
                            rule_violated="LEGAL_PENALTY_RATE_TOO_HIGH",
                            affected_section="s10",
                            message=(
                                f"อัตราค่าปรับ ({penalty_rate:.4f}% ต่อวัน) "
                                f"สูงกว่าอัตราสูงสุด ({PENALTY_RATE_MAX_PERCENT}% ต่อวัน)"
                            ),
                            recommended_correction=(
                                f"ปรับอัตราค่าปรับให้ไม่เกิน {PENALTY_RATE_MAX_PERCENT}% ต่อวัน"
                            ),
                        )
                    )

        if penalty_min_baht is not None:
            if isinstance(penalty_min_baht, (int, float)):
                if penalty_min_baht < PENALTY_MIN_BAHT_PER_DAY:
                    findings.append(
                        Finding(
                            severity=Severity.WARNING,
                            rule_violated="LEGAL_PENALTY_MIN_TOO_LOW",
                            affected_section="s10",
                            message=(
                                f"ค่าปรับขั้นต่ำ ({penalty_min_baht:.0f} บาท/วัน) "
                                f"ต่ำกว่าเกณฑ์ขั้นต่ำ ({PENALTY_MIN_BAHT_PER_DAY:.0f} บาท/วัน)"
                            ),
                            recommended_correction=(
                                f"กำหนดค่าปรับขั้นต่ำไม่น้อยกว่า {PENALTY_MIN_BAHT_PER_DAY:.0f} บาท/วัน"
                            ),
                        )
                    )

        return findings


class BrandLockFairnessRule(BaseRule):
    """Check for proprietary brand names without 'or equivalent' clause.

    Per procurement fairness principles, TOR documents should not specify
    particular brand names without including an equivalence clause such as
    "หรือเทียบเท่า" (or equivalent) to allow fair competition.

    Validates: Requirements 6.1 (fairness aspect of legal compliance)
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Scan TOR sections for brand names without equivalence clause.

        Args:
            tor_document: Dict with section_key -> content mapping.

        Returns:
            List of findings for each brand mention without equivalence clause.
        """
        findings: list[Finding] = []

        # Sections to check for brand-lock issues
        sections_to_check = ["s3", "s4", "s5", "s6", "s8"]

        for section_key in sections_to_check:
            content = tor_document.get(section_key, "")
            if not isinstance(content, str) or not content.strip():
                continue

            section_findings = self._check_section_for_brands(section_key, content)
            findings.extend(section_findings)

        return findings

    def _check_section_for_brands(
        self, section_key: str, content: str
    ) -> list[Finding]:
        """Check a single section's content for brand names without equivalence.

        Args:
            section_key: The TOR section identifier (e.g. 's4').
            content: The text content of the section.

        Returns:
            Findings for brand mentions lacking equivalence clauses.
        """
        findings: list[Finding] = []
        detected_brands: set[str] = set()

        for pattern in BRAND_PATTERNS:
            for match in pattern.finditer(content):
                brand_name = match.group(0)
                # Avoid duplicate findings for the same brand in the same section
                if brand_name.lower() in detected_brands:
                    continue

                # Check context around the brand mention for equivalence phrase
                context_start = max(0, match.start() - 50)
                context_end = min(len(content), match.end() + 100)
                context = content[context_start:context_end]

                has_equivalence = any(
                    phrase in context for phrase in EQUIVALENCE_PHRASES
                )

                if not has_equivalence:
                    detected_brands.add(brand_name.lower())
                    findings.append(
                        Finding(
                            severity=Severity.WARNING,
                            rule_violated="LEGAL_BRAND_LOCK",
                            affected_section=section_key,
                            message=(
                                f"พบการระบุยี่ห้อ '{brand_name}' "
                                f"โดยไม่มีข้อความ 'หรือเทียบเท่า'"
                            ),
                            recommended_correction=(
                                f"เพิ่มข้อความ 'หรือเทียบเท่า' หลังชื่อยี่ห้อ '{brand_name}' "
                                f"เพื่อเปิดกว้างการแข่งขัน"
                            ),
                        )
                    )

        return findings


class RequiredLegalReferencesRule(BaseRule):
    """Validate that TOR contains required legal references and clauses.

    A compliant TOR must reference พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560
    and contain the required clauses (qualifications, scope, penalty, warranty).

    Validates: Requirements 6.1
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check for required legal references and clauses.

        Args:
            tor_document: Dict with section_key -> content mapping.

        Returns:
            Findings for missing legal references or required clauses.
        """
        findings: list[Finding] = []

        # Check for legal reference to พ.ร.บ. 2560
        findings.extend(self._check_legal_references(tor_document))

        # Check for required clauses
        findings.extend(self._check_required_clauses(tor_document))

        return findings

    def _check_legal_references(self, tor_document: dict) -> list[Finding]:
        """Check if the TOR references the procurement act.

        Scans all text content for references to the procurement act.
        Accepts both full and abbreviated forms.
        """
        findings: list[Finding] = []

        # Collect all text content from the document
        all_text = ""
        for key, value in tor_document.items():
            if isinstance(value, str):
                all_text += " " + value

        # Check for any acceptable reference form
        all_references = REQUIRED_LEGAL_REFERENCES + ACCEPTABLE_SHORT_REFERENCES
        has_reference = any(ref in all_text for ref in all_references)

        # Also check for partial matches (in case of slight variations)
        has_partial = (
            "พ.ร.บ." in all_text and "จัดซื้อจัดจ้าง" in all_text and "2560" in all_text
        ) or ("พระราชบัญญัติ" in all_text and "จัดซื้อจัดจ้าง" in all_text and "2560" in all_text)

        if not has_reference and not has_partial:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_violated="LEGAL_REF_MISSING_ACT",
                    affected_section="s1",
                    message=(
                        "ไม่พบการอ้างอิง พ.ร.บ. การจัดซื้อจัดจ้างและ"
                        "การบริหารพัสดุภาครัฐ พ.ศ. 2560 ในเอกสาร TOR"
                    ),
                    recommended_correction=(
                        "เพิ่มการอ้างอิง 'ตามพระราชบัญญัติการจัดซื้อจัดจ้าง"
                        "และการบริหารพัสดุภาครัฐ พ.ศ. 2560' ในส่วนความเป็นมา"
                    ),
                )
            )

        return findings

    def _check_required_clauses(self, tor_document: dict) -> list[Finding]:
        """Check for presence of required TOR clauses."""
        findings: list[Finding] = []

        for clause in REQUIRED_CLAUSES:
            section_key = clause["section"]
            content = tor_document.get(section_key, "")

            if not content or (isinstance(content, str) and not content.strip()):
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_violated=f"LEGAL_CLAUSE_MISSING_{clause['id'].upper()}",
                        affected_section=section_key,
                        message=f"ไม่พบข้อกำหนดที่จำเป็น: {clause['description']}",
                        recommended_correction=(
                            f"เพิ่มเนื้อหาส่วน{clause['description']}ให้ครบถ้วน"
                        ),
                    )
                )

        return findings


def compute_vendor_capital(budget: int | float) -> int:
    """Compute the required vendor paid-up capital from project budget.

    Per พ.ร.บ. 2560 regulations, the minimum vendor paid-up capital
    (ทุนจดทะเบียน) is calculated as floor(budget / 4).

    Args:
        budget: Project budget in baht (positive number).

    Returns:
        Required minimum paid-up capital in baht (integer, rounded down).

    Raises:
        ValueError: If budget is not a positive number.
    """
    if not isinstance(budget, (int, float)) or budget <= 0:
        raise ValueError("งบประมาณต้องเป็นจำนวนบวก (budget must be positive)")
    return math.floor(budget / 4)


def validate_penalty_rate(rate_percent: float) -> bool:
    """Check if a penalty rate is within legal bounds.

    Args:
        rate_percent: Penalty rate as percentage per day (e.g. 0.10 means 0.10%/day).

    Returns:
        True if rate is within [0.01%, 0.20%] inclusive.
    """
    return PENALTY_RATE_MIN_PERCENT <= rate_percent <= PENALTY_RATE_MAX_PERCENT
