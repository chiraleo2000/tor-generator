"""Unit tests for completeness and consistency rules.

Tests cover:
- SectionPresenceRule: All 13 sections present, missing sections raise halt
- RequiredSubsectionsRule: Required subsections in scope of work
- MinimumContentRule: Minimum content length enforcement
- BudgetScopeConsistencyRule: Budget-scope alignment
- TimelineDeliverablesConsistencyRule: Timeline-deliverables alignment
- QualificationsComplexityConsistencyRule: Qualifications-complexity alignment
- Engine integration: Halting when required sections are missing (Req 6.9)
"""

from __future__ import annotations

import pytest

from app.domain.tor_sections import sample_complete_sections
from app.rule_engine.engine import Finding, RuleEngine, Severity
from app.rule_engine.rules.completeness import (
    CRITICAL_SECTIONS_MIN_LENGTH,
    MINIMUM_CONTENT_LENGTH,
    TOR_REQUIRED_SECTIONS,
    MinimumContentRule,
    MissingSectionsHalt,
    RequiredSubsectionsRule,
    SectionPresenceRule,
)
from app.rule_engine.rules.consistency import (
    BudgetScopeConsistencyRule,
    QualificationsComplexityConsistencyRule,
    TimelineDeliverablesConsistencyRule,
)


# --- Fixtures ---


@pytest.fixture
def complete_tor_document() -> dict:
    """A TOR document with all 13 sections filled with adequate content."""
    return {
        "sections": sample_complete_sections(),
        "metadata": {
            "budget": 5_000_000,
            "project_type": "it",
            "timeline_days": 180,
        },
    }


@pytest.fixture
def incomplete_tor_document() -> dict:
    """A TOR document with some sections missing."""
    return {
        "sections": {
            "s1": "ความเป็นมาของโครงการพัฒนาระบบสารสนเทศเพื่อการจัดการทรัพยากรบุคคล ของกระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม",
            "s2": "วัตถุประสงค์เพื่อพัฒนาระบบ",
            "s4": "ขอบเขตของงาน...",
            "s7": "งบประมาณ 5,000,000 บาท",
            # Missing: s3, s5, s6, s8, s9, s10, s11, s12, s13
        },
        "metadata": {
            "budget": 5_000_000,
            "project_type": "it",
            "timeline_days": 180,
        },
    }


# --- Tests: SectionPresenceRule ---


class TestSectionPresenceRule:
    """Test that all 13 required sections are checked."""

    def test_all_sections_present_passes(self, complete_tor_document: dict):
        """Document with all 13 sections produces no findings."""
        rule = SectionPresenceRule()
        findings = rule.validate(complete_tor_document)
        assert findings == []

    def test_missing_sections_raises_halt(self, incomplete_tor_document: dict):
        """Document with missing sections raises MissingSectionsHalt."""
        rule = SectionPresenceRule()
        with pytest.raises(MissingSectionsHalt) as exc_info:
            rule.validate(incomplete_tor_document)

        halt = exc_info.value
        assert "s3" in halt.missing_sections
        assert "s5" in halt.missing_sections
        assert "s6" in halt.missing_sections
        assert "s8" in halt.missing_sections
        assert "s9" in halt.missing_sections
        assert "s10" in halt.missing_sections
        assert "s11" in halt.missing_sections
        assert "s12" in halt.missing_sections
        assert "s13" in halt.missing_sections

    def test_missing_single_section_raises_halt(self, complete_tor_document: dict):
        """Even one missing section raises MissingSectionsHalt."""
        del complete_tor_document["sections"]["s13"]
        rule = SectionPresenceRule()

        with pytest.raises(MissingSectionsHalt) as exc_info:
            rule.validate(complete_tor_document)

        halt = exc_info.value
        assert halt.missing_sections == {
            "s13": TOR_REQUIRED_SECTIONS["s13"]
        }
        assert len(halt.findings) == 1
        assert halt.findings[0].severity == Severity.ERROR

    def test_empty_string_treated_as_missing(self, complete_tor_document: dict):
        """A section with empty string content is treated as missing."""
        complete_tor_document["sections"]["s5"] = ""
        rule = SectionPresenceRule()

        with pytest.raises(MissingSectionsHalt) as exc_info:
            rule.validate(complete_tor_document)

        assert "s5" in exc_info.value.missing_sections

    def test_whitespace_only_treated_as_missing(self, complete_tor_document: dict):
        """A section with only whitespace is treated as missing."""
        complete_tor_document["sections"]["s5"] = "   \n\t  "
        rule = SectionPresenceRule()

        with pytest.raises(MissingSectionsHalt) as exc_info:
            rule.validate(complete_tor_document)

        assert "s5" in exc_info.value.missing_sections

    def test_findings_have_correct_fields(self, incomplete_tor_document: dict):
        """Halt findings contain correct severity and rule_violated."""
        rule = SectionPresenceRule()
        with pytest.raises(MissingSectionsHalt) as exc_info:
            rule.validate(incomplete_tor_document)

        for finding in exc_info.value.findings:
            assert finding.severity == Severity.ERROR
            assert finding.rule_violated == "COMPLETENESS_SECTION_MISSING"
            assert finding.recommended_correction is not None

    def test_document_without_sections_wrapper(self):
        """Document with flat structure (no 'sections' key) is handled."""
        doc = {
            "s1": "ความเป็นมา test content that is long enough for the section",
            "s2": "วัตถุประสงค์ test objectives content",
        }
        rule = SectionPresenceRule()
        with pytest.raises(MissingSectionsHalt):
            rule.validate(doc)


# --- Tests: RequiredSubsectionsRule ---


class TestRequiredSubsectionsRule:
    """Test that required subsections are checked."""

    def test_scope_with_subsections_as_dict(self, complete_tor_document: dict):
        """Scope with subsections as nested dict passes."""
        complete_tor_document["sections"]["s4"] = {
            "s4.1": "รายละเอียดงานพัฒนาระบบ",
            "s4.8": "ผลงานส่งมอบ: รายงาน, ระบบ, คู่มือ",
        }
        rule = RequiredSubsectionsRule()
        findings = rule.validate(complete_tor_document)
        assert findings == []

    def test_scope_with_subsections_as_top_level(self, complete_tor_document: dict):
        """Subsections as top-level keys pass."""
        complete_tor_document["sections"]["s4.1"] = "รายละเอียดงาน"
        complete_tor_document["sections"]["s4.8"] = "ผลงานส่งมอบ"
        rule = RequiredSubsectionsRule()
        findings = rule.validate(complete_tor_document)
        assert findings == []

    def test_missing_subsections_produces_warnings(self, complete_tor_document: dict):
        """Missing required subsections produce WARNING findings."""
        # s4 is just a string, no subsections explicitly defined
        complete_tor_document["sections"]["s4"] = "ขอบเขตของงาน"
        # Remove any top-level subsection keys
        complete_tor_document["sections"].pop("s4.1", None)
        complete_tor_document["sections"].pop("s4.8", None)
        rule = RequiredSubsectionsRule()
        findings = rule.validate(complete_tor_document)
        assert len(findings) == 2
        assert all(f.severity == Severity.WARNING for f in findings)
        assert all(f.rule_violated == "COMPLETENESS_SUBSECTION_MISSING" for f in findings)
        assert all(f.affected_section == "s4" for f in findings)

    def test_partial_subsections_produces_one_warning(self, complete_tor_document: dict):
        """Only missing subsections produce warnings."""
        complete_tor_document["sections"]["s4"] = {
            "s4.1": "รายละเอียดงานพัฒนาระบบ",
            # s4.8 missing
        }
        rule = RequiredSubsectionsRule()
        findings = rule.validate(complete_tor_document)
        assert len(findings) == 1
        assert "ผลงานส่งมอบ" in findings[0].message


# --- Tests: MinimumContentRule ---


class TestMinimumContentRule:
    """Test minimum content length enforcement."""

    def test_adequate_content_passes(self, complete_tor_document: dict):
        """Sections with adequate content produce no findings."""
        rule = MinimumContentRule()
        findings = rule.validate(complete_tor_document)
        assert findings == []

    def test_short_content_produces_warning(self, complete_tor_document: dict):
        """Sections with too-short content produce WARNING findings."""
        # s1 requires 50 chars minimum
        complete_tor_document["sections"]["s1"] = "สั้นเกินไป"  # ~10 chars
        rule = MinimumContentRule()
        findings = rule.validate(complete_tor_document)
        assert len(findings) >= 1
        s1_findings = [f for f in findings if f.affected_section == "s1"]
        assert len(s1_findings) == 1
        assert s1_findings[0].severity == Severity.WARNING
        assert s1_findings[0].rule_violated == "COMPLETENESS_CONTENT_TOO_SHORT"

    def test_critical_section_higher_minimum(self, complete_tor_document: dict):
        """Critical sections have higher minimum than default."""
        # s4 (scope) requires 100 chars
        complete_tor_document["sections"]["s4"] = "ขอบเขตงานสั้น"  # ~14 chars
        rule = MinimumContentRule()
        findings = rule.validate(complete_tor_document)
        s4_findings = [f for f in findings if f.affected_section == "s4"]
        assert len(s4_findings) == 1
        assert "100" in s4_findings[0].message

    def test_non_critical_section_uses_default_minimum(self, complete_tor_document: dict):
        """Non-critical sections use MINIMUM_CONTENT_LENGTH (20 chars)."""
        # s10 is not in CRITICAL_SECTIONS_MIN_LENGTH, uses default 20
        complete_tor_document["sections"]["s10"] = "สั้น"  # ~4 chars
        rule = MinimumContentRule()
        findings = rule.validate(complete_tor_document)
        s10_findings = [f for f in findings if f.affected_section == "s10"]
        assert len(s10_findings) == 1

    def test_missing_sections_are_skipped(self, complete_tor_document: dict):
        """Missing sections (None) are not checked by MinimumContentRule."""
        complete_tor_document["sections"]["s13"] = None
        rule = MinimumContentRule()
        findings = rule.validate(complete_tor_document)
        s13_findings = [f for f in findings if f.affected_section == "s13"]
        assert s13_findings == []

    def test_dict_section_content_joined(self, complete_tor_document: dict):
        """Dict section content is joined for length check."""
        complete_tor_document["sections"]["s4"] = {
            "s4.1": "รายละเอียดงานพัฒนาระบบสารสนเทศครบวงจรสำหรับองค์กรภาครัฐ รวมถึงการออกแบบ พัฒนา ทดสอบ และติดตั้งระบบ",
            "s4.8": "ผลงานส่งมอบประกอบด้วยรายงานการวิเคราะห์ ระบบซอฟต์แวร์ที่พัฒนาเสร็จ และคู่มือผู้ใช้งาน รวมถึงการฝึกอบรมบุคลากร",
        }
        rule = MinimumContentRule()
        findings = rule.validate(complete_tor_document)
        s4_findings = [f for f in findings if f.affected_section == "s4"]
        assert s4_findings == []  # Combined is long enough


# --- Tests: BudgetScopeConsistencyRule ---


class TestBudgetScopeConsistencyRule:
    """Test budget-scope alignment validation."""

    def test_adequate_budget_for_scope_passes(self, complete_tor_document: dict):
        """Budget matching scope complexity produces no findings."""
        rule = BudgetScopeConsistencyRule()
        findings = rule.validate(complete_tor_document)
        # 5M budget with simple IT scope — should pass
        assert not any(
            f.rule_violated == "CONSISTENCY_BUDGET_LOW_FOR_SCOPE" for f in findings
        )

    def test_low_budget_for_complex_scope_warns(self):
        """Complex scope with low budget produces WARNING."""
        doc = {
            "sections": {
                "s4": (
                    "พัฒนาระบบสารสนเทศบูรณาการเชื่อมโยงฐานข้อมูลขนาดใหญ่ "
                    "ระบบเครือข่ายความปลอดภัย Cloud AI Machine Learning"
                ),
                "s6": "งบประมาณ 500,000 บาท",
            },
            "metadata": {"budget": 500_000},
        }
        rule = BudgetScopeConsistencyRule()
        findings = rule.validate(doc)
        assert any(
            f.rule_violated == "CONSISTENCY_BUDGET_LOW_FOR_SCOPE" for f in findings
        )

    def test_budget_mismatch_in_content_vs_metadata(self):
        """Budget amount in text not matching metadata produces ERROR."""
        doc = {
            "sections": {
                "s4": "ขอบเขตงาน",
                "s6": "งบประมาณ 10,000,000 บาท",
            },
            "metadata": {"budget": 5_000_000},
        }
        rule = BudgetScopeConsistencyRule()
        findings = rule.validate(doc)
        assert any(
            f.rule_violated == "CONSISTENCY_BUDGET_MISMATCH" for f in findings
        )

    def test_budget_matching_in_content_passes(self):
        """Budget amount in text matching metadata produces no mismatch finding."""
        doc = {
            "sections": {
                "s4": "ขอบเขตงาน",
                "s6": "งบประมาณ 5,000,000 บาท (ห้าล้านบาทถ้วน)",
            },
            "metadata": {"budget": 5_000_000},
        }
        rule = BudgetScopeConsistencyRule()
        findings = rule.validate(doc)
        assert not any(
            f.rule_violated == "CONSISTENCY_BUDGET_MISMATCH" for f in findings
        )

    def test_invalid_budget_produces_error(self):
        """Non-numeric budget produces ERROR."""
        doc = {
            "sections": {"s4": "ขอบเขตงาน", "s6": "งบประมาณ"},
            "metadata": {"budget": "invalid"},
        }
        rule = BudgetScopeConsistencyRule()
        findings = rule.validate(doc)
        assert any(
            f.rule_violated == "CONSISTENCY_BUDGET_INVALID" for f in findings
        )

    def test_no_budget_returns_empty(self):
        """Document without budget metadata returns no findings."""
        doc = {
            "sections": {"s4": "ขอบเขตงาน", "s6": "งบประมาณ"},
            "metadata": {},
        }
        rule = BudgetScopeConsistencyRule()
        findings = rule.validate(doc)
        assert findings == []


# --- Tests: TimelineDeliverablesConsistencyRule ---


class TestTimelineDeliverablesConsistencyRule:
    """Test timeline-deliverables alignment validation."""

    def test_reasonable_timeline_passes(self, complete_tor_document: dict):
        """Timeline adequate for deliverables produces no issue."""
        rule = TimelineDeliverablesConsistencyRule()
        findings = rule.validate(complete_tor_document)
        # 180 days, 3 deliverables → 60 days each, fine
        assert not any(
            f.rule_violated == "CONSISTENCY_TIMELINE_TOO_SHORT_FOR_DELIVERABLES"
            for f in findings
        )

    def test_too_many_deliverables_for_timeline_warns(self):
        """Many deliverables with short timeline produces WARNING."""
        doc = {
            "sections": {
                "s4": (
                    "ผลงานส่งมอบ งวดที่ 1 งวดที่ 2 งวดที่ 3 งวดที่ 4 "
                    "งวดที่ 5 งวดที่ 6 งวดที่ 7 งวดที่ 8 งวดที่ 9 งวดที่ 10"
                ),
                "s5": "ระยะเวลา 30 วัน",
                "s8": "การชำระเงิน",
            },
            "metadata": {"timeline_days": 30},
        }
        rule = TimelineDeliverablesConsistencyRule()
        findings = rule.validate(doc)
        assert any(
            f.rule_violated == "CONSISTENCY_TIMELINE_TOO_SHORT_FOR_DELIVERABLES"
            for f in findings
        )

    def test_too_many_payment_phases_for_timeline_warns(self):
        """Many payment phases with short timeline produces WARNING."""
        doc = {
            "sections": {
                "s4": "ขอบเขตงาน",
                "s5": "ระยะเวลา 30 วัน",
                "s8": "งวดที่ 1 งวดที่ 2 งวดที่ 3 งวดที่ 4 งวดที่ 5",
            },
            "metadata": {"timeline_days": 30},
        }
        rule = TimelineDeliverablesConsistencyRule()
        findings = rule.validate(doc)
        assert any(
            f.rule_violated == "CONSISTENCY_PAYMENT_PHASES_TOO_MANY"
            for f in findings
        )

    def test_no_timeline_returns_empty(self):
        """Document without timeline_days returns no findings."""
        doc = {
            "sections": {"s4": "ขอบเขตงาน", "s5": "ระยะเวลา", "s8": "การชำระเงิน"},
            "metadata": {},
        }
        rule = TimelineDeliverablesConsistencyRule()
        findings = rule.validate(doc)
        assert findings == []

    def test_invalid_timeline_produces_error(self):
        """Non-numeric timeline_days produces ERROR."""
        doc = {
            "sections": {"s4": "ขอบเขตงาน", "s5": "ระยะเวลา"},
            "metadata": {"timeline_days": "invalid"},
        }
        rule = TimelineDeliverablesConsistencyRule()
        findings = rule.validate(doc)
        assert any(
            f.rule_violated == "CONSISTENCY_TIMELINE_INVALID" for f in findings
        )


# --- Tests: QualificationsComplexityConsistencyRule ---


class TestQualificationsComplexityConsistencyRule:
    """Test qualifications-complexity alignment validation."""

    def test_matching_qualifications_passes(self, complete_tor_document: dict):
        """IT scope with IT qualifications produces no findings."""
        rule = QualificationsComplexityConsistencyRule()
        findings = rule.validate(complete_tor_document)
        # Scope mentions ระบบสารสนเทศ, quals mention ประสบการณ์ด้านเทคโนโลยีสารสนเทศ
        assert not any(
            f.rule_violated == "CONSISTENCY_QUALIFICATIONS_MISMATCH"
            for f in findings
        )

    def test_it_scope_without_it_qualifications_warns(self):
        """IT scope without IT qualifications produces WARNING."""
        doc = {
            "sections": {
                "s3": "ผู้เสนอราคาต้องเป็นนิติบุคคล จดทะเบียน",
                "s4": "พัฒนาระบบสารสนเทศ ซอฟต์แวร์ เว็บไซต์ แอปพลิเคชัน",
            },
            "metadata": {"budget": 1_000_000, "project_type": "it"},
        }
        rule = QualificationsComplexityConsistencyRule()
        findings = rule.validate(doc)
        assert any(
            f.rule_violated == "CONSISTENCY_QUALIFICATIONS_MISMATCH"
            for f in findings
        )

    def test_construction_scope_without_construction_qualifications_warns(self):
        """Construction scope without matching qualifications produces WARNING."""
        doc = {
            "sections": {
                "s3": "ผู้เสนอราคาต้องเป็นนิติบุคคล",
                "s4": "ก่อสร้างอาคาร ถนน สะพาน งานโยธา",
            },
            "metadata": {"budget": 10_000_000, "project_type": "construction"},
        }
        rule = QualificationsComplexityConsistencyRule()
        findings = rule.validate(doc)
        assert any(
            f.rule_violated == "CONSISTENCY_QUALIFICATIONS_MISMATCH"
            for f in findings
        )

    def test_high_budget_without_strong_qualifications_warns(self):
        """High budget project without strong qualifications produces WARNING."""
        doc = {
            "sections": {
                "s3": "ผู้เสนอราคาต้องเป็นนิติบุคคล",
                "s4": "ขอบเขตงาน",
            },
            "metadata": {"budget": 60_000_000},
        }
        rule = QualificationsComplexityConsistencyRule()
        findings = rule.validate(doc)
        assert any(
            f.rule_violated == "CONSISTENCY_QUALIFICATIONS_WEAK_FOR_BUDGET"
            for f in findings
        )

    def test_high_budget_with_strong_qualifications_passes(self):
        """High budget with strong qualifications passes."""
        doc = {
            "sections": {
                "s3": "ผู้เสนอราคาต้องมีประสบการณ์ไม่น้อยกว่า 5 ปี มีผลงานไม่น้อยกว่า 3 โครงการ ทุนจดทะเบียนไม่น้อยกว่า 15 ล้านบาท",
                "s4": "ขอบเขตงาน",
            },
            "metadata": {"budget": 60_000_000},
        }
        rule = QualificationsComplexityConsistencyRule()
        findings = rule.validate(doc)
        assert not any(
            f.rule_violated == "CONSISTENCY_QUALIFICATIONS_WEAK_FOR_BUDGET"
            for f in findings
        )

    def test_empty_scope_and_qualifications_returns_empty(self):
        """Empty scope and qualifications returns no findings."""
        doc = {
            "sections": {"s3": "", "s4": ""},
            "metadata": {"budget": 1_000_000},
        }
        rule = QualificationsComplexityConsistencyRule()
        findings = rule.validate(doc)
        assert findings == []


# --- Tests: Engine integration with halting (Req 6.9) ---


class TestEngineHaltingOnMissingSections:
    """Test that the engine halts scoring when sections are missing."""

    def test_engine_halts_when_sections_missing(self, incomplete_tor_document: dict):
        """Engine returns halted=True with missing_sections when sections missing."""
        engine = RuleEngine()
        engine.register_rule("completeness", SectionPresenceRule())
        engine.register_rule("completeness", RequiredSubsectionsRule())
        engine.register_rule("completeness", MinimumContentRule())

        result = engine.validate(incomplete_tor_document)

        assert result.halted is True
        assert result.quality_score == 0
        assert result.is_valid is False
        assert len(result.missing_sections) > 0
        assert "s3" in result.missing_sections

    def test_engine_does_not_halt_when_all_present(self, complete_tor_document: dict):
        """Engine does not halt when all sections are present."""
        engine = RuleEngine()
        engine.register_rule("completeness", SectionPresenceRule())
        engine.register_rule("completeness", RequiredSubsectionsRule())
        engine.register_rule("completeness", MinimumContentRule())

        result = engine.validate(complete_tor_document)

        assert result.halted is False
        assert result.quality_score > 0
        assert len(result.missing_sections) == 0

    def test_engine_halt_prevents_other_category_validation(
        self, incomplete_tor_document: dict
    ):
        """When halted, other categories are not validated."""
        engine = RuleEngine()
        # Register SectionPresenceRule first in completeness (will halt)
        engine.register_rule("completeness", SectionPresenceRule())
        # Register consistency rules (should NOT execute)
        engine.register_rule("consistency", BudgetScopeConsistencyRule())
        engine.register_rule("consistency", TimelineDeliverablesConsistencyRule())

        result = engine.validate(incomplete_tor_document)

        assert result.halted is True
        # Only completeness findings should be present
        assert all(
            f.rule_violated == "COMPLETENESS_SECTION_MISSING"
            for f in result.findings
        )
        # No category breakdown when halted
        assert result.categories == []

    def test_engine_returns_all_missing_sections_in_list(
        self, incomplete_tor_document: dict
    ):
        """Halted result includes full list of all missing sections."""
        engine = RuleEngine()
        engine.register_rule("completeness", SectionPresenceRule())

        result = engine.validate(incomplete_tor_document)

        assert result.halted is True
        # The incomplete doc is missing s3, s5, s6, s8, s9, s10, s11, s12, s13
        expected_missing = {"s3", "s5", "s6", "s8", "s9", "s10", "s11", "s12", "s13"}
        assert set(result.missing_sections.keys()) == expected_missing

    def test_engine_full_integration_all_rules(self, complete_tor_document: dict):
        """Full engine with all completeness and consistency rules validates correctly."""
        engine = RuleEngine()
        # Completeness rules
        engine.register_rule("completeness", SectionPresenceRule())
        engine.register_rule("completeness", RequiredSubsectionsRule())
        engine.register_rule("completeness", MinimumContentRule())
        # Consistency rules
        engine.register_rule("consistency", BudgetScopeConsistencyRule())
        engine.register_rule("consistency", TimelineDeliverablesConsistencyRule())
        engine.register_rule("consistency", QualificationsComplexityConsistencyRule())

        result = engine.validate(complete_tor_document)

        assert result.halted is False
        assert 0 <= result.quality_score <= 100
        assert len(result.categories) == 4
