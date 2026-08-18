"""Consistency validation rules for TOR documents.

Validates cross-section consistency to ensure different parts of the TOR
are aligned and do not contradict each other:
- Budget ↔ Scope alignment
- Timeline ↔ Deliverables alignment
- Qualifications ↔ Scope complexity alignment

These rules implement Requirement 6.5 of the specification.
"""

from __future__ import annotations

import re

from app.rule_engine.engine import Finding, Severity
from app.rule_engine.rules.base import BaseRule


# Keywords indicating high-complexity scope that requires stronger qualifications
HIGH_COMPLEXITY_KEYWORDS: list[str] = [
    "ระบบสารสนเทศ",        # Information system
    "บูรณาการ",            # Integration
    "เชื่อมโยง",           # Interconnection
    "ฐานข้อมูลขนาดใหญ่",   # Large database
    "ความปลอดภัย",         # Security
    "Cloud",
    "AI",
    "Machine Learning",
    "Blockchain",
    "IoT",
    "ระบบเครือข่าย",       # Network system
    "Data Center",
    "ก่อสร้างอาคาร",       # Building construction
    "โครงสร้างพื้นฐาน",    # Infrastructure
]

# Keywords indicating scope requires specific professional qualifications
PROFESSIONAL_SCOPE_KEYWORDS: dict[str, list[str]] = {
    "it": [
        "ระบบสารสนเทศ",
        "ซอฟต์แวร์",
        "เว็บไซต์",
        "แอปพลิเคชัน",
        "ระบบเครือข่าย",
        "Data Center",
        "Cloud",
        "IT",
    ],
    "construction": [
        "ก่อสร้าง",
        "อาคาร",
        "ถนน",
        "สะพาน",
        "ปรับปรุงอาคาร",
        "โครงสร้าง",
        "งานโยธา",
    ],
    "consulting": [
        "ที่ปรึกษา",
        "ศึกษาวิจัย",
        "ออกแบบ",
        "วิเคราะห์",
        "ประเมินผล",
        "สำรวจ",
    ],
}

# Budget thresholds for complexity assessment (in Thai Baht)
HIGH_BUDGET_THRESHOLD: int = 50_000_000  # 50 million baht
MEDIUM_BUDGET_THRESHOLD: int = 10_000_000  # 10 million baht


class BudgetScopeConsistencyRule(BaseRule):
    """Validate that budget is proportionate to scope of work.

    Checks:
    - Large/complex scope should have adequate budget
    - Budget value mentioned in budget section should match metadata
    - Scope complexity indicators should align with budget range
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check budget-scope alignment.

        Args:
            tor_document: Dict with sections (s1..s13) and metadata
                (budget, project_type).

        Returns:
            List of findings for budget-scope inconsistencies.
        """
        findings: list[Finding] = []
        sections = tor_document.get("sections", tor_document)
        metadata = tor_document.get("metadata", {})

        budget = metadata.get("budget") or tor_document.get("budget")
        scope_content = sections.get("s4", "")
        budget_content = sections.get("s6", "")

        if budget is None:
            return findings

        # Ensure budget is numeric
        try:
            budget = int(budget)
        except (TypeError, ValueError):
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_violated="CONSISTENCY_BUDGET_INVALID",
                    affected_section="s6",
                    message="งบประมาณไม่ใช่ตัวเลขที่ถูกต้อง",
                    recommended_correction="กรุณาระบุงบประมาณเป็นจำนวนเต็มบวก",
                )
            )
            return findings

        # Get scope text for analysis
        scope_text = self._get_text(scope_content)

        # Check if high-complexity scope has adequate budget
        complexity_count = self._count_complexity_indicators(scope_text)

        if complexity_count >= 3 and budget < MEDIUM_BUDGET_THRESHOLD:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_violated="CONSISTENCY_BUDGET_LOW_FOR_SCOPE",
                    affected_section="s6",
                    message=(
                        f"ขอบเขตงานมีความซับซ้อนสูง "
                        f"(ตัวชี้วัดความซับซ้อน {complexity_count} รายการ) "
                        f"แต่งบประมาณ ({budget:,.0f} บาท) อาจไม่เพียงพอ"
                    ),
                    recommended_correction=(
                        "กรุณาทบทวนงบประมาณให้สอดคล้องกับความซับซ้อนของขอบเขตงาน "
                        "หรือลดขอบเขตงานให้เหมาะสมกับงบประมาณ"
                    ),
                )
            )

        # Check if budget content mentions a different amount than metadata
        budget_text = self._get_text(budget_content)
        mentioned_amounts = self._extract_budget_amounts(budget_text)

        if mentioned_amounts and budget > 0:
            # Check if metadata budget matches any mentioned amount
            budget_matched = any(
                abs(amount - budget) / budget < 0.01  # 1% tolerance
                for amount in mentioned_amounts
                if amount > 0
            )
            if not budget_matched and mentioned_amounts:
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_violated="CONSISTENCY_BUDGET_MISMATCH",
                        affected_section="s6",
                        message=(
                            f"จำนวนเงินในหัวข้องบประมาณ "
                            f"ไม่ตรงกับงบประมาณโครงการ ({budget:,.0f} บาท)"
                        ),
                        recommended_correction=(
                            "กรุณาตรวจสอบให้จำนวนเงินในหัวข้องบประมาณ"
                            "ตรงกับงบประมาณโครงการที่ระบุ"
                        ),
                    )
                )

        return findings

    def _get_text(self, content: str | dict | None) -> str:
        """Extract text from section content (may be str or dict)."""
        if content is None:
            return ""
        if isinstance(content, dict):
            return " ".join(str(v) for v in content.values() if v is not None)
        return str(content)

    def _count_complexity_indicators(self, text: str) -> int:
        """Count how many complexity keywords appear in the scope text."""
        text_lower = text.lower()
        count = 0
        for keyword in HIGH_COMPLEXITY_KEYWORDS:
            if keyword.lower() in text_lower:
                count += 1
        return count

    def _extract_budget_amounts(self, text: str) -> list[int]:
        """Extract monetary amounts from budget text.

        Looks for patterns like:
        - 1,000,000 บาท
        - 1000000
        - ๑,๐๐๐,๐๐๐
        """
        amounts: list[int] = []

        # Match numbers with commas followed by "บาท" (possessive digits, no nested optional)
        pattern = r"(\d[\d,]*(?:\.\d+)?)\s+บาท"
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                amount = int(match.replace(",", "").split(".")[0])
                if amount > 0:
                    amounts.append(amount)
            except ValueError:
                continue

        return amounts


class TimelineDeliverablesConsistencyRule(BaseRule):
    """Validate that timeline is consistent with deliverables.

    Checks:
    - Number of deliverables should be achievable within timeline
    - Payment milestones should align with timeline phases
    - Deliverable submission dates should fall within project timeline
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check timeline-deliverables alignment.

        Args:
            tor_document: Dict with sections and metadata.
                Metadata should include timeline_days.

        Returns:
            List of findings for timeline-deliverables inconsistencies.
        """
        findings: list[Finding] = []
        sections = tor_document.get("sections", tor_document)
        metadata = tor_document.get("metadata", {})

        timeline_days = metadata.get("timeline_days") or tor_document.get(
            "timeline_days"
        )
        scope_content = sections.get("s4", "")
        payment_content = sections.get("s8", "")

        if timeline_days is None:
            return findings

        try:
            timeline_days = int(timeline_days)
        except (TypeError, ValueError):
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_violated="CONSISTENCY_TIMELINE_INVALID",
                    affected_section="s5",
                    message="ระยะเวลาดำเนินการไม่ใช่ตัวเลขที่ถูกต้อง",
                    recommended_correction="กรุณาระบุระยะเวลาดำเนินการเป็นจำนวนวัน",
                )
            )
            return findings

        # Count deliverables mentioned in scope
        scope_text = self._get_text(scope_content)
        deliverable_count = self._count_deliverables(scope_text)

        # Check if number of deliverables is feasible given timeline
        if deliverable_count > 0 and timeline_days > 0:
            days_per_deliverable = timeline_days / deliverable_count
            if days_per_deliverable < 7:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        rule_violated="CONSISTENCY_TIMELINE_TOO_SHORT_FOR_DELIVERABLES",
                        affected_section="s5",
                        message=(
                            f"ระยะเวลาดำเนินการ ({timeline_days} วัน) "
                            f"อาจไม่เพียงพอสำหรับผลงานส่งมอบ "
                            f"{deliverable_count} รายการ "
                            f"(เฉลี่ย {days_per_deliverable:.0f} วัน/รายการ)"
                        ),
                        recommended_correction=(
                            "กรุณาทบทวนระยะเวลาดำเนินการให้เพียงพอ "
                            "หรือลดจำนวนผลงานส่งมอบ"
                        ),
                    )
                )

        # Check payment installments vs timeline
        payment_text = self._get_text(payment_content)
        payment_phases = self._count_payment_phases(payment_text)

        if payment_phases > 0 and timeline_days > 0:
            days_per_phase = timeline_days / payment_phases
            if days_per_phase < 15:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        rule_violated="CONSISTENCY_PAYMENT_PHASES_TOO_MANY",
                        affected_section="s8",
                        message=(
                            f"จำนวนงวดการชำระเงิน ({payment_phases} งวด) "
                            f"มากเกินไปสำหรับระยะเวลา {timeline_days} วัน "
                            f"(เฉลี่ย {days_per_phase:.0f} วัน/งวด)"
                        ),
                        recommended_correction=(
                            "กรุณาลดจำนวนงวดการชำระเงิน "
                            "หรือเพิ่มระยะเวลาดำเนินการ"
                        ),
                    )
                )

        return findings

    def _get_text(self, content: str | dict | None) -> str:
        """Extract text from section content (may be str or dict)."""
        if content is None:
            return ""
        if isinstance(content, dict):
            return " ".join(str(v) for v in content.values() if v is not None)
        return str(content)

    def _count_deliverables(self, text: str) -> int:
        """Count deliverable mentions in scope text.

        Looks for:
        - ผลงานส่งมอบ (deliverable)
        - งวดที่/งวดงาน (phase/installment)
        - Numbered deliverable items
        """
        count = 0

        # Count explicit deliverable mentions
        deliverable_patterns = [
            r"ผลงานส่งมอบ",
            r"งวดที่\s*\d+",
            r"ส่งมอบงาน",
            r"deliverable",
        ]
        for pattern in deliverable_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            count += len(matches)

        # If no explicit mentions, try numbered items as heuristic
        if count == 0:
            numbered_items = re.findall(r"^\s*\d+[.)]\s", text, re.MULTILINE)
            count = len(numbered_items)

        return count

    def _count_payment_phases(self, text: str) -> int:
        """Count payment phases/installments in payment section."""
        patterns = [
            r"งวดที่\s*\d+",
            r"งวด\s*\d+",
            r"ครั้งที่\s*\d+",
            r"installment\s*\d+",
        ]
        phases: set[str] = set()
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            phases.update(matches)
        return len(phases)


class QualificationsComplexityConsistencyRule(BaseRule):
    """Validate that vendor qualifications match scope complexity.

    Checks:
    - Complex IT scope requires IT-related qualifications
    - Construction scope requires engineering qualifications
    - Consulting scope requires relevant professional experience
    - High-budget projects should require proportionate experience
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Check qualifications-complexity alignment.

        Args:
            tor_document: Dict with sections and metadata.

        Returns:
            List of findings for qualifications-complexity inconsistencies.
        """
        findings: list[Finding] = []
        sections = tor_document.get("sections", tor_document)
        metadata = tor_document.get("metadata", {})

        scope_content = sections.get("s4", "")
        qualifications_content = sections.get("s3", "")
        budget = metadata.get("budget") or tor_document.get("budget")

        scope_text = self._get_text(scope_content)
        qual_text = self._get_text(qualifications_content)

        if not scope_text or not qual_text:
            return findings

        # Determine scope domain(s)
        scope_domains = self._detect_domains(scope_text)

        # Check if qualifications mention relevant domain expertise
        if scope_domains and qual_text:
            for domain in scope_domains:
                domain_keywords = PROFESSIONAL_SCOPE_KEYWORDS.get(domain, [])
                has_relevant_qualification = any(
                    kw.lower() in qual_text.lower() for kw in domain_keywords
                )

                # Also check for generic experience keywords
                experience_keywords = [
                    "ประสบการณ์",
                    "ผลงาน",
                    "เคยดำเนินการ",
                    "ผ่านงาน",
                ]
                has_experience_mention = any(
                    kw in qual_text for kw in experience_keywords
                )

                if not has_relevant_qualification and not has_experience_mention:
                    domain_label = {
                        "it": "เทคโนโลยีสารสนเทศ",
                        "construction": "งานก่อสร้าง",
                        "consulting": "งานที่ปรึกษา",
                    }.get(domain, domain)

                    findings.append(
                        Finding(
                            severity=Severity.WARNING,
                            rule_violated="CONSISTENCY_QUALIFICATIONS_MISMATCH",
                            affected_section="s3",
                            message=(
                                f"ขอบเขตงานเกี่ยวข้องกับ{domain_label} "
                                f"แต่ไม่พบการกำหนดคุณสมบัติ"
                                f"ด้าน{domain_label}ของผู้เสนอราคา"
                            ),
                            recommended_correction=(
                                f"กรุณาเพิ่มคุณสมบัติด้าน{domain_label} "
                                f"ในหัวข้อคุณสมบัติของผู้เสนอราคา "
                                f"เช่น ประสบการณ์ ผลงานที่ผ่านมา"
                            ),
                        )
                    )

        # Check if high budget requires stronger qualifications
        if budget is not None:
            try:
                budget_val = int(budget)
            except (TypeError, ValueError):
                budget_val = 0

            if budget_val >= HIGH_BUDGET_THRESHOLD:
                # High-budget projects should mention experience/track record
                strong_qual_keywords = [
                    "ประสบการณ์",
                    "ผลงาน",
                    "ทุนจดทะเบียน",
                    "ไม่น้อยกว่า",
                    "ขึ้นทะเบียน",
                ]
                has_strong_qualifications = any(
                    kw in qual_text for kw in strong_qual_keywords
                )
                if not has_strong_qualifications:
                    findings.append(
                        Finding(
                            severity=Severity.WARNING,
                            rule_violated="CONSISTENCY_QUALIFICATIONS_WEAK_FOR_BUDGET",
                            affected_section="s3",
                            message=(
                                f"โครงการมีงบประมาณสูง ({budget_val:,.0f} บาท) "
                                f"แต่ไม่พบการกำหนดคุณสมบัติที่เข้มงวด "
                                f"เช่น ประสบการณ์ ผลงานที่ผ่านมา ทุนจดทะเบียน"
                            ),
                            recommended_correction=(
                                "กรุณาเพิ่มเงื่อนไขคุณสมบัติที่เข้มงวดขึ้น "
                                "สำหรับโครงการที่มีงบประมาณสูง เช่น "
                                "ผลงานในวงเงินไม่น้อยกว่า... "
                                "ประสบการณ์ไม่น้อยกว่า... ปี"
                            ),
                        )
                    )

        return findings

    def _get_text(self, content: str | dict | None) -> str:
        """Extract text from section content (may be str or dict)."""
        if content is None:
            return ""
        if isinstance(content, dict):
            return " ".join(str(v) for v in content.values() if v is not None)
        return str(content)

    def _detect_domains(self, text: str) -> list[str]:
        """Detect which professional domains are involved in the scope."""
        domains: list[str] = []
        text_lower = text.lower()

        for domain, keywords in PROFESSIONAL_SCOPE_KEYWORDS.items():
            if any(kw.lower() in text_lower for kw in keywords):
                domains.append(domain)

        return domains
