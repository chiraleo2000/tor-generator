"""Timeline feasibility validation rules.

Validates that project duration is appropriate for the given budget:
- Budget > 100 million baht → duration must be at least 180 days
- Budget < 10 million baht → duration must not exceed 365 days

These thresholds ensure that large projects have sufficient implementation time
and that small projects do not drag on excessively.

Validates: Requirements 6.4
"""

from __future__ import annotations

from app.rule_engine.engine import Finding, Severity
from app.rule_engine.rules.base import BaseRule

# Budget thresholds (in baht)
HIGH_BUDGET_THRESHOLD: int = 100_000_000  # 100 million baht
LOW_BUDGET_THRESHOLD: int = 10_000_000  # 10 million baht

# Duration thresholds (in days)
HIGH_BUDGET_MIN_DAYS: int = 180
LOW_BUDGET_MAX_DAYS: int = 365


class TimelineFeasibilityRule(BaseRule):
    """Validates timeline feasibility relative to project budget.

    Checks:
    1. If budget exceeds 100 million baht, duration must be at least 180 days.
    2. If budget is less than 10 million baht, duration must not exceed 365 days.

    Expected tor_document keys:
        - budget: int — project budget in baht.
        - timeline_days: int — project duration in days.

    Validates: Requirements 6.4
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Validate timeline feasibility against budget-based rules.

        Args:
            tor_document: Dict containing budget and timeline_days keys.

        Returns:
            List of findings. Empty if timeline is feasible.
        """
        findings: list[Finding] = []

        budget = tor_document.get("budget")
        timeline_days = tor_document.get("timeline_days")

        # If budget or timeline data is missing, skip validation
        if budget is None or timeline_days is None:
            return findings

        # Rule 1: High budget (> 100M) requires at least 180 days
        if budget > HIGH_BUDGET_THRESHOLD and timeline_days < HIGH_BUDGET_MIN_DAYS:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_violated="TIMELINE_TOO_SHORT_FOR_BUDGET",
                    affected_section="s5",
                    message=(
                        f"งบประมาณ {budget:,.0f} บาท (เกิน 100 ล้านบาท) "
                        f"แต่ระยะเวลาดำเนินการเพียง {timeline_days} วัน "
                        f"ซึ่งน้อยกว่าขั้นต่ำ {HIGH_BUDGET_MIN_DAYS} วัน"
                    ),
                    recommended_correction=(
                        f"เพิ่มระยะเวลาดำเนินการให้ไม่น้อยกว่า {HIGH_BUDGET_MIN_DAYS} วัน "
                        f"สำหรับโครงการที่มีงบประมาณเกิน 100 ล้านบาท"
                    ),
                )
            )

        # Rule 2: Low budget (< 10M) should not exceed 365 days
        if budget < LOW_BUDGET_THRESHOLD and timeline_days > LOW_BUDGET_MAX_DAYS:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    rule_violated="TIMELINE_TOO_LONG_FOR_BUDGET",
                    affected_section="s5",
                    message=(
                        f"งบประมาณ {budget:,.0f} บาท (น้อยกว่า 10 ล้านบาท) "
                        f"แต่ระยะเวลาดำเนินการ {timeline_days} วัน "
                        f"ซึ่งเกินกว่า {LOW_BUDGET_MAX_DAYS} วัน"
                    ),
                    recommended_correction=(
                        f"ลดระยะเวลาดำเนินการให้ไม่เกิน {LOW_BUDGET_MAX_DAYS} วัน "
                        f"สำหรับโครงการที่มีงบประมาณน้อยกว่า 10 ล้านบาท"
                    ),
                )
            )

        return findings
