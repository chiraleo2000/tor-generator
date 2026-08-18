"""Unit tests for task 10.4: Retry loop and human-in-the-loop breakpoints.

Tests verify:
1. Best-scoring draft tracking across retries
2. LangGraph interrupt configuration for human-in-the-loop
3. Configurable asyncio timeout for agent invocations
4. Retry bound enforcement and human review triggering

Requirements: 5.4, 5.5, 12.3, 12.5, 12.6, 12.7, 12.8, 12.9
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestrator.graph import (
    DEFAULT_MAX_RETRIES,
    GUARDRAIL_THRESHOLD,
    LLM_TIMEOUT_SECONDS,
    MANDATORY_HUMAN_REVIEW_SECTIONS,
    MAX_TIMEOUT_SECONDS,
    build_tor_drafting_graph,
    compile_tor_drafting_graph,
    human_review,
    llm_draft,
    route_after_guardrail,
    rule_guardrail,
    validate_input,
)
from app.orchestrator.state import TORDraftState

# =============================================================================
# Best-draft tracking tests
# =============================================================================


class TestBestDraftTracking:
    """Tests for best-scoring draft tracking across retries (Req 5.5)."""

    @pytest.mark.asyncio
    async def test_first_attempt_sets_best_draft(self):
        """First Rule Engine call sets best_draft fields."""
        mock_result = MagicMock(quality_score=45, findings=[])

        with patch("app.orchestrator.graph._create_rule_engine") as mock_create:
            mock_engine = MagicMock()
            mock_engine.validate.return_value = mock_result
            mock_create.return_value = mock_engine

            state: TORDraftState = {
                "target_section": "s1",
                "draft_content": "First attempt draft",
                "user_input": {},
                "draft_version": 1,
                "retry_count": 0,
                "max_retries": 3,
                "best_draft_content": None,
                "best_draft_score": -1.0,
                "best_draft_findings": [],
            }

            result = await rule_guardrail(state)

        assert result["best_draft_content"] == "First attempt draft"
        assert result["best_draft_score"] == 45
        assert result["best_draft_findings"] == []

    @pytest.mark.asyncio
    async def test_higher_scoring_draft_replaces_best(self):
        """A draft with a higher score replaces the previous best."""
        mock_result = MagicMock(quality_score=60, findings=[])

        with patch("app.orchestrator.graph._create_rule_engine") as mock_create:
            mock_engine = MagicMock()
            mock_engine.validate.return_value = mock_result
            mock_create.return_value = mock_engine

            state: TORDraftState = {
                "target_section": "s1",
                "draft_content": "Better draft",
                "user_input": {},
                "draft_version": 2,
                "retry_count": 1,
                "max_retries": 3,
                "best_draft_content": "First attempt draft",
                "best_draft_score": 45.0,
                "best_draft_findings": [{"severity": "error", "message": "old"}],
            }

            result = await rule_guardrail(state)

        assert result["best_draft_content"] == "Better draft"
        assert result["best_draft_score"] == 60
        assert result["best_draft_findings"] == []

    @pytest.mark.asyncio
    async def test_lower_scoring_draft_does_not_replace_best(self):
        """A draft with a lower score does NOT replace the best."""
        mock_result = MagicMock(quality_score=30, findings=[])

        with patch("app.orchestrator.graph._create_rule_engine") as mock_create:
            mock_engine = MagicMock()
            mock_engine.validate.return_value = mock_result
            mock_create.return_value = mock_engine

            state: TORDraftState = {
                "target_section": "s1",
                "draft_content": "Worse draft",
                "user_input": {},
                "draft_version": 3,
                "retry_count": 2,
                "max_retries": 3,
                "best_draft_content": "Better draft",
                "best_draft_score": 60.0,
                "best_draft_findings": [],
            }

            result = await rule_guardrail(state)

        assert result["best_draft_content"] == "Better draft"
        assert result["best_draft_score"] == 60.0

    @pytest.mark.asyncio
    async def test_human_review_presents_best_draft_when_retries_exhausted(self):
        """When retries exhausted and best > current, human_review uses best draft."""
        state: TORDraftState = {
            "target_section": "s1",
            "draft_content": "Last attempt (worse)",
            "quality_score": 40,
            "validation_findings": [{"severity": "error", "message": "bad"}],
            "retry_count": 3,
            "max_retries": 3,
            "guardrail_passed": False,
            "best_draft_content": "Best attempt (better)",
            "best_draft_score": 60.0,
            "best_draft_findings": [{"severity": "warning", "message": "minor"}],
            "human_approved": None,
            "human_feedback": None,
        }

        result = await human_review(state)

        # Should present the best draft
        assert result["draft_content"] == "Best attempt (better)"
        assert result["quality_score"] == 60.0
        assert result["validation_findings"] == [{"severity": "warning", "message": "minor"}]

    @pytest.mark.asyncio
    async def test_human_review_keeps_current_when_best_is_not_better(self):
        """When best score is not higher than current, keep the current draft."""
        state: TORDraftState = {
            "target_section": "s1",
            "draft_content": "Current draft",
            "quality_score": 65,
            "validation_findings": [],
            "retry_count": 3,
            "max_retries": 3,
            "guardrail_passed": False,
            "best_draft_content": "Best draft",
            "best_draft_score": 65.0,
            "best_draft_findings": [],
            "human_approved": None,
            "human_feedback": None,
        }

        result = await human_review(state)

        # Best is not strictly better, so keep current
        assert result["draft_content"] == "Current draft"

    @pytest.mark.asyncio
    async def test_human_review_no_best_draft_swap_when_guardrail_passed(self):
        """When guardrail passed, no best-draft swap logic applies."""
        state: TORDraftState = {
            "target_section": "s1",
            "draft_content": "Good draft",
            "quality_score": 85,
            "validation_findings": [],
            "retry_count": 1,
            "max_retries": 3,
            "guardrail_passed": True,
            "best_draft_content": "Some other draft",
            "best_draft_score": 90.0,
            "best_draft_findings": [],
            "human_approved": None,
            "human_feedback": None,
        }

        result = await human_review(state)

        # No swap because guardrail passed — present current draft as-is
        assert result.get("draft_content", state["draft_content"]) == "Good draft"


# =============================================================================
# Timeout configuration tests
# =============================================================================


class TestTimeoutConfiguration:
    """Tests for configurable asyncio timeout (Req 12.6, 12.8)."""

    @pytest.mark.asyncio
    async def test_validate_input_initializes_default_timeout(self):
        """Default timeout is 60 seconds when not specified."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"project_name": "Test"},
            "target_section": "s1",
        }

        result = await validate_input(state)

        assert result["agent_timeout_seconds"] == LLM_TIMEOUT_SECONDS

    @pytest.mark.asyncio
    async def test_validate_input_accepts_custom_timeout(self):
        """Custom timeout value is accepted within bounds."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"project_name": "Test"},
            "target_section": "s1",
            "agent_timeout_seconds": 120,
        }

        result = await validate_input(state)

        assert result["agent_timeout_seconds"] == 120

    @pytest.mark.asyncio
    async def test_validate_input_clamps_timeout_to_max(self):
        """Timeout is clamped to MAX_TIMEOUT_SECONDS (300)."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"project_name": "Test"},
            "target_section": "s1",
            "agent_timeout_seconds": 999,
        }

        result = await validate_input(state)

        assert result["agent_timeout_seconds"] == MAX_TIMEOUT_SECONDS

    @pytest.mark.asyncio
    async def test_validate_input_clamps_timeout_to_min(self):
        """Timeout is clamped to minimum of 1 second."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"project_name": "Test"},
            "target_section": "s1",
            "agent_timeout_seconds": 0,
        }

        result = await validate_input(state)

        assert result["agent_timeout_seconds"] == 1

    @pytest.mark.asyncio
    async def test_llm_draft_uses_asyncio_timeout(self):
        """LLM draft uses asyncio.wait_for with configured timeout."""

        async def slow_llm(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate slow LLM
            return MagicMock(content="should not reach here", usage={})

        with patch("app.providers.factory.ProviderFactory") as mock_factory_cls:
            mock_factory = MagicMock()
            mock_llm = MagicMock()
            mock_llm.invoke = slow_llm
            mock_factory.get_llm.return_value = mock_llm
            mock_factory_cls.return_value = mock_factory

            state: TORDraftState = {
                "target_section": "s1",
                "user_input": {"project_name": "Test"},
                "template": {},
                "rag_chunks": [],
                "retry_count": 0,
                "draft_version": 0,
                "agent_timeout_seconds": 1,  # 1 second timeout
            }

            result = await llm_draft(state)

        # Should have timed out and set error
        assert result["error"] is not None
        assert "timeout" in result["error"].lower()
        assert "1s" in result["error"]

    @pytest.mark.asyncio
    async def test_llm_draft_timeout_includes_agent_identifier(self):
        """Timeout error includes agent/section identifier (Req 12.8)."""

        async def slow_llm(*args, **kwargs):
            await asyncio.sleep(10)
            return MagicMock(content="x", usage={})

        with patch("app.providers.factory.ProviderFactory") as mock_factory_cls:
            mock_factory = MagicMock()
            mock_llm = MagicMock()
            mock_llm.invoke = slow_llm
            mock_factory.get_llm.return_value = mock_llm
            mock_factory_cls.return_value = mock_factory

            state: TORDraftState = {
                "target_section": "s3",
                "user_input": {"project_name": "Test"},
                "template": {},
                "rag_chunks": [],
                "retry_count": 0,
                "draft_version": 0,
                "agent_timeout_seconds": 1,
            }

            result = await llm_draft(state)

        assert "s3" in result["error"]
        assert "Agent" in result["error"] or "section" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_llm_draft_defaults_to_standard_timeout_when_not_set(self):
        """When agent_timeout_seconds not in state, uses LLM_TIMEOUT_SECONDS default."""

        async def slow_llm(*args, **kwargs):
            await asyncio.sleep(0.2)
            return MagicMock(content="completed", usage={"total_tokens": 100})

        with patch("app.providers.factory.ProviderFactory") as mock_factory_cls:
            mock_factory = MagicMock()
            mock_llm = MagicMock()
            mock_llm.invoke = slow_llm
            mock_factory.get_llm.return_value = mock_llm
            mock_factory_cls.return_value = mock_factory

            state: TORDraftState = {
                "target_section": "s1",
                "user_input": {"project_name": "Test"},
                "template": {},
                "rag_chunks": [],
                "retry_count": 0,
                "draft_version": 0,
                # agent_timeout_seconds not set, should use default
            }

            result = await llm_draft(state)

        # Should succeed since the LLM finishes in 0.2s (well under 60s default)
        assert result["draft_content"] == "completed"
        assert result.get("error") is None


# =============================================================================
# Retry bound enforcement tests
# =============================================================================


class TestRetryBoundEnforcement:
    """Tests verifying retry bound is enforced (Req 12.6, Property 12)."""

    def test_route_after_guardrail_retries_when_under_limit(self):
        """Routes to llm_draft when retry_count < max_retries."""
        state: TORDraftState = {
            "guardrail_passed": False,
            "retry_count": 1,
            "max_retries": 3,
        }
        assert route_after_guardrail(state) == "llm_draft"

    def test_route_after_guardrail_stops_at_max_retries(self):
        """Routes to human_review when retry_count >= max_retries."""
        state: TORDraftState = {
            "guardrail_passed": False,
            "retry_count": 3,
            "max_retries": 3,
        }
        assert route_after_guardrail(state) == "human_review"

    def test_route_after_guardrail_stops_at_exact_boundary(self):
        """Routes to human_review at exactly max_retries."""
        for max_r in [1, 3, 5, 10]:
            state: TORDraftState = {
                "guardrail_passed": False,
                "retry_count": max_r,
                "max_retries": max_r,
            }
            assert route_after_guardrail(state) == "human_review"

    def test_route_after_guardrail_stops_when_over_limit(self):
        """Routes to human_review when retry_count exceeds max_retries."""
        state: TORDraftState = {
            "guardrail_passed": False,
            "retry_count": 5,
            "max_retries": 3,
        }
        assert route_after_guardrail(state) == "human_review"

    @pytest.mark.asyncio
    async def test_max_retries_default_is_3(self):
        """Default max_retries is 3 (Req 12.6)."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"project_name": "Test"},
            "target_section": "s1",
        }

        result = await validate_input(state)

        assert result["max_retries"] == DEFAULT_MAX_RETRIES
        assert result["max_retries"] == 3

    @pytest.mark.asyncio
    async def test_max_retries_maximum_is_10(self):
        """max_retries cannot exceed 10 (Req 12.6)."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"project_name": "Test"},
            "target_section": "s1",
            "max_retries": 50,
        }

        result = await validate_input(state)

        assert result["max_retries"] == 10

    @pytest.mark.asyncio
    async def test_retry_count_increments_on_failure(self):
        """retry_count increments each time guardrail fails."""
        mock_result = MagicMock(quality_score=40, findings=[])

        with patch("app.orchestrator.graph._create_rule_engine") as mock_create:
            mock_engine = MagicMock()
            mock_engine.validate.return_value = mock_result
            mock_create.return_value = mock_engine

            state: TORDraftState = {
                "target_section": "s1",
                "draft_content": "content",
                "user_input": {},
                "draft_version": 1,
                "retry_count": 2,
                "max_retries": 5,
                "best_draft_content": None,
                "best_draft_score": -1.0,
                "best_draft_findings": [],
            }

            result = await rule_guardrail(state)

        assert result["retry_count"] == 3

    @pytest.mark.asyncio
    async def test_retry_count_not_incremented_on_pass(self):
        """retry_count stays the same when guardrail passes."""
        mock_result = MagicMock(quality_score=85, findings=[])

        with patch("app.orchestrator.graph._create_rule_engine") as mock_create:
            mock_engine = MagicMock()
            mock_engine.validate.return_value = mock_result
            mock_create.return_value = mock_engine

            state: TORDraftState = {
                "target_section": "s1",
                "draft_content": "good content",
                "user_input": {},
                "draft_version": 2,
                "retry_count": 1,
                "max_retries": 3,
                "best_draft_content": None,
                "best_draft_score": -1.0,
                "best_draft_findings": [],
            }

            result = await rule_guardrail(state)

        assert result["retry_count"] == 1  # Not incremented


# =============================================================================
# Human-in-the-loop trigger tests
# =============================================================================


class TestHumanInTheLoopTrigger:
    """Tests for mandatory human review triggering (Req 12.7)."""

    @pytest.mark.asyncio
    async def test_mandatory_sections_require_human_review(self):
        """Sections s3, s6, s8, s10, s13 must trigger human review."""
        expected_sections = {"s3", "s6", "s8", "s10", "s13"}
        assert MANDATORY_HUMAN_REVIEW_SECTIONS == expected_sections

        for section in expected_sections:
            state: TORDraftState = {
                "project_id": "proj-123",
                "user_input": {"project_name": "Test"},
                "target_section": section,
            }
            result = await validate_input(state)
            assert result["requires_human_review"] is True, (
                f"Section {section} should require mandatory human review"
            )

    @pytest.mark.asyncio
    async def test_non_mandatory_sections_skip_review_when_passed(self):
        """Non-mandatory sections (s1, s2, s4, etc.) don't force review."""
        non_mandatory = ["s1", "s2", "s4", "s5", "s7", "s9", "s11", "s12"]

        for section in non_mandatory:
            state: TORDraftState = {
                "project_id": "proj-123",
                "user_input": {"project_name": "Test"},
                "target_section": section,
            }
            result = await validate_input(state)
            assert result["requires_human_review"] is False, (
                f"Section {section} should NOT require mandatory human review"
            )

    @pytest.mark.asyncio
    async def test_three_failed_validations_routes_to_human_review(self):
        """3× failed validation routes to human_review regardless of section."""
        state: TORDraftState = {
            "guardrail_passed": False,
            "retry_count": 3,
            "max_retries": 3,
        }
        assert route_after_guardrail(state) == "human_review"

    def test_guardrail_threshold_is_70(self):
        """Guardrail threshold is 70 (0.7 * 100)."""
        assert GUARDRAIL_THRESHOLD == 70


# =============================================================================
# LangGraph interrupt configuration tests
# =============================================================================


class TestLangGraphInterrupt:
    """Tests for LangGraph interrupt at human_review node."""

    def test_compile_with_interrupt_before_human_review(self):
        """compile_tor_drafting_graph configures interrupt_before human_review."""
        # The compile function should not raise when setting interrupt_before
        compiled_graph = compile_tor_drafting_graph()
        # The compiled graph should exist and be functional
        assert compiled_graph is not None

    def test_graph_has_human_review_node(self):
        """The graph contains the human_review node for interrupt."""
        graph = build_tor_drafting_graph()
        # StateGraph's nodes dict contains all registered nodes
        assert "human_review" in graph.nodes


# =============================================================================
# Structured correction instructions on retry tests (Req 12.3)
# =============================================================================


class TestStructuredCorrectionInstructions:
    """Tests verifying Rule Engine feedback is passed as structured instructions."""

    @pytest.mark.asyncio
    async def test_retry_includes_validation_findings_in_llm_messages(self):
        """On retry (retry_count > 0), validation findings are passed to LLM."""
        mock_response = MagicMock(
            content="Corrected draft",
            usage={"total_tokens": 400},
        )

        with patch("app.providers.factory.ProviderFactory") as mock_factory_cls:
            mock_factory = MagicMock()
            mock_llm = AsyncMock()
            mock_llm.invoke = AsyncMock(return_value=mock_response)
            mock_factory.get_llm.return_value = mock_llm
            mock_factory_cls.return_value = mock_factory

            state: TORDraftState = {
                "target_section": "s1",
                "user_input": {"project_name": "Test"},
                "template": {},
                "rag_chunks": [],
                "retry_count": 1,  # Retry
                "draft_version": 1,
                "validation_findings": [
                    {
                        "severity": "error",
                        "message": "ไม่มีการอ้างอิง พ.ร.บ. 2560",
                        "recommended_correction": "เพิ่มการอ้างอิง",
                    }
                ],
                "agent_timeout_seconds": 60,
            }

            await llm_draft(state)

            # Check that the messages passed to LLM include the findings
            call_args = mock_llm.invoke.call_args
            messages = call_args.kwargs.get("messages") or call_args[0][0]

            # Find user message
            user_msg = next(m for m in messages if m["role"] == "user")
            assert "กรุณาแก้ไข" in user_msg["content"]
            assert "ไม่มีการอ้างอิง พ.ร.บ. 2560" in user_msg["content"]
            assert "เพิ่มการอ้างอิง" in user_msg["content"]

    @pytest.mark.asyncio
    async def test_first_attempt_does_not_include_findings(self):
        """On first attempt (retry_count=0), validation findings are NOT included."""
        mock_response = MagicMock(
            content="First draft",
            usage={"total_tokens": 300},
        )

        with patch("app.providers.factory.ProviderFactory") as mock_factory_cls:
            mock_factory = MagicMock()
            mock_llm = AsyncMock()
            mock_llm.invoke = AsyncMock(return_value=mock_response)
            mock_factory.get_llm.return_value = mock_llm
            mock_factory_cls.return_value = mock_factory

            state: TORDraftState = {
                "target_section": "s1",
                "user_input": {"project_name": "Test"},
                "template": {},
                "rag_chunks": [],
                "retry_count": 0,
                "draft_version": 0,
                "validation_findings": [
                    {
                        "severity": "error",
                        "message": "Some error from prior run",
                        "recommended_correction": "Fix it",
                    }
                ],
                "agent_timeout_seconds": 60,
            }

            await llm_draft(state)

            call_args = mock_llm.invoke.call_args
            messages = call_args.kwargs.get("messages") or call_args[0][0]

            user_msg = next(m for m in messages if m["role"] == "user")
            assert "ข้อเสนอแนะจากการตรวจสอบครั้งก่อน" not in user_msg["content"]
            assert "Some error from prior run" not in user_msg["content"]


# =============================================================================
# State initialization tests
# =============================================================================


class TestStateInitialization:
    """Tests for proper state initialization in validate_input."""

    @pytest.mark.asyncio
    async def test_initializes_best_draft_fields(self):
        """validate_input sets best_draft_content=None, best_draft_score=-1."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"project_name": "Test"},
            "target_section": "s1",
        }

        result = await validate_input(state)

        assert result["best_draft_content"] is None
        assert result["best_draft_score"] == -1.0
        assert result["best_draft_findings"] == []

    @pytest.mark.asyncio
    async def test_initializes_agent_timeout(self):
        """validate_input sets agent_timeout_seconds from state or default."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"project_name": "Test"},
            "target_section": "s1",
        }

        result = await validate_input(state)

        assert result["agent_timeout_seconds"] == LLM_TIMEOUT_SECONDS

    @pytest.mark.asyncio
    async def test_preserves_previously_completed_sections(self):
        """Sections previously finalized are not affected (Req 12.9)."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {
                "project_name": "Test",
                "existing_sections": {"s1": "Finalized s1 content"},
            },
            "target_section": "s2",
        }

        result = await validate_input(state)

        # existing_sections in user_input is preserved
        assert result["user_input"]["existing_sections"]["s1"] == "Finalized s1 content"
        assert result["error"] is None
