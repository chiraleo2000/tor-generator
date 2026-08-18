"""Property-based tests for Orchestrator Retry Bound (Property 12).

Verifies that the orchestrator's retry mechanism is bounded and never enters
an infinite loop:
- For any max_retries value (1–10), the route_after_guardrail function
  always routes to human_review once retry_count >= max_retries
- For any sequence of guardrail failures, the orchestrator terminates
  after at most max_retries iterations
- The retry bound is enforced regardless of quality scores or findings

**Validates: Requirements 5.4, 5.5, 12.6**

# Feature: tor-drafting-review-app, Property 12: Orchestrator Retry Bound
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.orchestrator.graph import (
    DEFAULT_MAX_RETRIES,
    GUARDRAIL_THRESHOLD,
    route_after_guardrail,
)
from app.orchestrator.state import TORDraftState


# Strategies for generating test data
max_retries_strategy = st.integers(min_value=1, max_value=10)
retry_count_strategy = st.integers(min_value=0, max_value=20)
quality_score_strategy = st.integers(min_value=0, max_value=100)
section_key_strategy = st.sampled_from(
    ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11", "s12", "s13"]
)


@pytest.mark.property
class TestOrchestratorRetryBound:
    """Property 12: Orchestrator Retry Bound.

    For any agent invocation that fails Rule Engine validation, the Orchestrator
    SHALL invoke a maximum of max_retries retry attempts before presenting the
    best result with warnings — the system never enters an infinite retry loop.
    """

    @given(
        max_retries=max_retries_strategy,
        retry_count=retry_count_strategy,
    )
    @settings(max_examples=200)
    # Feature: tor-drafting-review-app, Property 12: Orchestrator Retry Bound
    def test_retry_bound_always_terminates_at_max(
        self, max_retries: int, retry_count: int
    ):
        """When retry_count >= max_retries, always routes to human_review.

        For any valid max_retries (1–10) and any retry_count that has reached
        or exceeded the limit, the routing function must always terminate the
        retry loop by routing to human_review instead of llm_draft.

        **Validates: Requirements 5.4, 5.5, 12.6**
        """
        if retry_count < max_retries:
            # Below the limit with guardrail_passed=False: should retry
            return

        # At or above the limit: must terminate (route to human_review)
        state: TORDraftState = {
            "guardrail_passed": False,
            "retry_count": retry_count,
            "max_retries": max_retries,
        }

        result = route_after_guardrail(state)
        assert result == "human_review", (
            f"Expected 'human_review' when retry_count={retry_count} >= "
            f"max_retries={max_retries}, but got '{result}'"
        )

    @given(
        max_retries=max_retries_strategy,
        retry_count=st.integers(min_value=0, max_value=9),
    )
    @settings(max_examples=200)
    # Feature: tor-drafting-review-app, Property 12: Orchestrator Retry Bound
    def test_retry_loop_only_continues_below_max(
        self, max_retries: int, retry_count: int
    ):
        """When retry_count < max_retries, routes to llm_draft (retry).

        The system only retries when still below the configured maximum.
        Once at or above, it never retries.

        **Validates: Requirements 5.4, 12.6**
        """
        if retry_count >= max_retries:
            # At or above the limit: should terminate, skip this case
            return

        # Below the limit with guardrail_passed=False: should retry
        state: TORDraftState = {
            "guardrail_passed": False,
            "retry_count": retry_count,
            "max_retries": max_retries,
        }

        result = route_after_guardrail(state)
        assert result == "llm_draft", (
            f"Expected 'llm_draft' when retry_count={retry_count} < "
            f"max_retries={max_retries}, but got '{result}'"
        )

    @given(
        max_retries=max_retries_strategy,
        quality_score=quality_score_strategy,
    )
    @settings(max_examples=200)
    # Feature: tor-drafting-review-app, Property 12: Orchestrator Retry Bound
    def test_guardrail_pass_always_routes_to_human_review(
        self, max_retries: int, quality_score: int
    ):
        """When guardrail_passed=True, always routes to human_review regardless of retries.

        A passing guardrail always terminates the retry loop early, no matter
        what the retry_count or quality_score values are.

        **Validates: Requirements 5.4, 5.5, 12.6**
        """
        state: TORDraftState = {
            "guardrail_passed": True,
            "retry_count": 0,
            "max_retries": max_retries,
            "quality_score": quality_score,
        }

        result = route_after_guardrail(state)
        assert result == "human_review", (
            f"Expected 'human_review' when guardrail_passed=True, "
            f"but got '{result}'"
        )

    @given(
        max_retries=max_retries_strategy,
        num_failures=st.integers(min_value=1, max_value=15),
    )
    @settings(max_examples=200)
    # Feature: tor-drafting-review-app, Property 12: Orchestrator Retry Bound
    def test_simulated_failure_sequence_terminates_within_bound(
        self, max_retries: int, num_failures: int
    ):
        """Simulating sequential failures always terminates within max_retries.

        For any max_retries and any sequence of consecutive guardrail failures,
        the number of times route_after_guardrail returns "llm_draft" (retry)
        is at most max_retries. The system always terminates — it never enters
        an infinite retry loop.

        The orchestrator allows exactly max_retries retry attempts (retry_count
        goes from 0 to max_retries-1 routing to llm_draft), then at
        retry_count == max_retries it routes to human_review.

        **Validates: Requirements 5.4, 5.5, 12.6**
        """
        retry_iterations = 0

        for attempt in range(num_failures):
            state: TORDraftState = {
                "guardrail_passed": False,
                "retry_count": attempt,
                "max_retries": max_retries,
            }

            result = route_after_guardrail(state)
            if result == "llm_draft":
                retry_iterations += 1
            else:
                # Terminated at human_review
                break

        # The number of retries must never exceed max_retries
        # (retry_count 0..max_retries-1 → llm_draft, retry_count >= max_retries → human_review)
        assert retry_iterations <= max_retries, (
            f"Expected at most {max_retries} retries, "
            f"but got {retry_iterations} with max_retries={max_retries}"
        )

        # The loop must have terminated (routed to human_review)
        # at exactly retry_count == max_retries
        if num_failures >= max_retries:
            final_state: TORDraftState = {
                "guardrail_passed": False,
                "retry_count": max_retries,
                "max_retries": max_retries,
            }
            assert route_after_guardrail(final_state) == "human_review"

    @given(
        max_retries=max_retries_strategy,
        section=section_key_strategy,
        quality_score=st.integers(min_value=0, max_value=GUARDRAIL_THRESHOLD - 1),
    )
    @settings(max_examples=200)
    # Feature: tor-drafting-review-app, Property 12: Orchestrator Retry Bound
    def test_max_retries_exhausted_terminates_regardless_of_score_or_section(
        self, max_retries: int, section: str, quality_score: int
    ):
        """At max retries, terminates regardless of section or score below threshold.

        The retry bound is universal — it applies equally to all sections,
        all quality scores below threshold, and all possible state combinations.
        Once max_retries is reached, the system always terminates.

        **Validates: Requirements 5.4, 5.5, 12.6**
        """
        state: TORDraftState = {
            "guardrail_passed": False,
            "retry_count": max_retries,
            "max_retries": max_retries,
            "target_section": section,
            "quality_score": quality_score,
        }

        result = route_after_guardrail(state)
        assert result == "human_review", (
            f"Expected 'human_review' at max retries for section={section}, "
            f"score={quality_score}, but got '{result}'"
        )
