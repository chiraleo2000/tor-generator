"""Property-based tests for Vendor Capital Calculation (Property 4).

Verifies that for any positive integer budget, the vendor paid-up capital
requirement is computed as floor(budget / 4) and that the VendorPaidUpCapitalRule
correctly validates matching and non-matching capital values.

**Validates: Requirements 6.2**

# Feature: tor-drafting-review-app, Property 4: Vendor Capital Calculation
"""

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.rule_engine.engine import Severity
from app.rule_engine.rules.legal import VendorPaidUpCapitalRule, compute_vendor_capital


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Budget range: 1 baht to 10 billion baht (10,000,000,000)
positive_budget_strategy = st.integers(min_value=1, max_value=10_000_000_000)


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestVendorCapitalCalculation:
    """Property 4: Vendor Capital Calculation.

    For any positive integer budget value, the computed vendor paid-up capital
    requirement SHALL equal floor(budget / 4) — the Rule Engine output for this
    field is a pure function of budget input.
    """

    @given(budget=positive_budget_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 4: Vendor Capital Calculation
    def test_compute_vendor_capital_equals_floor_budget_div_4(self, budget: int):
        """For any positive budget, compute_vendor_capital(budget) == budget // 4.

        **Validates: Requirements 6.2**
        """
        result = compute_vendor_capital(budget)
        assert result == budget // 4

    @given(budget=positive_budget_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 4: Vendor Capital Calculation
    def test_compute_vendor_capital_result_is_integer(self, budget: int):
        """For any positive budget, the result is always an integer.

        **Validates: Requirements 6.2**
        """
        result = compute_vendor_capital(budget)
        assert isinstance(result, int)

    @given(budget=positive_budget_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 4: Vendor Capital Calculation
    def test_compute_vendor_capital_consistent_with_math_floor(self, budget: int):
        """For any positive budget, result equals math.floor(budget / 4).

        This verifies equivalence between integer division and explicit floor.

        **Validates: Requirements 6.2**
        """
        result = compute_vendor_capital(budget)
        assert result == math.floor(budget / 4)

    @given(budget=positive_budget_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 4: Vendor Capital Calculation
    def test_rule_produces_no_findings_when_capital_matches(self, budget: int):
        """VendorPaidUpCapitalRule produces no findings when vendor_capital
        matches floor(budget / 4).

        **Validates: Requirements 6.2**
        """
        expected_capital = budget // 4
        tor_document = {
            "budget": budget,
            "vendor_capital": expected_capital,
        }

        rule = VendorPaidUpCapitalRule()
        findings = rule.validate(tor_document)

        # No error or warning findings when capital matches
        assert len(findings) == 0

    @given(budget=positive_budget_strategy)
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 4: Vendor Capital Calculation
    def test_rule_produces_error_when_capital_does_not_match(self, budget: int):
        """VendorPaidUpCapitalRule produces errors when vendor_capital does NOT
        match floor(budget / 4).

        **Validates: Requirements 6.2**
        """
        expected_capital = budget // 4
        # Use an incorrect value that is guaranteed to differ
        wrong_capital = expected_capital + 1

        tor_document = {
            "budget": budget,
            "vendor_capital": wrong_capital,
        }

        rule = VendorPaidUpCapitalRule()
        findings = rule.validate(tor_document)

        # Must produce at least one finding
        assert len(findings) > 0
        # The finding must be an error about capital mismatch
        assert any(f.severity == Severity.ERROR for f in findings)
        assert any("LEGAL_CAPITAL_MISMATCH" in f.rule_violated for f in findings)
