"""Unit tests for orchestrator graph node implementations.

Tests the 5 core orchestrator nodes:
- validate_input: Input validation and initialization
- retrieve_context: RAG retrieval with graceful failure handling
- llm_draft: LLM invocation with proper message construction
- rule_guardrail: Rule Engine validation and routing decision
- finalize: Section finalization

Also tests routing functions and helper utilities.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.orchestrator.agents.registry import get_agent_for_section
from app.orchestrator.graph import (
    MANDATORY_HUMAN_REVIEW_SECTIONS,
    _build_llm_messages,
    _build_rag_query,
    _create_rule_engine,
    finalize,
    llm_draft,
    retrieve_context,
    route_after_guardrail,
    route_after_human_review,
    route_after_validation,
    rule_guardrail,
    validate_input,
)
from app.orchestrator.state import TORDraftState

# =============================================================================
# validate_input tests
# =============================================================================


class TestValidateInput:
    """Tests for the validate_input node."""

    @pytest.mark.asyncio
    async def test_valid_input_initializes_state(self):
        """Valid input initializes retry_count, max_retries, and review flag."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"project_name": "Test"},
            "target_section": "s1",
        }

        result = await validate_input(state)

        assert result["error"] is None
        assert result["retry_count"] == 0
        assert result["max_retries"] == 3
        assert result["draft_version"] == 0
        assert result["requires_human_review"] is False

    @pytest.mark.asyncio
    async def test_missing_project_id_returns_error(self):
        """Missing project_id triggers validation error."""
        state: TORDraftState = {
            "user_input": {"name": "test"},
            "target_section": "s1",
        }

        result = await validate_input(state)

        assert result["error"] is not None
        assert "project_id" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_user_input_returns_error(self):
        """Missing user_input triggers validation error."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "target_section": "s1",
        }

        result = await validate_input(state)

        assert result["error"] is not None
        assert "user_input" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_target_section_returns_error(self):
        """Missing target_section triggers validation error."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"name": "test"},
        }

        result = await validate_input(state)

        assert result["error"] is not None
        assert "target_section" in result["error"]

    @pytest.mark.asyncio
    async def test_invalid_target_section_returns_error(self):
        """Invalid target_section key triggers validation error."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"name": "test"},
            "target_section": "s99",
        }

        result = await validate_input(state)

        assert result["error"] is not None
        assert "s99" in result["error"]
        assert "invalid" in result["error"]

    @pytest.mark.asyncio
    async def test_mandatory_review_sections(self):
        """Sections s3, s6, s8, s10, s13 require mandatory human review."""
        for section in MANDATORY_HUMAN_REVIEW_SECTIONS:
            state: TORDraftState = {
                "project_id": "proj-123",
                "user_input": {"name": "test"},
                "target_section": section,
            }

            result = await validate_input(state)

            assert result["requires_human_review"] is True, (
                f"Section {section} should require human review"
            )

    @pytest.mark.asyncio
    async def test_non_mandatory_review_sections(self):
        """Non-mandatory sections (s1, s2, s4, etc.) don't require review."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"name": "test"},
            "target_section": "s1",
        }

        result = await validate_input(state)

        assert result["requires_human_review"] is False

    @pytest.mark.asyncio
    async def test_max_retries_clamped_to_bounds(self):
        """max_retries is clamped between 1 and 10."""
        # Test upper bound
        state: TORDraftState = {
            "project_id": "proj-123",
            "user_input": {"name": "test"},
            "target_section": "s1",
            "max_retries": 99,
        }
        result = await validate_input(state)
        assert result["max_retries"] == 10

        # Test lower bound
        state["max_retries"] = 0
        result = await validate_input(state)
        assert result["max_retries"] == 1

    @pytest.mark.asyncio
    async def test_multiple_errors_reported(self):
        """All missing fields are reported in a single error."""
        state: TORDraftState = {}

        result = await validate_input(state)

        assert result["error"] is not None
        assert "project_id" in result["error"]
        assert "user_input" in result["error"]
        assert "target_section" in result["error"]


# =============================================================================
# retrieve_context tests
# =============================================================================


class TestRetrieveContext:
    """Tests for the retrieve_context node."""

    @pytest.mark.asyncio
    async def test_successful_retrieval(self):
        """Successful RAG retrieval populates rag_chunks."""
        mock_chunks = [
            MagicMock(
                id="chunk-1",
                text="Legal reference text",
                score=0.9,
                source_document="พ.ร.บ. 2560",
                section_label="§3",
                page_number=10,
                document_type="law",
                legal_reference="พ.ร.บ. 2560",
            )
        ]
        mock_result = MagicMock(chunks=mock_chunks)

        with patch(
            "app.rag.hybrid.hybrid_retrieve", new_callable=AsyncMock
        ) as mock_hybrid:
            mock_hybrid.return_value = (mock_result, [], False)

            state: TORDraftState = {
                "target_section": "s3",
                "user_input": {"project_name": "Test", "budget": 5000000},
            }

            result = await retrieve_context(state)

        assert result["rag_retrieval_failed"] is False
        assert len(result["rag_chunks"]) == 1
        assert result["rag_chunks"][0]["id"] == "chunk-1"
        assert result["rag_chunks"][0]["text"] == "Legal reference text"
        assert result["rag_chunks"][0]["score"] == 0.9

    @pytest.mark.asyncio
    async def test_retrieval_failure_graceful_degradation(self):
        """RAG failure sets rag_retrieval_failed=True and continues (Req 5.8)."""
        with patch(
            "app.rag.hybrid.hybrid_retrieve", new_callable=AsyncMock
        ) as mock_hybrid:
            mock_hybrid.side_effect = Exception("Connection refused")

            state: TORDraftState = {
                "target_section": "s1",
                "user_input": {"project_name": "Test"},
            }

            result = await retrieve_context(state)

        assert result["rag_retrieval_failed"] is True
        assert result["rag_chunks"] == []

    @pytest.mark.asyncio
    async def test_empty_retrieval_results(self):
        """Empty retrieval results are handled gracefully."""
        mock_result = MagicMock(chunks=[])

        with patch(
            "app.rag.hybrid.hybrid_retrieve", new_callable=AsyncMock
        ) as mock_hybrid:
            mock_hybrid.return_value = (mock_result, [], True)

            state: TORDraftState = {
                "target_section": "s1",
                "user_input": {"project_name": "Test"},
            }

            result = await retrieve_context(state)

        assert result["rag_retrieval_failed"] is False
        assert result["rag_chunks"] == []


# =============================================================================
# llm_draft tests
# =============================================================================


class TestLlmDraft:
    """Tests for the llm_draft node."""

    @pytest.mark.asyncio
    async def test_successful_draft_generation(self):
        """Successful LLM call returns draft content and increments version."""
        mock_response = MagicMock(
            content="ร่าง TOR ส่วนที่ 1: ความเป็นมา...",
            usage={"total_tokens": 500},
        )

        with patch("app.providers.factory.ProviderFactory") as mock_factory_cls:
            mock_factory = MagicMock()
            mock_llm = AsyncMock()
            mock_llm.invoke = AsyncMock(return_value=mock_response)
            mock_factory.get_llm.return_value = mock_llm
            mock_factory_cls.return_value = mock_factory

            state: TORDraftState = {
                "target_section": "s1",
                "user_input": {"project_name": "ระบบทดสอบ"},
                "template": {},
                "rag_chunks": [],
                "retry_count": 0,
                "draft_version": 0,
            }

            result = await llm_draft(state)

        assert result["draft_content"] == "ร่าง TOR ส่วนที่ 1: ความเป็นมา..."
        assert result["draft_version"] == 1

    @pytest.mark.asyncio
    async def test_draft_version_increments(self):
        """Each invocation increments draft_version."""
        mock_response = MagicMock(
            content="Draft v2",
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
                "retry_count": 1,
                "draft_version": 1,
            }

            result = await llm_draft(state)

        assert result["draft_version"] == 2

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """TimeoutError sets error message and preserves existing draft."""
        with patch("app.providers.factory.ProviderFactory") as mock_factory_cls:
            mock_factory = MagicMock()
            mock_llm = AsyncMock()
            mock_llm.invoke = AsyncMock(side_effect=TimeoutError("LLM timeout"))
            mock_factory.get_llm.return_value = mock_llm
            mock_factory_cls.return_value = mock_factory

            state: TORDraftState = {
                "target_section": "s1",
                "user_input": {"project_name": "Test"},
                "template": {},
                "rag_chunks": [],
                "retry_count": 0,
                "draft_version": 0,
                "draft_content": "previous draft",
            }

            result = await llm_draft(state)

        assert "timeout" in result["error"].lower()
        assert result["draft_content"] == "previous draft"

    @pytest.mark.asyncio
    async def test_connection_error_handling(self):
        """ConnectionError sets appropriate error message."""
        with patch("app.providers.factory.ProviderFactory") as mock_factory_cls:
            mock_factory = MagicMock()
            mock_llm = AsyncMock()
            mock_llm.invoke = AsyncMock(
                side_effect=ConnectionError("Provider unreachable")
            )
            mock_factory.get_llm.return_value = mock_llm
            mock_factory_cls.return_value = mock_factory

            state: TORDraftState = {
                "target_section": "s1",
                "user_input": {"project_name": "Test"},
                "template": {},
                "rag_chunks": [],
                "retry_count": 0,
                "draft_version": 0,
            }

            result = await llm_draft(state)

        assert "unreachable" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_uses_registered_section_agent(self):
        """llm_draft looks up get_agent_for_section('s1') and drafts through it."""
        mock_response = MagicMock(
            content="ร่างจาก agent",
            usage={"total_tokens": 120},
        )

        with patch("app.providers.factory.ProviderFactory") as mock_factory_cls:
            mock_factory = MagicMock()
            mock_llm = AsyncMock()
            mock_llm.invoke = AsyncMock(return_value=mock_response)
            mock_factory.get_llm.return_value = mock_llm
            mock_factory_cls.return_value = mock_factory

            with patch(
                "app.orchestrator.graph.get_agent_for_section",
                wraps=get_agent_for_section,
            ) as spy:
                state: TORDraftState = {
                    "target_section": "s1",
                    "user_input": {"project_name": "ระบบทดสอบ"},
                    "template": {},
                    "rag_chunks": [],
                    "retry_count": 0,
                    "draft_version": 0,
                }
                result = await llm_draft(state)

        spy.assert_called_with("s1")
        assert result["draft_content"] == "ร่างจาก agent"
        assert mock_llm.invoke.await_count == 2

    @pytest.mark.asyncio
    async def test_falls_back_when_no_agent(self):
        """When no agent is registered, llm_draft uses _build_llm_messages."""
        mock_response = MagicMock(
            content="fallback draft",
            usage={"total_tokens": 10},
        )

        with patch("app.providers.factory.ProviderFactory") as mock_factory_cls:
            mock_factory = MagicMock()
            mock_llm = AsyncMock()
            mock_llm.invoke = AsyncMock(return_value=mock_response)
            mock_factory.get_llm.return_value = mock_llm
            mock_factory_cls.return_value = mock_factory

            with patch(
                "app.orchestrator.graph.get_agent_for_section",
                return_value=None,
            ):
                state: TORDraftState = {
                    "target_section": "s1",
                    "user_input": {"project_name": "ระบบทดสอบ"},
                    "template": {},
                    "rag_chunks": [],
                    "retry_count": 0,
                    "draft_version": 0,
                }
                result = await llm_draft(state)

        assert result["draft_content"] == "fallback draft"
        call_kwargs = mock_llm.invoke.await_args.kwargs
        assert "messages" in call_kwargs
        assert call_kwargs["messages"][0]["role"] == "system"


# =============================================================================
# rule_guardrail tests
# =============================================================================


class TestRuleGuardrail:
    """Tests for the rule_guardrail node."""

    @pytest.mark.asyncio
    async def test_passing_score(self):
        """Score >= 70 sets guardrail_passed=True, no retry increment."""
        mock_result = MagicMock(
            quality_score=85,
            findings=[],
        )

        with patch("app.orchestrator.graph._create_rule_engine") as mock_create:
            mock_engine = MagicMock()
            mock_engine.validate.return_value = mock_result
            mock_create.return_value = mock_engine

            state: TORDraftState = {
                "target_section": "s1",
                "draft_content": "Valid TOR content",
                "user_input": {},
                "draft_version": 1,
                "retry_count": 0,
                "max_retries": 3,
            }

            result = await rule_guardrail(state)

        assert result["quality_score"] == 85
        assert result["guardrail_passed"] is True
        assert result["retry_count"] == 0  # Not incremented on pass

    @pytest.mark.asyncio
    async def test_failing_score_increments_retry(self):
        """Score < 70 sets guardrail_passed=False and increments retry_count."""
        from app.rule_engine.engine import Finding, Severity

        mock_finding = Finding(
            severity=Severity.ERROR,
            rule_violated="MISSING_LEGAL_REF",
            affected_section="s1",
            message="ไม่มีการอ้างอิง พ.ร.บ.",
            recommended_correction="เพิ่มการอ้างอิง พ.ร.บ. 2560",
        )
        mock_result = MagicMock(
            quality_score=45,
            findings=[mock_finding],
        )

        with patch("app.orchestrator.graph._create_rule_engine") as mock_create:
            mock_engine = MagicMock()
            mock_engine.validate.return_value = mock_result
            mock_create.return_value = mock_engine

            state: TORDraftState = {
                "target_section": "s1",
                "draft_content": "Incomplete content",
                "user_input": {},
                "draft_version": 1,
                "retry_count": 0,
                "max_retries": 3,
            }

            result = await rule_guardrail(state)

        assert result["quality_score"] == 45
        assert result["guardrail_passed"] is False
        assert result["retry_count"] == 1
        assert len(result["validation_findings"]) == 1
        assert result["validation_findings"][0]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_rule_engine_exception_treated_as_failure(self):
        """Rule Engine exception results in score 0 and retry increment."""
        with patch("app.orchestrator.graph._create_rule_engine") as mock_create:
            mock_engine = MagicMock()
            mock_engine.validate.side_effect = RuntimeError("Unexpected error")
            mock_create.return_value = mock_engine

            state: TORDraftState = {
                "target_section": "s1",
                "draft_content": "Some content",
                "user_input": {},
                "draft_version": 1,
                "retry_count": 0,
                "max_retries": 3,
            }

            result = await rule_guardrail(state)

        assert result["quality_score"] == 0
        assert result["guardrail_passed"] is False
        assert result["retry_count"] == 1
        assert result["validation_findings"][0]["rule_violated"] == "RULE_ENGINE_ERROR"

    @pytest.mark.asyncio
    async def test_includes_budget_metadata_for_validation(self):
        """User input budget and project_type are passed to Rule Engine."""
        mock_result = MagicMock(quality_score=80, findings=[])

        with patch("app.orchestrator.graph._create_rule_engine") as mock_create:
            mock_engine = MagicMock()
            mock_engine.validate.return_value = mock_result
            mock_create.return_value = mock_engine

            state: TORDraftState = {
                "target_section": "s6",
                "draft_content": "Budget content",
                "user_input": {
                    "budget": 5000000,
                    "project_type": "it",
                    "timeline_days": 180,
                },
                "draft_version": 1,
                "retry_count": 0,
                "max_retries": 3,
            }

            await rule_guardrail(state)

            # Verify the tor_document passed to engine includes metadata
            call_args = mock_engine.validate.call_args[0][0]
            assert call_args["budget"] == 5000000
            assert call_args["project_type"] == "it"
            assert call_args["timeline_days"] == 180
            assert call_args["s6"] == "Budget content"


# =============================================================================
# finalize tests
# =============================================================================


class TestFinalize:
    """Tests for the finalize node."""

    @pytest.mark.asyncio
    async def test_sets_finalized_content(self):
        """Finalize copies draft_content to finalized_content."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "target_section": "s1",
            "draft_content": "Finalized section content",
            "quality_score": 85,
        }

        result = await finalize(state)

        assert result["finalized_content"] == "Finalized section content"
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_clears_error_on_finalize(self):
        """Finalize clears any previous error state."""
        state: TORDraftState = {
            "project_id": "proj-123",
            "target_section": "s1",
            "draft_content": "Content",
            "quality_score": 85,
            "error": "some previous error",
        }

        result = await finalize(state)

        assert result["error"] is None


# =============================================================================
# Routing function tests
# =============================================================================


class TestRouteAfterValidation:
    """Tests for the route_after_validation function."""

    def test_routes_to_retrieve_on_success(self):
        """No error routes to retrieve_context."""
        state: TORDraftState = {"error": None}
        assert route_after_validation(state) == "retrieve_context"

    def test_routes_to_end_on_error(self):
        """Error present routes to END."""
        state: TORDraftState = {"error": "Validation failed"}
        assert route_after_validation(state) == "__end__"


class TestRouteAfterGuardrail:
    """Tests for the route_after_guardrail function."""

    def test_routes_to_human_review_when_passed(self):
        """Guardrail passed routes to human_review."""
        state: TORDraftState = {
            "guardrail_passed": True,
            "retry_count": 0,
            "max_retries": 3,
        }
        assert route_after_guardrail(state) == "human_review"

    def test_routes_to_llm_draft_when_failed_with_retries(self):
        """Failed with retries remaining routes to llm_draft."""
        state: TORDraftState = {
            "guardrail_passed": False,
            "retry_count": 1,
            "max_retries": 3,
        }
        assert route_after_guardrail(state) == "llm_draft"

    def test_routes_to_human_review_when_max_retries_exhausted(self):
        """Max retries exhausted routes to human_review with warnings."""
        state: TORDraftState = {
            "guardrail_passed": False,
            "retry_count": 3,
            "max_retries": 3,
        }
        assert route_after_guardrail(state) == "human_review"


class TestRouteAfterHumanReview:
    """Tests for the route_after_human_review function."""

    def test_routes_to_finalize_when_approved(self):
        """Human approved routes to finalize."""
        state: TORDraftState = {"human_approved": True, "human_feedback": None}
        assert route_after_human_review(state) == "finalize"

    def test_routes_to_llm_draft_when_rejected_with_feedback(self):
        """Human rejected with feedback routes to llm_draft."""
        state: TORDraftState = {
            "human_approved": False,
            "human_feedback": "Please add more detail",
        }
        assert route_after_human_review(state) == "llm_draft"

    def test_routes_to_finalize_when_no_decision(self):
        """No decision (None) defaults to finalize."""
        state: TORDraftState = {"human_approved": None, "human_feedback": None}
        assert route_after_human_review(state) == "finalize"

    def test_routes_to_finalize_when_rejected_without_feedback(self):
        """Rejected without feedback still goes to finalize (no re-draft)."""
        state: TORDraftState = {"human_approved": False, "human_feedback": None}
        assert route_after_human_review(state) == "finalize"


# =============================================================================
# Helper function tests
# =============================================================================


class TestBuildRagQuery:
    """Tests for the _build_rag_query helper."""

    def test_includes_section_name(self):
        """Query includes the TOR section name."""
        query = _build_rag_query("s1", {})
        assert "ความเป็นมา" in query

    def test_includes_project_name(self):
        """Query includes project name when available."""
        query = _build_rag_query("s1", {"project_name": "ระบบ IT"})
        assert "ระบบ IT" in query

    def test_includes_budget_for_s3(self):
        """Budget context added for qualifications section."""
        query = _build_rag_query("s3", {"budget": 5000000})
        assert "5000000" in query
        assert "คุณสมบัติ" in query

    def test_includes_legal_context_for_s10(self):
        """Legal context added for penalties section."""
        query = _build_rag_query("s10", {})
        assert "ค่าปรับ" in query
        assert "พ.ร.บ. 2560" in query


class TestBuildLlmMessages:
    """Tests for the _build_llm_messages helper."""

    def test_system_prompt_for_known_section(self):
        """Known section gets its specialized system prompt."""
        messages = _build_llm_messages(
            target_section="s1",
            user_input={"project_name": "test"},
            template={},
            rag_chunks=[],
        )

        assert messages[0]["role"] == "system"
        assert "ความเป็นมา" in messages[0]["content"]

    def test_user_message_includes_input(self):
        """User message includes user_input data."""
        messages = _build_llm_messages(
            target_section="s1",
            user_input={"project_name": "ระบบทดสอบ", "description": "ระบบใหม่"},
            template={},
            rag_chunks=[],
        )

        user_msg = messages[1]["content"]
        assert "ระบบทดสอบ" in user_msg
        assert "ระบบใหม่" in user_msg

    def test_includes_rag_context(self):
        """RAG chunks are included in user message."""
        chunks = [
            {"text": "Legal text from law", "source_document": "พ.ร.บ. 2560"}
        ]
        messages = _build_llm_messages(
            target_section="s1",
            user_input={"project_name": "test"},
            template={},
            rag_chunks=chunks,
        )

        user_msg = messages[1]["content"]
        assert "Legal text from law" in user_msg
        assert "พ.ร.บ. 2560" in user_msg

    def test_includes_validation_feedback_on_retry(self):
        """Validation findings included when retry_count > 0."""
        findings = [
            {
                "severity": "error",
                "message": "ไม่มีการอ้างอิงกฎหมาย",
                "recommended_correction": "เพิ่ม พ.ร.บ. 2560",
            }
        ]
        messages = _build_llm_messages(
            target_section="s1",
            user_input={"project_name": "test"},
            template={},
            rag_chunks=[],
            validation_findings=findings,
            retry_count=1,
        )

        user_msg = messages[1]["content"]
        assert "ข้อแก้ไข" in user_msg
        assert "ไม่มีการอ้างอิงกฎหมาย" in user_msg
        assert "เพิ่ม พ.ร.บ. 2560" in user_msg

    def test_no_validation_feedback_on_first_attempt(self):
        """No validation feedback shown on first attempt (retry_count=0)."""
        findings = [
            {
                "severity": "error",
                "message": "Some error",
                "recommended_correction": "Fix it",
            }
        ]
        messages = _build_llm_messages(
            target_section="s1",
            user_input={"project_name": "test"},
            template={},
            rag_chunks=[],
            validation_findings=findings,
            retry_count=0,
        )

        user_msg = messages[1]["content"]
        assert "ข้อแก้ไข" not in user_msg

    def test_includes_human_feedback(self):
        """Human feedback is included in user message."""
        messages = _build_llm_messages(
            target_section="s1",
            user_input={"project_name": "test"},
            template={},
            rag_chunks=[],
            human_feedback="กรุณาเพิ่มรายละเอียดเพิ่มเติม",
        )

        user_msg = messages[1]["content"]
        assert "กรุณาเพิ่มรายละเอียดเพิ่มเติม" in user_msg

    def test_fallback_system_prompt_for_unknown_section(self):
        """Unknown section gets a generic system prompt."""
        messages = _build_llm_messages(
            target_section="s99",
            user_input={"project_name": "test"},
            template={},
            rag_chunks=[],
        )

        assert "ผู้เชี่ยวชาญ" in messages[0]["content"]
        assert "ภาษาราชการไทย" in messages[0]["content"]

    def test_no_rag_shows_notice(self):
        """When no RAG chunks, a notice about missing context is shown."""
        messages = _build_llm_messages(
            target_section="s1",
            user_input={"project_name": "test"},
            template={},
            rag_chunks=[],
        )

        user_msg = messages[1]["content"]
        assert "ไม่สามารถดึงข้อมูลอ้างอิง" in user_msg


class TestCreateRuleEngine:
    """Tests for the _create_rule_engine helper."""

    def test_creates_rule_engine_instance(self):
        """Creates a RuleEngine with rules registered."""
        engine = _create_rule_engine()

        from app.rule_engine.engine import RuleEngine

        assert isinstance(engine, RuleEngine)

    def test_legal_rules_registered(self):
        """Legal rules include payment and timeline feasibility rules."""
        engine = _create_rule_engine()
        from app.rule_engine.rules.payment import PaymentScheduleRule
        from app.rule_engine.rules.timeline import TimelineFeasibilityRule

        assert len(engine._rules["legal"]) > 0
        legal_types = {type(rule) for rule in engine._rules["legal"]}
        assert PaymentScheduleRule in legal_types
        assert TimelineFeasibilityRule in legal_types
        from app.rule_engine.rules.risk import AnnouncedPriceRule

        assert AnnouncedPriceRule in legal_types

    def test_format_rules_registered(self):
        """Format rules are registered in the engine."""
        engine = _create_rule_engine()
        assert len(engine._rules["format"]) > 0
