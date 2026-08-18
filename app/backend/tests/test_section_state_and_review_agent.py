"""Unit tests for cross-section state management and ReviewAgent.

Tests cover:
- SectionStateManager: add/remove/get sections, assembly, factory method
- ReviewAgent: deterministic checks, LLM review parsing, merge logic, full review
- Integration: SectionStateManager feeding into ReviewAgent

Requirements: 10.2, 12.4
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.orchestrator.agents.review_agent import (
    ReviewAgent,
    ReviewResult,
    ReviewSuggestion,
)
from app.orchestrator.section_state import (
    SECTION_NAMES_TH,
    SECTION_ORDER,
    SectionSnapshot,
    SectionStateManager,
)


# =============================================================================
# SectionStateManager tests
# =============================================================================


class TestSectionStateManager:
    """Tests for the SectionStateManager."""

    def test_init_creates_empty_manager(self):
        """Newly created manager has no sections."""
        manager = SectionStateManager(project_id="proj-001")
        assert manager.project_id == "proj-001"
        assert manager.section_count == 0
        assert manager.completed_section_keys == []

    def test_add_section_stores_content(self):
        """Adding a section stores it and increases count."""
        manager = SectionStateManager(project_id="proj-001")
        manager.add_section("s1", "ความเป็นมาของโครงการ...", quality_score=85.0)

        assert manager.section_count == 1
        assert manager.completed_section_keys == ["s1"]

        section = manager.get_section("s1")
        assert section is not None
        assert section.content == "ความเป็นมาของโครงการ..."
        assert section.quality_score == 85.0

    def test_add_section_with_metadata(self):
        """Sections can store additional metadata."""
        manager = SectionStateManager(project_id="proj-001")
        manager.add_section(
            "s6",
            "วงเงินงบประมาณ 5,000,000 บาท",
            quality_score=90.0,
            metadata={"budget": 5000000, "project_type": "it"},
        )

        section = manager.get_section("s6")
        assert section is not None
        assert section.metadata["budget"] == 5000000
        assert section.metadata["project_type"] == "it"

    def test_add_section_overwrites_existing(self):
        """Adding a section with the same key updates the content."""
        manager = SectionStateManager(project_id="proj-001")
        manager.add_section("s1", "Original content", quality_score=70.0)
        manager.add_section("s1", "Updated content", quality_score=85.0)

        assert manager.section_count == 1
        section = manager.get_section("s1")
        assert section.content == "Updated content"
        assert section.quality_score == 85.0

    def test_remove_section(self):
        """Removing a section decreases count."""
        manager = SectionStateManager(project_id="proj-001")
        manager.add_section("s1", "Content 1")
        manager.add_section("s2", "Content 2")

        manager.remove_section("s1")

        assert manager.section_count == 1
        assert manager.get_section("s1") is None
        assert manager.get_section("s2") is not None

    def test_remove_nonexistent_section_is_safe(self):
        """Removing a non-existent section doesn't raise."""
        manager = SectionStateManager(project_id="proj-001")
        manager.remove_section("s99")  # Should not raise
        assert manager.section_count == 0

    def test_get_existing_sections_returns_content_dict(self):
        """get_existing_sections returns section_key -> content mapping."""
        manager = SectionStateManager(project_id="proj-001")
        manager.add_section("s1", "Background...")
        manager.add_section("s2", "Objectives...")
        manager.add_section("s4", "Scope...")

        existing = manager.get_existing_sections()

        assert existing == {
            "s1": "Background...",
            "s2": "Objectives...",
            "s4": "Scope...",
        }

    def test_assemble_full_tor_in_order(self):
        """assemble_full_tor returns sections in standard TOR order."""
        manager = SectionStateManager(project_id="proj-001")
        # Add out of order
        manager.add_section("s4", "Scope content")
        manager.add_section("s1", "Background content")
        manager.add_section("s2", "Objectives content")

        assembled = manager.assemble_full_tor()

        # Keys should be in standard order
        keys = list(assembled.keys())
        assert keys == ["s1", "s2", "s4"]
        assert assembled["s1"] == "Background content"
        assert assembled["s4"] == "Scope content"

    def test_get_assembled_text_includes_headers(self):
        """get_assembled_text produces readable text with Thai headers."""
        manager = SectionStateManager(project_id="proj-001")
        manager.add_section("s1", "เนื้อหาความเป็นมา")
        manager.add_section("s2", "เนื้อหาวัตถุประสงค์")

        text = manager.get_assembled_text()

        assert "## ความเป็นมา" in text
        assert "เนื้อหาความเป็นมา" in text
        assert "## วัตถุประสงค์" in text
        assert "เนื้อหาวัตถุประสงค์" in text

    def test_get_average_quality_score(self):
        """Average score is computed correctly across sections with scores."""
        manager = SectionStateManager(project_id="proj-001")
        manager.add_section("s1", "content", quality_score=80.0)
        manager.add_section("s2", "content", quality_score=90.0)
        manager.add_section("s3", "content", quality_score=70.0)

        avg = manager.get_average_quality_score()
        assert avg == 80.0

    def test_get_average_quality_score_none_when_empty(self):
        """Average score is None when no sections have scores."""
        manager = SectionStateManager(project_id="proj-001")
        manager.add_section("s1", "content")  # No score

        assert manager.get_average_quality_score() is None

    def test_get_average_quality_score_ignores_none_scores(self):
        """Average score only considers sections with non-None scores."""
        manager = SectionStateManager(project_id="proj-001")
        manager.add_section("s1", "content", quality_score=80.0)
        manager.add_section("s2", "content")  # None score
        manager.add_section("s3", "content", quality_score=60.0)

        avg = manager.get_average_quality_score()
        assert avg == 70.0

    def test_from_sections_dict_factory(self):
        """from_sections_dict creates a populated manager."""
        sections = {"s1": "Background", "s2": "Objectives", "s4": "Scope"}
        scores = {"s1": 85.0, "s2": 90.0}
        metadata = {"s4": {"deliverables_count": 5}}

        manager = SectionStateManager.from_sections_dict(
            project_id="proj-002",
            sections=sections,
            scores=scores,
            metadata=metadata,
        )

        assert manager.project_id == "proj-002"
        assert manager.section_count == 3
        assert manager.get_section("s1").quality_score == 85.0
        assert manager.get_section("s4").metadata == {"deliverables_count": 5}
        assert manager.get_section("s2").quality_score == 90.0

    def test_completed_section_keys_in_order(self):
        """completed_section_keys returns keys in SECTION_ORDER."""
        manager = SectionStateManager(project_id="proj-001")
        # Add in reverse order
        manager.add_section("s10", "Penalties")
        manager.add_section("s1", "Background")
        manager.add_section("s4", "Scope")

        keys = manager.completed_section_keys
        assert keys == ["s1", "s4", "s10"]

    def test_get_section_metadata(self):
        """get_section_metadata returns metadata for all sections."""
        manager = SectionStateManager(project_id="proj-001")
        manager.add_section("s1", "bg", metadata={"key": "val1"})
        manager.add_section("s6", "budget", metadata={"budget": 1000000})

        meta = manager.get_section_metadata()
        assert meta == {
            "s1": {"key": "val1"},
            "s6": {"budget": 1000000},
        }


# =============================================================================
# ReviewAgent deterministic checks tests
# =============================================================================


class TestReviewAgentDeterministicChecks:
    """Tests for ReviewAgent._run_deterministic_checks."""

    def setup_method(self):
        """Create ReviewAgent instance for each test."""
        self.agent = ReviewAgent()

    def test_budget_scope_alignment_short_budget(self):
        """Flags when budget section is much shorter than scope."""
        sections = {
            "s4": "ขอบเขตงาน " * 100,  # Long scope (>500 chars)
            "s6": "งบ 5 ล้าน",  # Short budget (<200 chars)
        }

        suggestions = self.agent._run_deterministic_checks(sections, {})

        budget_suggestions = [s for s in suggestions if s.section_key == "s6"]
        assert len(budget_suggestions) >= 1
        assert budget_suggestions[0].category == "completeness"

    def test_payment_missing_deliverables_reference(self):
        """Flags when payment doesn't reference deliverables."""
        sections = {
            "s4": "ขอบเขตงาน: ผลงานส่งมอบหลายรายการ",
            "s8": "งวดที่ 1: จ่าย 30% งวดที่ 2: จ่าย 70%",  # No deliverables ref
        }

        suggestions = self.agent._run_deterministic_checks(sections, {})

        payment_suggestions = [s for s in suggestions if s.section_key == "s8"]
        assert len(payment_suggestions) >= 1
        assert payment_suggestions[0].category == "consistency"

    def test_payment_with_deliverables_no_flag(self):
        """No flag when payment mentions deliverables."""
        sections = {
            "s4": "ขอบเขตงาน: ระบบซอฟต์แวร์",
            "s8": "งวดที่ 1: ผลงานส่งมอบ — เอกสารออกแบบ จ่าย 30%",
        }

        suggestions = self.agent._run_deterministic_checks(sections, {})

        payment_suggestions = [s for s in suggestions if s.section_key == "s8"]
        assert len(payment_suggestions) == 0

    def test_background_missing_legal_reference(self):
        """Flags when background doesn't mention relevant law."""
        sections = {
            "s1": "หน่วยงานต้องการจัดซื้อระบบคอมพิวเตอร์เนื่องจากระบบเก่าชำรุด",
        }

        suggestions = self.agent._run_deterministic_checks(sections, {})

        bg_suggestions = [s for s in suggestions if s.section_key == "s1"]
        assert len(bg_suggestions) >= 1
        assert bg_suggestions[0].category == "compliance"

    def test_background_with_legal_reference_no_flag(self):
        """No flag when background mentions พ.ร.บ."""
        sections = {
            "s1": "ตามอำนาจหน้าที่ตาม พ.ร.บ. จัดซื้อจัดจ้าง 2560 จึงต้องดำเนินการ...",
        }

        suggestions = self.agent._run_deterministic_checks(sections, {})

        bg_suggestions = [s for s in suggestions if s.section_key == "s1"]
        assert len(bg_suggestions) == 0

    def test_qualifications_capital_check(self):
        """Flags when capital amount not mentioned for given budget."""
        sections = {
            "s3": "ผู้เสนอราคาต้องเป็นนิติบุคคลที่จดทะเบียนในประเทศไทย",
        }
        metadata = {"budget": 8000000}

        suggestions = self.agent._run_deterministic_checks(sections, metadata)

        qual_suggestions = [s for s in suggestions if s.section_key == "s3"]
        assert len(qual_suggestions) >= 1
        assert qual_suggestions[0].category == "compliance"
        assert "2,000,000" in qual_suggestions[0].suggested_text

    def test_qualifications_capital_present_no_flag(self):
        """No flag when correct capital amount is mentioned."""
        sections = {
            "s3": "ผู้เสนอราคาต้องมีทุนจดทะเบียนชำระแล้วไม่น้อยกว่า 2000000 บาท",
        }
        metadata = {"budget": 8000000}

        suggestions = self.agent._run_deterministic_checks(sections, metadata)

        qual_suggestions = [s for s in suggestions if s.section_key == "s3"]
        assert len(qual_suggestions) == 0

    def test_penalties_missing_rate(self):
        """Flags when penalties section doesn't mention percentage rate."""
        sections = {
            "s10": "กรณีส่งงานล่าช้า ผู้รับจ้างจะต้องชำระค่าปรับตามสัญญา",
        }

        suggestions = self.agent._run_deterministic_checks(sections, {})

        penalty_suggestions = [s for s in suggestions if s.section_key == "s10"]
        assert len(penalty_suggestions) >= 1
        assert penalty_suggestions[0].category == "compliance"

    def test_penalties_with_rate_no_flag(self):
        """No flag when penalties mention percentage."""
        sections = {
            "s10": "อัตราค่าปรับร้อยละ 0.10 ต่อวัน ของมูลค่างานที่ล่าช้า",
        }

        suggestions = self.agent._run_deterministic_checks(sections, {})

        penalty_suggestions = [s for s in suggestions if s.section_key == "s10"]
        assert len(penalty_suggestions) == 0

    def test_short_objectives_with_long_scope(self):
        """Flags incomplete objectives relative to scope."""
        sections = {
            "s2": "เพื่อพัฒนาระบบ",  # Too short
            "s4": "ขอบเขตงาน " * 100,  # Long scope
        }

        suggestions = self.agent._run_deterministic_checks(sections, {})

        obj_suggestions = [s for s in suggestions if s.section_key == "s2"]
        assert len(obj_suggestions) >= 1
        assert obj_suggestions[0].category == "completeness"

    def test_empty_sections_no_crash(self):
        """Empty sections dict produces no suggestions without errors."""
        suggestions = self.agent._run_deterministic_checks({}, {})
        assert suggestions == []


# =============================================================================
# ReviewAgent LLM parsing tests
# =============================================================================


class TestReviewAgentParsing:
    """Tests for ReviewAgent._parse_llm_suggestions."""

    def setup_method(self):
        """Create ReviewAgent instance."""
        self.agent = ReviewAgent()

    def test_parse_valid_json_array(self):
        """Parses a valid JSON array of suggestions."""
        llm_output = json.dumps([
            {
                "category": "consistency",
                "section_key": "s4",
                "current_text": "ขอบเขตงานระบุ 10 รายการ",
                "suggested_text": "ควรระบุให้สอดคล้องกับงวดงาน",
                "predicted_score_improvement": 2.5,
            },
            {
                "category": "compliance",
                "section_key": "s3",
                "current_text": "คุณสมบัติเดิม",
                "suggested_text": "เพิ่มทุนจดทะเบียน",
                "predicted_score_improvement": 4.0,
            },
        ])

        results = self.agent._parse_llm_suggestions(llm_output)

        assert len(results) == 2
        assert results[0].category == "consistency"
        assert results[0].section_key == "s4"
        assert results[0].predicted_score_improvement == 2.5
        assert results[1].category == "compliance"

    def test_parse_json_in_markdown_code_block(self):
        """Handles JSON wrapped in markdown code blocks."""
        llm_output = """```json
[
  {
    "category": "clarity",
    "section_key": "s1",
    "current_text": "เนื้อหาเดิม",
    "suggested_text": "เนื้อหาใหม่ที่ชัดเจนกว่า",
    "predicted_score_improvement": 1.5
  }
]
```"""

        results = self.agent._parse_llm_suggestions(llm_output)

        assert len(results) == 1
        assert results[0].category == "clarity"

    def test_parse_invalid_json_returns_empty(self):
        """Invalid JSON returns empty list."""
        results = self.agent._parse_llm_suggestions("This is not JSON at all")
        assert results == []

    def test_parse_filters_invalid_categories(self):
        """Items with invalid categories are skipped."""
        llm_output = json.dumps([
            {
                "category": "invalid_category",
                "section_key": "s1",
                "current_text": "text",
                "suggested_text": "suggestion",
                "predicted_score_improvement": 1.0,
            },
            {
                "category": "compliance",
                "section_key": "s1",
                "current_text": "valid",
                "suggested_text": "valid suggestion",
                "predicted_score_improvement": 2.0,
            },
        ])

        results = self.agent._parse_llm_suggestions(llm_output)

        assert len(results) == 1
        assert results[0].category == "compliance"

    def test_parse_filters_invalid_section_keys(self):
        """Items with invalid section keys are skipped."""
        llm_output = json.dumps([
            {
                "category": "compliance",
                "section_key": "s99",
                "current_text": "text",
                "suggested_text": "suggestion",
                "predicted_score_improvement": 1.0,
            },
        ])

        results = self.agent._parse_llm_suggestions(llm_output)
        assert results == []

    def test_parse_clamps_score_improvement(self):
        """Score improvement is clamped between 0.5 and 10.0."""
        llm_output = json.dumps([
            {
                "category": "compliance",
                "section_key": "s1",
                "current_text": "text",
                "suggested_text": "suggestion",
                "predicted_score_improvement": 50.0,
            },
            {
                "category": "clarity",
                "section_key": "s2",
                "current_text": "text",
                "suggested_text": "suggestion",
                "predicted_score_improvement": 0.01,
            },
        ])

        results = self.agent._parse_llm_suggestions(llm_output)

        assert results[0].predicted_score_improvement == 10.0
        assert results[1].predicted_score_improvement == 0.5

    def test_parse_skips_empty_text_fields(self):
        """Items with empty current_text or suggested_text are skipped."""
        llm_output = json.dumps([
            {
                "category": "compliance",
                "section_key": "s1",
                "current_text": "",
                "suggested_text": "suggestion",
                "predicted_score_improvement": 1.0,
            },
            {
                "category": "compliance",
                "section_key": "s2",
                "current_text": "text",
                "suggested_text": "",
                "predicted_score_improvement": 1.0,
            },
        ])

        results = self.agent._parse_llm_suggestions(llm_output)
        assert results == []

    def test_parse_truncates_long_text(self):
        """Very long text fields are truncated."""
        long_text = "A" * 1000
        llm_output = json.dumps([
            {
                "category": "clarity",
                "section_key": "s1",
                "current_text": long_text,
                "suggested_text": long_text,
                "predicted_score_improvement": 1.0,
            },
        ])

        results = self.agent._parse_llm_suggestions(llm_output)

        assert len(results) == 1
        assert len(results[0].current_text) <= 500
        assert len(results[0].suggested_text) <= 1000


# =============================================================================
# ReviewAgent merge logic tests
# =============================================================================


class TestReviewAgentMerge:
    """Tests for ReviewAgent._merge_suggestions."""

    def setup_method(self):
        """Create ReviewAgent instance."""
        self.agent = ReviewAgent()

    def test_merge_deduplicates_by_section_category(self):
        """LLM suggestions for same section+category are deduplicated."""
        deterministic = [
            ReviewSuggestion(
                category="compliance",
                section_key="s3",
                current_text="det text",
                suggested_text="det suggestion",
                predicted_score_improvement=4.0,
            ),
        ]
        llm_based = [
            ReviewSuggestion(
                category="compliance",
                section_key="s3",  # Same section+category
                current_text="llm text",
                suggested_text="llm suggestion",
                predicted_score_improvement=3.0,
            ),
            ReviewSuggestion(
                category="clarity",
                section_key="s3",  # Different category
                current_text="llm clarity",
                suggested_text="llm clarity fix",
                predicted_score_improvement=2.0,
            ),
        ]

        merged = self.agent._merge_suggestions(deterministic, llm_based)

        # Should have 2: deterministic compliance + llm clarity
        assert len(merged) == 2
        # Sorted by score (4.0, 2.0)
        assert merged[0].predicted_score_improvement == 4.0
        assert merged[1].category == "clarity"

    def test_merge_sorts_by_score_descending(self):
        """Merged results sorted by predicted_score_improvement descending."""
        det = [
            ReviewSuggestion("compliance", "s1", "t", "s", 2.0),
        ]
        llm = [
            ReviewSuggestion("clarity", "s2", "t", "s", 5.0),
            ReviewSuggestion("completeness", "s4", "t", "s", 1.0),
        ]

        merged = self.agent._merge_suggestions(det, llm)

        scores = [s.predicted_score_improvement for s in merged]
        assert scores == sorted(scores, reverse=True)

    def test_merge_empty_inputs(self):
        """Empty inputs produce empty merged list."""
        assert self.agent._merge_suggestions([], []) == []


# =============================================================================
# ReviewAgent full review tests
# =============================================================================


class TestReviewAgentFullReview:
    """Tests for the full ReviewAgent.review() flow."""

    @pytest.mark.asyncio
    async def test_review_with_llm_success(self):
        """Full review produces suggestions from both passes."""
        mock_llm = AsyncMock()
        mock_llm.invoke = AsyncMock(return_value=MagicMock(
            content=json.dumps([
                {
                    "category": "clarity",
                    "section_key": "s4",
                    "current_text": "ขอบเขตงานไม่ชัดเจน",
                    "suggested_text": "ขอบเขตงานที่ระบุรายละเอียดชัดเจน",
                    "predicted_score_improvement": 2.5,
                },
            ]),
            usage={"total_tokens": 1000},
        ))

        agent = ReviewAgent()
        sections = {
            "s1": "หน่วยงานต้องการจัดซื้อระบบ",  # Missing legal ref
            "s4": "ขอบเขตงาน " * 100,
            "s6": "งบ 5 ล้าน",  # Short budget
        }

        result = await agent.review(
            llm=mock_llm,
            sections=sections,
            project_metadata={"budget": 5000000},
        )

        assert isinstance(result, ReviewResult)
        assert len(result.suggestions) >= 1
        assert result.overall_assessment != ""

        # Check that categories are valid
        for s in result.suggestions:
            assert s.category in {"compliance", "clarity", "completeness", "consistency"}

    @pytest.mark.asyncio
    async def test_review_with_llm_failure_falls_back(self):
        """If LLM fails, review still returns deterministic suggestions."""
        mock_llm = AsyncMock()
        mock_llm.invoke = AsyncMock(side_effect=Exception("LLM error"))

        agent = ReviewAgent()
        sections = {
            "s1": "หน่วยงานต้องการจัดซื้อระบบ",  # Missing legal ref
            "s4": "ขอบเขตงาน " * 100,
            "s6": "งบ 5 ล้าน",  # Short budget
        }

        result = await agent.review(
            llm=mock_llm,
            sections=sections,
            project_metadata={},
        )

        # Should still have deterministic suggestions
        assert isinstance(result, ReviewResult)
        assert len(result.suggestions) >= 1

    @pytest.mark.asyncio
    async def test_review_empty_sections(self):
        """Review with no sections produces no crash and minimal result."""
        mock_llm = AsyncMock()

        agent = ReviewAgent()
        result = await agent.review(llm=mock_llm, sections={})

        assert isinstance(result, ReviewResult)
        assert len(result.suggestions) == 0

    @pytest.mark.asyncio
    async def test_review_respects_max_suggestions(self):
        """Review never returns more than MAX_SUGGESTIONS."""
        # Create a large mock response
        many_suggestions = [
            {
                "category": "clarity",
                "section_key": f"s{i % 13 + 1}",
                "current_text": f"text {i}",
                "suggested_text": f"suggestion {i}",
                "predicted_score_improvement": float(i),
            }
            for i in range(1, 30)
        ]

        mock_llm = AsyncMock()
        mock_llm.invoke = AsyncMock(return_value=MagicMock(
            content=json.dumps(many_suggestions),
            usage={"total_tokens": 2000},
        ))

        agent = ReviewAgent()
        sections = {"s1": "content", "s2": "content"}

        result = await agent.review(llm=mock_llm, sections=sections)

        assert len(result.suggestions) <= 20

    @pytest.mark.asyncio
    async def test_review_suggestion_categories_correct(self):
        """All suggestions have valid categories."""
        mock_llm = AsyncMock()
        mock_llm.invoke = AsyncMock(return_value=MagicMock(
            content=json.dumps([]),
            usage={"total_tokens": 100},
        ))

        agent = ReviewAgent()
        sections = {
            "s1": "เนื้อหาสั้น",
            "s3": "คุณสมบัติทั่วไป",
            "s4": "ขอบเขตงาน " * 100,
            "s6": "งบ",
            "s8": "งวดที่ 1 จ่าย 100%",
            "s10": "ปรับตามสัญญา",
        }

        result = await agent.review(
            llm=mock_llm,
            sections=sections,
            project_metadata={"budget": 4000000},
        )

        valid_categories = {"compliance", "clarity", "completeness", "consistency"}
        for s in result.suggestions:
            assert s.category in valid_categories


# =============================================================================
# Integration: SectionStateManager + ReviewAgent
# =============================================================================


class TestSectionStateReviewIntegration:
    """Tests combining SectionStateManager with ReviewAgent."""

    @pytest.mark.asyncio
    async def test_manager_feeds_review_agent(self):
        """SectionStateManager assembled TOR feeds ReviewAgent correctly."""
        # Build up sections through the manager
        manager = SectionStateManager(project_id="proj-integration")
        manager.add_section(
            "s1",
            "สำนักงานต้องการจัดซื้อระบบคอมพิวเตอร์",
            quality_score=75.0,
            metadata={"budget": 10000000},
        )
        manager.add_section(
            "s2",
            "เพื่อพัฒนาระบบ",
            quality_score=80.0,
        )
        manager.add_section(
            "s4",
            "ขอบเขตของงาน ประกอบด้วยรายการจัดซื้อเครื่องคอมพิวเตอร์ " * 20,
            quality_score=85.0,
        )

        # Use assembled TOR for review
        sections = manager.assemble_full_tor()
        assert "s1" in sections
        assert "s2" in sections
        assert "s4" in sections

        # Mock LLM
        mock_llm = AsyncMock()
        mock_llm.invoke = AsyncMock(return_value=MagicMock(
            content=json.dumps([]),
            usage={"total_tokens": 100},
        ))

        agent = ReviewAgent()
        result = await agent.review(
            llm=mock_llm,
            sections=sections,
            project_metadata={"budget": 10000000},
        )

        assert isinstance(result, ReviewResult)
        # Should detect missing legal reference in s1
        compliance_suggestions = [
            s for s in result.suggestions if s.category == "compliance"
        ]
        assert len(compliance_suggestions) >= 1

    def test_existing_sections_injection_for_drafting(self):
        """Demonstrates how manager feeds user_input for later agents."""
        manager = SectionStateManager(project_id="proj-001")
        manager.add_section("s1", "Background content about IT system")
        manager.add_section("s2", "Objectives: 1. Develop new system")
        manager.add_section("s4", "Scope: 10 workstations, 2 servers")

        # When drafting s6 (budget), inject existing sections
        existing = manager.get_existing_sections()
        user_input = {
            "budget": 5000000,
            "project_type": "it",
            "existing_sections": existing,
        }

        # The user_input now has context from earlier sections
        assert "s1" in user_input["existing_sections"]
        assert "s4" in user_input["existing_sections"]
        assert "IT system" in user_input["existing_sections"]["s1"]


# =============================================================================
# ReviewAgent assessment building tests
# =============================================================================


class TestReviewAgentAssessment:
    """Tests for ReviewAgent._build_assessment."""

    def setup_method(self):
        """Create ReviewAgent instance."""
        self.agent = ReviewAgent()

    def test_assessment_with_no_suggestions(self):
        """Assessment reports good quality when no suggestions."""
        assessment = self.agent._build_assessment(
            sections={"s1": "a", "s2": "b"},
            suggestions=[],
        )
        assert "สมบูรณ์ดี" in assessment
        assert "2 ส่วน" in assessment

    def test_assessment_with_few_suggestions(self):
        """Assessment reports minor issues for <=5 suggestions."""
        suggestions = [
            ReviewSuggestion("clarity", "s1", "t", "s", 1.0),
            ReviewSuggestion("compliance", "s3", "t", "s", 2.0),
        ]
        assessment = self.agent._build_assessment(
            sections={"s1": "a", "s3": "b"},
            suggestions=suggestions,
        )
        assert "2 รายการ" in assessment
        assert "คุณภาพดี" in assessment

    def test_assessment_with_many_suggestions(self):
        """Assessment recommends review for >5 suggestions."""
        suggestions = [
            ReviewSuggestion("clarity", f"s{i}", "t", "s", 1.0)
            for i in range(1, 8)
        ]
        assessment = self.agent._build_assessment(
            sections={"s1": "a"},
            suggestions=suggestions,
        )
        assert "ทบทวน" in assessment
