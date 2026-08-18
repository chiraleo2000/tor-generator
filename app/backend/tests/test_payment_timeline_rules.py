"""Unit tests for payment schedule and timeline feasibility validation rules.

Tests cover:
- PaymentScheduleRule:
  - Valid schedules pass without findings
  - Sum != 100% produces ERROR
  - Individual installment < 5% produces ERROR
  - Individual installment > 50% produces ERROR
  - Multiple violations produce multiple findings
  - Missing payment_installments is silently skipped
  - Empty installments list produces ERROR
  - Edge cases (exactly 5%, exactly 50%, boundary sums)

- TimelineFeasibilityRule:
  - Valid timelines pass without findings
  - Budget > 100M with < 180 days produces ERROR
  - Budget < 10M with > 365 days produces WARNING
  - Boundary values (exactly at thresholds)
  - Missing budget or timeline_days is silently skipped
  - Budget in middle range has no timeline constraints

- Integration with RuleEngine:
  - Rules register under "legal" category
  - Combined scoring works correctly
"""

from __future__ import annotations

import pytest

from app.rule_engine.engine import Finding, RuleEngine, Severity
from app.rule_engine.rules.payment import (
    MAX_INSTALLMENT_PERCENT,
    MIN_INSTALLMENT_PERCENT,
    SUM_TOLERANCE,
    PaymentScheduleRule,
)
from app.rule_engine.rules.timeline import (
    HIGH_BUDGET_MIN_DAYS,
    HIGH_BUDGET_THRESHOLD,
    LOW_BUDGET_MAX_DAYS,
    LOW_BUDGET_THRESHOLD,
    TimelineFeasibilityRule,
)


# --- Fixtures ---


@pytest.fixture
def payment_rule() -> PaymentScheduleRule:
    """Create a PaymentScheduleRule instance."""
    return PaymentScheduleRule()


@pytest.fixture
def timeline_rule() -> TimelineFeasibilityRule:
    """Create a TimelineFeasibilityRule instance."""
    return TimelineFeasibilityRule()


@pytest.fixture
def engine_with_rules() -> RuleEngine:
    """Create a RuleEngine with payment and timeline rules registered."""
    engine = RuleEngine()
    engine.register_rule("legal", PaymentScheduleRule())
    engine.register_rule("legal", TimelineFeasibilityRule())
    return engine


# ===========================================================================
# PaymentScheduleRule Tests
# ===========================================================================


class TestPaymentScheduleRuleValid:
    """Test that valid payment schedules produce no findings."""

    def test_two_equal_installments(self, payment_rule: PaymentScheduleRule):
        """Two installments of 50% each (sum=100%, each within 5-50%)."""
        doc = {"payment_installments": [50.0, 50.0]}
        findings = payment_rule.validate(doc)
        assert findings == []

    def test_four_equal_installments(self, payment_rule: PaymentScheduleRule):
        """Four installments of 25% each."""
        doc = {"payment_installments": [25.0, 25.0, 25.0, 25.0]}
        findings = payment_rule.validate(doc)
        assert findings == []

    def test_three_installments_varying(self, payment_rule: PaymentScheduleRule):
        """Three installments: 30% + 30% + 40% = 100%."""
        doc = {"payment_installments": [30.0, 30.0, 40.0]}
        findings = payment_rule.validate(doc)
        assert findings == []

    def test_minimum_installment_5_percent(self, payment_rule: PaymentScheduleRule):
        """Exactly 5% is the minimum allowed per installment."""
        doc = {"payment_installments": [5.0, 45.0, 50.0]}
        findings = payment_rule.validate(doc)
        assert findings == []

    def test_maximum_installment_50_percent(self, payment_rule: PaymentScheduleRule):
        """Exactly 50% is the maximum allowed per installment."""
        doc = {"payment_installments": [50.0, 50.0]}
        findings = payment_rule.validate(doc)
        assert findings == []

    def test_many_small_installments(self, payment_rule: PaymentScheduleRule):
        """20 installments of 5% each (sum=100%)."""
        doc = {"payment_installments": [5.0] * 20}
        findings = payment_rule.validate(doc)
        assert findings == []

    def test_sum_within_tolerance(self, payment_rule: PaymentScheduleRule):
        """Sum that's within SUM_TOLERANCE of 100% is accepted."""
        # 33.33 + 33.33 + 33.34 = 100.00 exactly
        doc = {"payment_installments": [33.33, 33.33, 33.34]}
        findings = payment_rule.validate(doc)
        assert findings == []


class TestPaymentScheduleSumErrors:
    """Test that incorrect sums produce ERROR findings."""

    def test_sum_below_100(self, payment_rule: PaymentScheduleRule):
        """Installments summing to less than 100% produces ERROR."""
        doc = {"payment_installments": [30.0, 30.0, 30.0]}  # sum=90%
        findings = payment_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].rule_violated == "PAYMENT_SUM_NOT_100"
        assert findings[0].affected_section == "s8"

    def test_sum_above_100(self, payment_rule: PaymentScheduleRule):
        """Installments summing to more than 100% produces ERROR."""
        doc = {"payment_installments": [40.0, 40.0, 30.0]}  # sum=110%
        findings = payment_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].rule_violated == "PAYMENT_SUM_NOT_100"

    def test_sum_slightly_off(self, payment_rule: PaymentScheduleRule):
        """Sum that's outside tolerance of 100% is flagged."""
        # 99.98 is 0.02 away from 100.0, which exceeds SUM_TOLERANCE of 0.01
        doc = {"payment_installments": [49.99, 49.99]}  # sum=99.98
        findings = payment_rule.validate(doc)
        sum_finding = [f for f in findings if f.rule_violated == "PAYMENT_SUM_NOT_100"]
        assert len(sum_finding) == 1


class TestPaymentScheduleInstallmentRange:
    """Test individual installment range checks."""

    def test_installment_below_5_percent(self, payment_rule: PaymentScheduleRule):
        """An installment below 5% produces ERROR."""
        doc = {"payment_installments": [4.0, 46.0, 50.0]}  # 4% < 5%
        findings = payment_rule.validate(doc)
        too_low = [f for f in findings if f.rule_violated == "PAYMENT_INSTALLMENT_TOO_LOW"]
        assert len(too_low) == 1
        assert "งวดที่ 1" in too_low[0].message

    def test_installment_above_50_percent(self, payment_rule: PaymentScheduleRule):
        """An installment above 50% produces ERROR."""
        doc = {"payment_installments": [51.0, 49.0]}  # 51% > 50%
        findings = payment_rule.validate(doc)
        too_high = [f for f in findings if f.rule_violated == "PAYMENT_INSTALLMENT_TOO_HIGH"]
        assert len(too_high) == 1
        assert "งวดที่ 1" in too_high[0].message

    def test_multiple_installments_below_5_percent(self, payment_rule: PaymentScheduleRule):
        """Multiple low installments produce one ERROR each."""
        doc = {"payment_installments": [3.0, 2.0, 45.0, 50.0]}  # sum=100%, two too low
        findings = payment_rule.validate(doc)
        too_low = [f for f in findings if f.rule_violated == "PAYMENT_INSTALLMENT_TOO_LOW"]
        assert len(too_low) == 2

    def test_multiple_installments_above_50_percent(self, payment_rule: PaymentScheduleRule):
        """Multiple high installments produce one ERROR each (sum likely > 100%)."""
        doc = {"payment_installments": [51.0, 51.0]}  # both > 50%, sum > 100%
        findings = payment_rule.validate(doc)
        too_high = [f for f in findings if f.rule_violated == "PAYMENT_INSTALLMENT_TOO_HIGH"]
        assert len(too_high) == 2

    def test_installment_exactly_at_boundaries(self, payment_rule: PaymentScheduleRule):
        """Exactly 5% and 50% should NOT produce findings (inclusive boundaries)."""
        doc = {"payment_installments": [5.0, 45.0, 50.0]}
        findings = payment_rule.validate(doc)
        range_findings = [
            f
            for f in findings
            if f.rule_violated
            in ("PAYMENT_INSTALLMENT_TOO_LOW", "PAYMENT_INSTALLMENT_TOO_HIGH")
        ]
        assert range_findings == []


class TestPaymentScheduleMissingData:
    """Test behavior when payment data is missing or empty."""

    def test_no_payment_installments_key(self, payment_rule: PaymentScheduleRule):
        """Missing payment_installments key is silently skipped."""
        doc = {"budget": 5_000_000}
        findings = payment_rule.validate(doc)
        assert findings == []

    def test_payment_installments_none(self, payment_rule: PaymentScheduleRule):
        """payment_installments set to None is silently skipped."""
        doc = {"payment_installments": None}
        findings = payment_rule.validate(doc)
        assert findings == []

    def test_payment_installments_empty_list(self, payment_rule: PaymentScheduleRule):
        """Empty installments list produces ERROR."""
        doc = {"payment_installments": []}
        findings = payment_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].rule_violated == "PAYMENT_SCHEDULE_EMPTY"
        assert findings[0].severity == Severity.ERROR


class TestPaymentScheduleCombinedErrors:
    """Test that multiple types of errors are all reported."""

    def test_sum_and_range_errors_combined(self, payment_rule: PaymentScheduleRule):
        """Both sum error and range error reported when both present."""
        doc = {"payment_installments": [3.0, 55.0, 30.0]}  # sum=88%, low, high
        findings = payment_rule.validate(doc)
        rule_violations = {f.rule_violated for f in findings}
        assert "PAYMENT_SUM_NOT_100" in rule_violations
        assert "PAYMENT_INSTALLMENT_TOO_LOW" in rule_violations
        assert "PAYMENT_INSTALLMENT_TOO_HIGH" in rule_violations


# ===========================================================================
# TimelineFeasibilityRule Tests
# ===========================================================================


class TestTimelineRuleValid:
    """Test that valid timeline/budget combinations produce no findings."""

    def test_high_budget_with_sufficient_duration(self, timeline_rule: TimelineFeasibilityRule):
        """Budget > 100M with >= 180 days passes."""
        doc = {"budget": 150_000_000, "timeline_days": 200}
        findings = timeline_rule.validate(doc)
        assert findings == []

    def test_high_budget_exactly_180_days(self, timeline_rule: TimelineFeasibilityRule):
        """Budget > 100M with exactly 180 days passes (inclusive boundary)."""
        doc = {"budget": 150_000_000, "timeline_days": 180}
        findings = timeline_rule.validate(doc)
        assert findings == []

    def test_low_budget_with_short_duration(self, timeline_rule: TimelineFeasibilityRule):
        """Budget < 10M with <= 365 days passes."""
        doc = {"budget": 5_000_000, "timeline_days": 200}
        findings = timeline_rule.validate(doc)
        assert findings == []

    def test_low_budget_exactly_365_days(self, timeline_rule: TimelineFeasibilityRule):
        """Budget < 10M with exactly 365 days passes (inclusive boundary)."""
        doc = {"budget": 5_000_000, "timeline_days": 365}
        findings = timeline_rule.validate(doc)
        assert findings == []

    def test_mid_range_budget_any_duration(self, timeline_rule: TimelineFeasibilityRule):
        """Budget between 10M and 100M has no timeline constraints."""
        doc = {"budget": 50_000_000, "timeline_days": 30}
        findings = timeline_rule.validate(doc)
        assert findings == []

    def test_mid_range_budget_long_duration(self, timeline_rule: TimelineFeasibilityRule):
        """Budget between 10M and 100M with long duration also passes."""
        doc = {"budget": 50_000_000, "timeline_days": 1000}
        findings = timeline_rule.validate(doc)
        assert findings == []

    def test_exactly_100m_budget_short_duration(self, timeline_rule: TimelineFeasibilityRule):
        """Budget exactly at 100M (not exceeding) with short duration passes."""
        doc = {"budget": 100_000_000, "timeline_days": 30}
        findings = timeline_rule.validate(doc)
        assert findings == []

    def test_exactly_10m_budget_long_duration(self, timeline_rule: TimelineFeasibilityRule):
        """Budget exactly at 10M (not less than) with long duration passes."""
        doc = {"budget": 10_000_000, "timeline_days": 500}
        findings = timeline_rule.validate(doc)
        assert findings == []


class TestTimelineHighBudgetTooShort:
    """Test that high-budget projects with short timelines are flagged."""

    def test_over_100m_under_180_days(self, timeline_rule: TimelineFeasibilityRule):
        """Budget > 100M with < 180 days produces ERROR."""
        doc = {"budget": 200_000_000, "timeline_days": 90}
        findings = timeline_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].rule_violated == "TIMELINE_TOO_SHORT_FOR_BUDGET"
        assert findings[0].affected_section == "s5"

    def test_just_over_100m_179_days(self, timeline_rule: TimelineFeasibilityRule):
        """Budget barely over 100M with 179 days (just under 180) produces ERROR."""
        doc = {"budget": 100_000_001, "timeline_days": 179}
        findings = timeline_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].rule_violated == "TIMELINE_TOO_SHORT_FOR_BUDGET"

    def test_very_high_budget_1_day(self, timeline_rule: TimelineFeasibilityRule):
        """1 billion baht with 1 day duration produces ERROR."""
        doc = {"budget": 1_000_000_000, "timeline_days": 1}
        findings = timeline_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_error_message_contains_budget_and_days(
        self, timeline_rule: TimelineFeasibilityRule
    ):
        """Error message includes both budget amount and timeline days."""
        doc = {"budget": 200_000_000, "timeline_days": 90}
        findings = timeline_rule.validate(doc)
        assert "200,000,000" in findings[0].message
        assert "90" in findings[0].message

    def test_recommended_correction_provided(self, timeline_rule: TimelineFeasibilityRule):
        """Finding includes a recommended correction."""
        doc = {"budget": 200_000_000, "timeline_days": 90}
        findings = timeline_rule.validate(doc)
        assert findings[0].recommended_correction is not None
        assert "180" in findings[0].recommended_correction


class TestTimelineLowBudgetTooLong:
    """Test that low-budget projects with long timelines are flagged."""

    def test_under_10m_over_365_days(self, timeline_rule: TimelineFeasibilityRule):
        """Budget < 10M with > 365 days produces WARNING."""
        doc = {"budget": 5_000_000, "timeline_days": 400}
        findings = timeline_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert findings[0].rule_violated == "TIMELINE_TOO_LONG_FOR_BUDGET"
        assert findings[0].affected_section == "s5"

    def test_just_under_10m_366_days(self, timeline_rule: TimelineFeasibilityRule):
        """Budget barely under 10M with 366 days (just over 365) produces WARNING."""
        doc = {"budget": 9_999_999, "timeline_days": 366}
        findings = timeline_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].rule_violated == "TIMELINE_TOO_LONG_FOR_BUDGET"

    def test_very_low_budget_very_long_duration(self, timeline_rule: TimelineFeasibilityRule):
        """Very low budget with very long duration produces WARNING."""
        doc = {"budget": 100_000, "timeline_days": 730}
        findings = timeline_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_warning_severity_not_error(self, timeline_rule: TimelineFeasibilityRule):
        """Low budget / long duration is WARNING, not ERROR."""
        doc = {"budget": 5_000_000, "timeline_days": 500}
        findings = timeline_rule.validate(doc)
        assert findings[0].severity == Severity.WARNING


class TestTimelineMissingData:
    """Test behavior when budget or timeline data is missing."""

    def test_no_budget_key(self, timeline_rule: TimelineFeasibilityRule):
        """Missing budget key is silently skipped."""
        doc = {"timeline_days": 90}
        findings = timeline_rule.validate(doc)
        assert findings == []

    def test_no_timeline_days_key(self, timeline_rule: TimelineFeasibilityRule):
        """Missing timeline_days key is silently skipped."""
        doc = {"budget": 200_000_000}
        findings = timeline_rule.validate(doc)
        assert findings == []

    def test_both_missing(self, timeline_rule: TimelineFeasibilityRule):
        """Both keys missing is silently skipped."""
        doc = {"s1": "content"}
        findings = timeline_rule.validate(doc)
        assert findings == []

    def test_budget_none(self, timeline_rule: TimelineFeasibilityRule):
        """Budget set to None is silently skipped."""
        doc = {"budget": None, "timeline_days": 90}
        findings = timeline_rule.validate(doc)
        assert findings == []

    def test_timeline_days_none(self, timeline_rule: TimelineFeasibilityRule):
        """timeline_days set to None is silently skipped."""
        doc = {"budget": 200_000_000, "timeline_days": None}
        findings = timeline_rule.validate(doc)
        assert findings == []


# ===========================================================================
# Integration with RuleEngine
# ===========================================================================


class TestRuleEngineIntegration:
    """Test payment and timeline rules integrated with the RuleEngine."""

    def test_valid_document_no_deductions(self, engine_with_rules: RuleEngine):
        """A valid document scores 100 with no legal findings."""
        doc = {
            "budget": 50_000_000,
            "timeline_days": 200,
            "payment_installments": [25.0, 25.0, 25.0, 25.0],
        }
        result = engine_with_rules.validate(doc)
        assert result.quality_score == 100
        assert result.is_valid is True
        assert len(result.findings) == 0

    def test_payment_error_affects_legal_score(self, engine_with_rules: RuleEngine):
        """Payment violation deducts from legal category (40% weight)."""
        doc = {
            "budget": 50_000_000,
            "timeline_days": 200,
            "payment_installments": [30.0, 30.0, 30.0],  # sum=90% → ERROR
        }
        result = engine_with_rules.validate(doc)
        legal = next(cs for cs in result.categories if cs.category == "legal")
        assert legal.score == 80.0  # 100 - 20 (one ERROR)
        # Total: 80*0.4 + 100*0.3 + 100*0.2 + 100*0.1 = 92
        assert result.quality_score == 92

    def test_timeline_error_affects_legal_score(self, engine_with_rules: RuleEngine):
        """Timeline violation deducts from legal category."""
        doc = {
            "budget": 200_000_000,
            "timeline_days": 90,  # > 100M but < 180 days → ERROR
            "payment_installments": [50.0, 50.0],
        }
        result = engine_with_rules.validate(doc)
        legal = next(cs for cs in result.categories if cs.category == "legal")
        assert legal.score == 80.0  # 100 - 20 (one ERROR)

    def test_timeline_warning_deducts_10(self, engine_with_rules: RuleEngine):
        """Timeline WARNING deducts 10 from legal category."""
        doc = {
            "budget": 5_000_000,
            "timeline_days": 400,  # < 10M but > 365 days → WARNING
            "payment_installments": [50.0, 50.0],
        }
        result = engine_with_rules.validate(doc)
        legal = next(cs for cs in result.categories if cs.category == "legal")
        assert legal.score == 90.0  # 100 - 10 (one WARNING)

    def test_combined_payment_and_timeline_errors(self, engine_with_rules: RuleEngine):
        """Both payment and timeline errors accumulate."""
        doc = {
            "budget": 200_000_000,
            "timeline_days": 90,  # ERROR: too short for budget
            "payment_installments": [60.0, 40.0],  # ERROR: 60% > 50%
        }
        result = engine_with_rules.validate(doc)
        legal = next(cs for cs in result.categories if cs.category == "legal")
        # Two ERRORs: -20 -20 = 60
        assert legal.score == 60.0


# ===========================================================================
# Constants verification
# ===========================================================================


class TestConstants:
    """Verify the rule constants match the design specification."""

    def test_payment_min_installment(self):
        """Minimum installment is 5%."""
        assert MIN_INSTALLMENT_PERCENT == 5.0

    def test_payment_max_installment(self):
        """Maximum installment is 50%."""
        assert MAX_INSTALLMENT_PERCENT == 50.0

    def test_high_budget_threshold(self):
        """High budget threshold is 100 million baht."""
        assert HIGH_BUDGET_THRESHOLD == 100_000_000

    def test_low_budget_threshold(self):
        """Low budget threshold is 10 million baht."""
        assert LOW_BUDGET_THRESHOLD == 10_000_000

    def test_high_budget_min_days(self):
        """High budget requires at least 180 days."""
        assert HIGH_BUDGET_MIN_DAYS == 180

    def test_low_budget_max_days(self):
        """Low budget should not exceed 365 days."""
        assert LOW_BUDGET_MAX_DAYS == 365
