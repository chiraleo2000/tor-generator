"""Property 8: quality score bounds. Property 7: payment installments sum to 100."""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from app.rule_engine.rules.payment import PaymentScheduleRule
from app.services.full_draft_generator import mean_quality

_SECTION_KEYS = [f"s{i}" for i in range(1, 14)]
_SCORE = st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False)


@pytest.mark.property
@settings(max_examples=40, deadline=None)
@given(st.dictionaries(st.sampled_from(_SECTION_KEYS), _SCORE, min_size=1, max_size=13))
def test_overall_quality_is_mean_and_bounded(scores: dict[str, float]):
    overall = mean_quality(scores)
    assert 0.0 <= overall <= 100.0
    expected = sum(scores.values()) / len(scores)
    assert abs(overall - expected) < 1e-6


def _valid_installments():
    return (
        st.integers(min_value=2, max_value=8)
        .flatmap(
            lambda n: st.lists(
                st.floats(min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False),
                min_size=n,
                max_size=n,
            )
        )
    )


@pytest.mark.property
@settings(max_examples=30, deadline=None)
@given(_valid_installments())
def test_valid_installments_sum_to_100(values: list[float]):
    total = sum(values)
    assume(total > 0)
    normalized = [round(v * 100.0 / total, 2) for v in values]
    drift = 100.0 - sum(normalized)
    normalized[-1] = round(normalized[-1] + drift, 2)
    assume(all(5.0 <= item <= 50.0 for item in normalized))
    assume(abs(sum(normalized) - 100.0) <= 0.01)
    findings = PaymentScheduleRule().validate(
        {"payment_installments": normalized, "s8": "งวด"}
    )
    assert findings == []
