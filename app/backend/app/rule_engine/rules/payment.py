"""Payment schedule validation rules.

Validates that payment installment percentages comply with procurement law:
- Sum of all installments must equal exactly 100%
- Each individual installment must be between 5% and 50% inclusive

These rules derive from พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560.

Validates: Requirements 6.3
"""

from __future__ import annotations

from app.rule_engine.engine import Finding, Severity
from app.rule_engine.rules.base import BaseRule

# Legal boundaries for individual payment installments
MIN_INSTALLMENT_PERCENT: float = 5.0
MAX_INSTALLMENT_PERCENT: float = 50.0

# Tolerance for floating-point comparison when verifying sum = 100%
SUM_TOLERANCE: float = 0.01


class PaymentScheduleRule(BaseRule):
    """Validates payment schedule percentages against procurement law.

    Checks:
    1. Payment schedule data is present in the TOR document.
    2. The sum of all installment percentages equals exactly 100% (within tolerance).
    3. No individual installment is less than 5%.
    4. No individual installment is greater than 50%.

    Expected tor_document keys:
        - payment_installments: list[float] — percentage for each installment.

    Validates: Requirements 6.3
    """

    def validate(self, tor_document: dict) -> list[Finding]:
        """Validate payment schedule against legal requirements.

        Args:
            tor_document: Dict containing payment_installments key with
                a list of percentage values for each payment installment.

        Returns:
            List of findings. Empty if payment schedule is valid.
        """
        findings: list[Finding] = []

        installments = tor_document.get("payment_installments")

        # If no payment data is present, skip validation (other rules handle missing sections)
        if installments is None:
            return findings

        # Validate that installments is a non-empty list
        if not isinstance(installments, list) or len(installments) == 0:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_violated="PAYMENT_SCHEDULE_EMPTY",
                    affected_section="s8",
                    message="ไม่พบข้อมูลงวดการชำระเงิน หรืองวดการชำระเงินว่างเปล่า",
                    recommended_correction="ระบุงวดการชำระเงินอย่างน้อย 1 งวด",
                )
            )
            return findings

        # Check 1: Sum of installments must equal 100%
        total = sum(installments)
        if abs(total - 100.0) > SUM_TOLERANCE:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_violated="PAYMENT_SUM_NOT_100",
                    affected_section="s8",
                    message=(
                        f"ผลรวมของงวดการชำระเงินเท่ากับ {total:.2f}% "
                        f"ซึ่งไม่เท่ากับ 100%"
                    ),
                    recommended_correction=(
                        "ปรับสัดส่วนการชำระเงินแต่ละงวดให้รวมกันเท่ากับ 100%"
                    ),
                )
            )

        # Check 2 & 3: Each installment must be between 5% and 50%
        for i, pct in enumerate(installments, start=1):
            if pct < MIN_INSTALLMENT_PERCENT:
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_violated="PAYMENT_INSTALLMENT_TOO_LOW",
                        affected_section="s8",
                        message=(
                            f"งวดที่ {i} มีสัดส่วน {pct:.2f}% "
                            f"ซึ่งต่ำกว่าขั้นต่ำ {MIN_INSTALLMENT_PERCENT:.0f}%"
                        ),
                        recommended_correction=(
                            f"ปรับงวดที่ {i} ให้มีสัดส่วนไม่น้อยกว่า "
                            f"{MIN_INSTALLMENT_PERCENT:.0f}%"
                        ),
                    )
                )
            elif pct > MAX_INSTALLMENT_PERCENT:
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_violated="PAYMENT_INSTALLMENT_TOO_HIGH",
                        affected_section="s8",
                        message=(
                            f"งวดที่ {i} มีสัดส่วน {pct:.2f}% "
                            f"ซึ่งสูงกว่าขีดสูงสุด {MAX_INSTALLMENT_PERCENT:.0f}%"
                        ),
                        recommended_correction=(
                            f"ปรับงวดที่ {i} ให้มีสัดส่วนไม่เกิน "
                            f"{MAX_INSTALLMENT_PERCENT:.0f}%"
                        ),
                    )
                )

        return findings
