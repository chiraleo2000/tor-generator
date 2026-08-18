"""Property-based tests for Payment Schedule Percentage Invariant (Property 3).

Verifies that the Rule Engine correctly validates payment schedules:
- Valid schedules (sum=100%, each installment 5%–50%) pass validation
- Invalid schedules (sum≠100% or installment out of range) are rejected
- Penalty rates within [0.01%, 0.20%] pass and outside fail

**Validates: Requirements 6.3, 6.8**

# Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.rule_engine.engine import RuleEngine, Severity
from app.rule_engine.rules.legal import (
    PENALTY_RATE_MAX_PERCENT,
    PENALTY_RATE_MIN_PERCENT,
    PenaltyRateRule,
    validate_penalty_rate,
)
from app.rule_engine.rules.payment import (
    MAX_INSTALLMENT_PERCENT,
    MIN_INSTALLMENT_PERCENT,
    SUM_TOLERANCE,
    PaymentScheduleRule,
)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


def _valid_installments_strategy():
    """Generate a list of installment percentages that sum to 100% and each is in [5, 50].

    Strategy approach:
    1. Pick a number of installments n (between 2 and 20, since max installment is 50%
       and min is 5%, we need at least 2 to sum to 100%).
    2. Generate n random values in [5, 50].
    3. Normalize them so they sum to exactly 100%.
    4. Verify all values still fall within [5, 50] after normalization.
    """
    return (
        st.integers(min_value=2, max_value=20)
        .flatmap(
            lambda n: st.lists(
                st.floats(min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False),
                min_size=n,
                max_size=n,
            )
        )
        .map(_normalize_to_100)
        .filter(lambda xs: all(MIN_INSTALLMENT_PERCENT <= x <= MAX_INSTALLMENT_PERCENT for x in xs))
        .filter(lambda xs: abs(sum(xs) - 100.0) <= SUM_TOLERANCE)
    )


def _normalize_to_100(values: list[float]) -> list[float]:
    """Normalize a list of positive floats so they sum to exactly 100.0."""
    total = sum(values)
    if total == 0:
        return values
    factor = 100.0 / total
    normalized = [round(v * factor, 4) for v in values]
    # Adjust the last element to ensure exact sum = 100
    diff = 100.0 - sum(normalized[:-1])
    normalized[-1] = round(diff, 4)
    return normalized


# Strategy for invalid sum: installments that sum to something other than 100%
def _invalid_sum_installments_strategy():
    """Generate installments where sum significantly deviates from 100%."""
    return st.lists(
        st.floats(min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=10,
    ).filter(lambda xs: abs(sum(xs) - 100.0) > SUM_TOLERANCE)


# Strategy for installments with at least one value out of [5, 50] range
def _out_of_range_installment_strategy():
    """Generate installments where at least one is below 5% or above 50%."""
    # Generate a low installment (below 5%)
    low_installment = st.floats(
        min_value=0.01, max_value=4.99, allow_nan=False, allow_infinity=False
    )
    # Generate a high installment (above 50%)
    high_installment = st.floats(
        min_value=50.01, max_value=95.0, allow_nan=False, allow_infinity=False
    )

    # Pick either a too-low or too-high value paired with complements
    return st.one_of(
        # Case 1: One installment too low, rest fill to 100%
        low_installment.flatmap(
            lambda low: st.just([low, 100.0 - low])
            if 5.0 <= (100.0 - low) <= 50.0
            else st.just([low, 50.0, 50.0 - low])
        ),
        # Case 2: One installment too high
        high_installment.flatmap(
            lambda high: st.just([high, 100.0 - high])
        ),
    )


# Strategy for valid penalty rates
valid_penalty_rate_strategy = st.floats(
    min_value=PENALTY_RATE_MIN_PERCENT,
    max_value=PENALTY_RATE_MAX_PERCENT,
    allow_nan=False,
    allow_infinity=False,
)

# Strategy for invalid penalty rates (too low)
invalid_penalty_rate_low_strategy = st.floats(
    min_value=0.0,
    max_value=PENALTY_RATE_MIN_PERCENT,
    allow_nan=False,
    allow_infinity=False,
    exclude_max=True,
)

# Strategy for invalid penalty rates (too high)
invalid_penalty_rate_high_strategy = st.floats(
    min_value=PENALTY_RATE_MAX_PERCENT,
    max_value=1.0,
    allow_nan=False,
    allow_infinity=False,
    exclude_min=True,
)


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestPaymentSchedulePercentageInvariant:
    """Property 3: Payment Schedule Percentage Invariant.

    For any TOR document that passes Rule Engine validation, the sum of all
    payment installment percentages SHALL equal exactly 100%, each installment
    SHALL be between 5% and 50% inclusive, and the penalty rate SHALL be
    between 0.01% and 0.20% per day.
    """

    @given(installments=_valid_installments_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_valid_schedule_passes_rule_engine(self, installments: list[float]):
        """For any valid payment schedule (sum=100%, each 5%–50%), validation passes.

        **Validates: Requirements 6.3, 6.8**
        """
        rule = PaymentScheduleRule()
        doc = {"payment_installments": installments}
        findings = rule.validate(doc)

        # A valid schedule should produce no findings
        assert findings == [], (
            f"Valid schedule {installments} (sum={sum(installments):.4f}) "
            f"produced unexpected findings: {[f.rule_violated for f in findings]}"
        )

    @given(installments=_valid_installments_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_valid_schedule_satisfies_invariants(self, installments: list[float]):
        """For any schedule generated as valid, the mathematical invariants hold.

        Confirms:
        - sum(installments) == 100% (within tolerance)
        - all(5% <= p <= 50%) for each installment

        **Validates: Requirements 6.3, 6.8**
        """
        assert abs(sum(installments) - 100.0) <= SUM_TOLERANCE, (
            f"Sum {sum(installments)} deviates from 100% beyond tolerance {SUM_TOLERANCE}"
        )
        for i, pct in enumerate(installments):
            assert MIN_INSTALLMENT_PERCENT <= pct <= MAX_INSTALLMENT_PERCENT, (
                f"Installment {i+1} = {pct}% is outside [{MIN_INSTALLMENT_PERCENT}, {MAX_INSTALLMENT_PERCENT}]"
            )

    @given(installments=_valid_installments_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_valid_schedule_integrated_with_engine(self, installments: list[float]):
        """For any valid payment schedule, full Rule Engine validation passes with no payment errors.

        **Validates: Requirements 6.3, 6.8**
        """
        engine = RuleEngine()
        engine.register_rule("legal", PaymentScheduleRule())

        doc = {"payment_installments": installments}
        result = engine.validate(doc)

        # No payment-related findings should be present
        payment_findings = [
            f for f in result.findings
            if f.rule_violated.startswith("PAYMENT_")
        ]
        assert payment_findings == [], (
            f"Valid schedule produced payment findings: "
            f"{[(f.rule_violated, f.message) for f in payment_findings]}"
        )

    @given(installments=_invalid_sum_installments_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_invalid_sum_rejected_by_rule_engine(self, installments: list[float]):
        """For any schedule where sum ≠ 100%, Rule Engine produces PAYMENT_SUM_NOT_100 error.

        **Validates: Requirements 6.3, 6.8**
        """
        rule = PaymentScheduleRule()
        doc = {"payment_installments": installments}
        findings = rule.validate(doc)

        sum_findings = [f for f in findings if f.rule_violated == "PAYMENT_SUM_NOT_100"]
        assert len(sum_findings) == 1, (
            f"Schedule with sum={sum(installments):.4f}% should produce "
            f"exactly one PAYMENT_SUM_NOT_100 finding"
        )
        assert sum_findings[0].severity == Severity.ERROR

    @given(
        low_pct=st.floats(
            min_value=0.01, max_value=4.99, allow_nan=False, allow_infinity=False
        ),
        num_others=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_installment_below_5_percent_rejected(self, low_pct: float, num_others: int):
        """For any installment below 5%, Rule Engine produces PAYMENT_INSTALLMENT_TOO_LOW error.

        **Validates: Requirements 6.3, 6.8**
        """
        # Build a schedule with one too-low installment
        remaining = 100.0 - low_pct
        # Distribute remaining across other installments (may not all be valid, that's OK)
        others = [remaining / num_others] * num_others
        installments = [low_pct] + others

        rule = PaymentScheduleRule()
        doc = {"payment_installments": installments}
        findings = rule.validate(doc)

        too_low_findings = [
            f for f in findings if f.rule_violated == "PAYMENT_INSTALLMENT_TOO_LOW"
        ]
        assert len(too_low_findings) >= 1, (
            f"Schedule with installment {low_pct:.2f}% (< 5%) should be rejected"
        )

    @given(
        high_pct=st.floats(
            min_value=50.01, max_value=95.0, allow_nan=False, allow_infinity=False
        ),
    )
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_installment_above_50_percent_rejected(self, high_pct: float):
        """For any installment above 50%, Rule Engine produces PAYMENT_INSTALLMENT_TOO_HIGH error.

        **Validates: Requirements 6.3, 6.8**
        """
        # Pair with a complement to make sum close to 100%
        complement = 100.0 - high_pct
        installments = [high_pct, complement]

        rule = PaymentScheduleRule()
        doc = {"payment_installments": installments}
        findings = rule.validate(doc)

        too_high_findings = [
            f for f in findings if f.rule_violated == "PAYMENT_INSTALLMENT_TOO_HIGH"
        ]
        assert len(too_high_findings) >= 1, (
            f"Schedule with installment {high_pct:.2f}% (> 50%) should be rejected"
        )

    @given(rate=valid_penalty_rate_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_valid_penalty_rate_passes(self, rate: float):
        """For any penalty rate within [0.01%, 0.20%], validation passes.

        **Validates: Requirements 6.3, 6.8**
        """
        assert validate_penalty_rate(rate) is True, (
            f"Penalty rate {rate}% should be valid (within [{PENALTY_RATE_MIN_PERCENT}, {PENALTY_RATE_MAX_PERCENT}])"
        )

    @given(rate=valid_penalty_rate_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_valid_penalty_rate_no_findings_in_rule(self, rate: float):
        """For any valid penalty rate, PenaltyRateRule produces no rate-related findings.

        **Validates: Requirements 6.3, 6.8**
        """
        rule = PenaltyRateRule()
        doc = {
            "penalty_rate_percent": rate,
            "s10": "ค่าปรับตามสัญญา",
        }
        findings = rule.validate(doc)

        rate_findings = [
            f for f in findings
            if f.rule_violated in ("LEGAL_PENALTY_RATE_TOO_LOW", "LEGAL_PENALTY_RATE_TOO_HIGH")
        ]
        assert rate_findings == [], (
            f"Penalty rate {rate}% should produce no rate findings, got: "
            f"{[f.rule_violated for f in rate_findings]}"
        )

    @given(rate=invalid_penalty_rate_low_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_penalty_rate_below_minimum_rejected(self, rate: float):
        """For any penalty rate below 0.01%, validation fails.

        **Validates: Requirements 6.3, 6.8**
        """
        assert validate_penalty_rate(rate) is False, (
            f"Penalty rate {rate}% should be invalid (below {PENALTY_RATE_MIN_PERCENT}%)"
        )

    @given(rate=invalid_penalty_rate_high_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_penalty_rate_above_maximum_rejected(self, rate: float):
        """For any penalty rate above 0.20%, validation fails.

        **Validates: Requirements 6.3, 6.8**
        """
        assert validate_penalty_rate(rate) is False, (
            f"Penalty rate {rate}% should be invalid (above {PENALTY_RATE_MAX_PERCENT}%)"
        )

    @given(rate=invalid_penalty_rate_low_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_penalty_rate_below_minimum_produces_finding(self, rate: float):
        """For any penalty rate below 0.01%, PenaltyRateRule produces LEGAL_PENALTY_RATE_TOO_LOW.

        **Validates: Requirements 6.3, 6.8**
        """
        rule = PenaltyRateRule()
        doc = {
            "penalty_rate_percent": rate,
            "s10": "ค่าปรับตามสัญญา",
        }
        findings = rule.validate(doc)

        low_findings = [
            f for f in findings if f.rule_violated == "LEGAL_PENALTY_RATE_TOO_LOW"
        ]
        assert len(low_findings) == 1, (
            f"Penalty rate {rate}% should produce LEGAL_PENALTY_RATE_TOO_LOW"
        )
        assert low_findings[0].severity == Severity.ERROR

    @given(rate=invalid_penalty_rate_high_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_penalty_rate_above_maximum_produces_finding(self, rate: float):
        """For any penalty rate above 0.20%, PenaltyRateRule produces LEGAL_PENALTY_RATE_TOO_HIGH.

        **Validates: Requirements 6.3, 6.8**
        """
        rule = PenaltyRateRule()
        doc = {
            "penalty_rate_percent": rate,
            "s10": "ค่าปรับตามสัญญา",
        }
        findings = rule.validate(doc)

        high_findings = [
            f for f in findings if f.rule_violated == "LEGAL_PENALTY_RATE_TOO_HIGH"
        ]
        assert len(high_findings) == 1, (
            f"Penalty rate {rate}% should produce LEGAL_PENALTY_RATE_TOO_HIGH"
        )
        assert high_findings[0].severity == Severity.ERROR

    @given(
        installments=_valid_installments_strategy(),
        rate=valid_penalty_rate_strategy,
    )
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 3: Payment Schedule Percentage Invariant
    def test_combined_valid_schedule_and_penalty_passes_engine(
        self, installments: list[float], rate: float
    ):
        """For any valid payment schedule AND valid penalty rate, full engine validation passes.

        **Validates: Requirements 6.3, 6.8**
        """
        engine = RuleEngine()
        engine.register_rule("legal", PaymentScheduleRule())
        engine.register_rule("legal", PenaltyRateRule())

        doc = {
            "payment_installments": installments,
            "penalty_rate_percent": rate,
            "s10": "อัตราค่าปรับตามสัญญา",
        }
        result = engine.validate(doc)

        # No payment or penalty-rate findings
        relevant_findings = [
            f for f in result.findings
            if f.rule_violated.startswith("PAYMENT_")
            or f.rule_violated in ("LEGAL_PENALTY_RATE_TOO_LOW", "LEGAL_PENALTY_RATE_TOO_HIGH")
        ]
        assert relevant_findings == [], (
            f"Valid schedule+penalty produced findings: "
            f"{[(f.rule_violated, f.message) for f in relevant_findings]}"
        )
        # Score should be 100 (no deductions)
        assert result.quality_score == 100
        assert result.is_valid is True
