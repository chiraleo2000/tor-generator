"""Unit tests for the Rule Engine core framework and scoring algorithm.

Tests cover:
- Quality score calculation with no findings (perfect 100)
- Score deductions per severity level
- Weighted category scoring
- is_valid threshold (>= 70)
- Determinism (same input → same output)
- Rule registration and validation
- Edge cases (score floor, multiple categories)
"""

from __future__ import annotations

import pytest

from app.rule_engine.engine import (
    CATEGORY_WEIGHTS,
    PASSING_THRESHOLD,
    SEVERITY_DEDUCTIONS,
    CategoryScore,
    Finding,
    RuleEngine,
    Severity,
    ValidationResult,
)
from app.rule_engine.rules.base import BaseRule


# --- Helper: Concrete rule implementations for testing ---


class AlwaysPassRule(BaseRule):
    """A rule that never produces findings (always passes)."""

    def validate(self, tor_document: dict) -> list[Finding]:
        return []


class SingleErrorRule(BaseRule):
    """A rule that always produces one ERROR finding."""

    def validate(self, tor_document: dict) -> list[Finding]:
        return [
            Finding(
                severity=Severity.ERROR,
                rule_violated="TEST_ERROR_001",
                affected_section="s1",
                message="ข้อผิดพลาดทดสอบ",
                recommended_correction="แก้ไขเนื้อหาส่วนนี้",
            )
        ]


class SingleWarningRule(BaseRule):
    """A rule that always produces one WARNING finding."""

    def validate(self, tor_document: dict) -> list[Finding]:
        return [
            Finding(
                severity=Severity.WARNING,
                rule_violated="TEST_WARNING_001",
                affected_section="s2",
                message="คำเตือนทดสอบ",
            )
        ]


class SingleSuggestionRule(BaseRule):
    """A rule that always produces one SUGGESTION finding."""

    def validate(self, tor_document: dict) -> list[Finding]:
        return [
            Finding(
                severity=Severity.SUGGESTION,
                rule_violated="TEST_SUGGESTION_001",
                affected_section="s3",
                message="ข้อเสนอแนะทดสอบ",
                recommended_correction="ปรับปรุงรูปแบบ",
            )
        ]


class MultipleErrorsRule(BaseRule):
    """A rule that produces multiple ERROR findings to test score floor."""

    def validate(self, tor_document: dict) -> list[Finding]:
        return [
            Finding(
                severity=Severity.ERROR,
                rule_violated=f"TEST_ERROR_{i:03d}",
                affected_section=f"s{i}",
                message=f"ข้อผิดพลาดที่ {i}",
            )
            for i in range(1, 7)  # 6 errors → -120 deduction → floor at 0
        ]


class ConditionalRule(BaseRule):
    """A rule that checks for a specific key in the document."""

    def validate(self, tor_document: dict) -> list[Finding]:
        findings: list[Finding] = []
        if "budget" not in tor_document:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_violated="BUDGET_MISSING",
                    affected_section="metadata",
                    message="ไม่พบข้อมูลงบประมาณ",
                    recommended_correction="ระบุงบประมาณในข้อมูลโครงการ",
                )
            )
        return findings


# --- Fixtures ---


@pytest.fixture
def engine() -> RuleEngine:
    """Create a fresh RuleEngine instance with no rules registered."""
    return RuleEngine()


@pytest.fixture
def sample_tor_document() -> dict:
    """A minimal valid TOR document for testing."""
    return {
        "s1": "ความเป็นมาของโครงการ...",
        "s2": "วัตถุประสงค์ของโครงการ...",
        "s3": "คุณสมบัติผู้เสนอราคา...",
        "s4": "ขอบเขตของงาน...",
        "s5": "ระยะเวลาดำเนินงาน...",
        "s6": "งบประมาณ...",
        "s7": "เงื่อนไขการชำระเงิน...",
        "s8": "หลักเกณฑ์การพิจารณา...",
        "s9": "การรับประกัน...",
        "s10": "ค่าปรับ...",
        "s11": "เอกสารประกอบ...",
        "s12": "เงื่อนไขอื่นๆ...",
        "s13": "ภาคผนวก...",
        "budget": 5_000_000,
        "project_type": "it",
        "timeline_days": 180,
    }


# --- Tests: Quality Score with no findings ---


class TestQualityScoreNoFindings:
    """Test that a document with no rule violations scores 100."""

    def test_no_rules_returns_perfect_score(self, engine: RuleEngine, sample_tor_document: dict):
        """An engine with no rules registered produces a perfect score."""
        result = engine.validate(sample_tor_document)
        assert result.quality_score == 100
        assert result.is_valid is True

    def test_all_pass_rules_returns_perfect_score(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """An engine where all rules pass produces a perfect score."""
        engine.register_rule("legal", AlwaysPassRule())
        engine.register_rule("completeness", AlwaysPassRule())
        engine.register_rule("consistency", AlwaysPassRule())
        engine.register_rule("format", AlwaysPassRule())

        result = engine.validate(sample_tor_document)
        assert result.quality_score == 100
        assert result.is_valid is True
        assert len(result.findings) == 0

    def test_perfect_score_has_all_categories_at_100(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """All category scores should be 100 when there are no findings."""
        result = engine.validate(sample_tor_document)
        for cs in result.categories:
            assert cs.score == 100.0


# --- Tests: Score deductions per severity ---


class TestSeverityDeductions:
    """Test score deductions based on finding severity levels."""

    def test_error_deducts_20_points(self, engine: RuleEngine, sample_tor_document: dict):
        """A single ERROR in legal category deducts 20 from that category."""
        engine.register_rule("legal", SingleErrorRule())
        result = engine.validate(sample_tor_document)

        legal_category = next(cs for cs in result.categories if cs.category == "legal")
        assert legal_category.score == 80.0  # 100 - 20

    def test_warning_deducts_10_points(self, engine: RuleEngine, sample_tor_document: dict):
        """A single WARNING deducts 10 from that category."""
        engine.register_rule("completeness", SingleWarningRule())
        result = engine.validate(sample_tor_document)

        completeness_category = next(
            cs for cs in result.categories if cs.category == "completeness"
        )
        assert completeness_category.score == 90.0  # 100 - 10

    def test_suggestion_deducts_5_points(self, engine: RuleEngine, sample_tor_document: dict):
        """A single SUGGESTION deducts 5 from that category."""
        engine.register_rule("format", SingleSuggestionRule())
        result = engine.validate(sample_tor_document)

        format_category = next(cs for cs in result.categories if cs.category == "format")
        assert format_category.score == 95.0  # 100 - 5

    def test_score_floor_at_zero(self, engine: RuleEngine, sample_tor_document: dict):
        """Category score never goes below 0 even with many findings."""
        engine.register_rule("legal", MultipleErrorsRule())  # 6 errors → -120
        result = engine.validate(sample_tor_document)

        legal_category = next(cs for cs in result.categories if cs.category == "legal")
        assert legal_category.score == 0.0

    def test_multiple_severities_cumulative(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """Multiple findings of different severities deduct cumulatively."""
        engine.register_rule("legal", SingleErrorRule())  # -20
        engine.register_rule("legal", SingleWarningRule())  # -10
        engine.register_rule("legal", SingleSuggestionRule())  # -5

        result = engine.validate(sample_tor_document)

        legal_category = next(cs for cs in result.categories if cs.category == "legal")
        assert legal_category.score == 65.0  # 100 - 20 - 10 - 5


# --- Tests: Weighted category scoring ---


class TestWeightedScoring:
    """Test the weighted total score calculation."""

    def test_category_weights_sum_to_one(self):
        """Category weights must sum to 1.0."""
        total = sum(CATEGORY_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-10

    def test_single_category_error_affects_total_proportionally(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """An error in legal (40% weight) reduces total by 20 * 0.4 = 8 points."""
        engine.register_rule("legal", SingleErrorRule())
        result = engine.validate(sample_tor_document)

        # Legal: 80, others: 100
        # Total = 80*0.4 + 100*0.3 + 100*0.2 + 100*0.1 = 32 + 30 + 20 + 10 = 92
        assert result.quality_score == 92

    def test_error_in_format_has_less_impact(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """An error in format (10% weight) reduces total by 20 * 0.1 = 2 points."""
        engine.register_rule("format", SingleErrorRule())
        result = engine.validate(sample_tor_document)

        # Format: 80, others: 100
        # Total = 100*0.4 + 100*0.3 + 100*0.2 + 80*0.1 = 40 + 30 + 20 + 8 = 98
        assert result.quality_score == 98

    def test_errors_in_all_categories(self, engine: RuleEngine, sample_tor_document: dict):
        """Errors spread across all categories compound weighted impact."""
        engine.register_rule("legal", SingleErrorRule())  # legal: 80
        engine.register_rule("completeness", SingleErrorRule())  # completeness: 80
        engine.register_rule("consistency", SingleErrorRule())  # consistency: 80
        engine.register_rule("format", SingleErrorRule())  # format: 80

        result = engine.validate(sample_tor_document)

        # 80*0.4 + 80*0.3 + 80*0.2 + 80*0.1 = 32 + 24 + 16 + 8 = 80
        assert result.quality_score == 80

    def test_zero_category_score_with_many_errors(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """Legal at 0 (40% weight) means max contribution from others is 60."""
        engine.register_rule("legal", MultipleErrorsRule())  # legal: 0
        result = engine.validate(sample_tor_document)

        # 0*0.4 + 100*0.3 + 100*0.2 + 100*0.1 = 0 + 30 + 20 + 10 = 60
        assert result.quality_score == 60


# --- Tests: is_valid threshold ---


class TestIsValidThreshold:
    """Test the is_valid flag based on the 70-point threshold."""

    def test_score_100_is_valid(self, engine: RuleEngine, sample_tor_document: dict):
        """Score 100 is valid."""
        result = engine.validate(sample_tor_document)
        assert result.is_valid is True

    def test_score_exactly_70_is_valid(self, engine: RuleEngine, sample_tor_document: dict):
        """Score exactly at threshold (70) is valid."""
        # Need to create a scenario where total = 70 exactly
        # Legal errors reducing total to 70:
        # We need total weighted = 70
        # If legal=25: 25*0.4 + 100*0.3 + 100*0.2 + 100*0.1 = 10 + 30 + 20 + 10 = 70
        # legal=25 means -75 deduction → impossible with ERROR=-20 (need 3.75 errors)
        # If legal=50, completeness=50:
        # 50*0.4 + 50*0.3 + 100*0.2 + 100*0.1 = 20 + 15 + 20 + 10 = 65 (too low)
        # If legal=75, completeness=50:
        # 75*0.4 + 50*0.3 + 100*0.2 + 100*0.1 = 30 + 15 + 20 + 10 = 75 (too high)
        # If legal=60, completeness=80:
        # 60*0.4 + 80*0.3 + 100*0.2 + 100*0.1 = 24 + 24 + 20 + 10 = 78 (too high)
        # Let's use: legal=80, completeness=60, consistency=50, format=100
        # 80*0.4 + 60*0.3 + 50*0.2 + 100*0.1 = 32 + 18 + 10 + 10 = 70 ✓
        # legal=80: 1 error; completeness=60: 2 errors or 4 warnings; consistency=50: 2.5 errors
        # Let's use: legal: 1 error (80), completeness: 4 warnings (60), consistency: 5 warnings (50)
        engine.register_rule("legal", SingleErrorRule())  # -20 → 80

        class FourWarningsRule(BaseRule):
            def validate(self, tor_document: dict) -> list[Finding]:
                return [
                    Finding(Severity.WARNING, "W1", "s1", "w1"),
                    Finding(Severity.WARNING, "W2", "s2", "w2"),
                    Finding(Severity.WARNING, "W3", "s3", "w3"),
                    Finding(Severity.WARNING, "W4", "s4", "w4"),
                ]

        class FiveWarningsRule(BaseRule):
            def validate(self, tor_document: dict) -> list[Finding]:
                return [
                    Finding(Severity.WARNING, f"W{i}", f"s{i}", f"w{i}")
                    for i in range(1, 6)
                ]

        engine.register_rule("completeness", FourWarningsRule())  # -40 → 60
        engine.register_rule("consistency", FiveWarningsRule())  # -50 → 50

        result = engine.validate(sample_tor_document)
        # 80*0.4 + 60*0.3 + 50*0.2 + 100*0.1 = 32 + 18 + 10 + 10 = 70
        assert result.quality_score == 70
        assert result.is_valid is True

    def test_score_below_70_is_not_valid(self, engine: RuleEngine, sample_tor_document: dict):
        """Score below threshold is not valid."""
        engine.register_rule("legal", MultipleErrorsRule())  # legal: 0
        result = engine.validate(sample_tor_document)

        # 0*0.4 + 100*0.3 + 100*0.2 + 100*0.1 = 60
        assert result.quality_score == 60
        assert result.is_valid is False

    def test_passing_threshold_constant(self):
        """Verify the passing threshold is 70."""
        assert PASSING_THRESHOLD == 70


# --- Tests: Determinism ---


class TestDeterminism:
    """Test that the Rule Engine produces identical results for identical input."""

    def test_same_input_same_output(self, engine: RuleEngine, sample_tor_document: dict):
        """Multiple invocations with same input produce identical results."""
        engine.register_rule("legal", SingleErrorRule())
        engine.register_rule("completeness", SingleWarningRule())
        engine.register_rule("format", SingleSuggestionRule())

        result1 = engine.validate(sample_tor_document)
        result2 = engine.validate(sample_tor_document)

        assert result1.quality_score == result2.quality_score
        assert result1.is_valid == result2.is_valid
        assert len(result1.findings) == len(result2.findings)
        assert len(result1.categories) == len(result2.categories)

        for cs1, cs2 in zip(result1.categories, result2.categories):
            assert cs1.category == cs2.category
            assert cs1.score == cs2.score
            assert cs1.weight == cs2.weight

    def test_determinism_across_100_invocations(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """100 invocations all produce the same quality_score."""
        engine.register_rule("legal", SingleErrorRule())
        engine.register_rule("completeness", ConditionalRule())

        scores = [engine.validate(sample_tor_document).quality_score for _ in range(100)]
        assert all(s == scores[0] for s in scores)

    def test_different_input_different_output(self, engine: RuleEngine):
        """Different documents can produce different results (not stuck on one value)."""
        engine.register_rule("legal", ConditionalRule())

        doc_with_budget = {"budget": 1_000_000}
        doc_without_budget = {"s1": "test"}

        result_with = engine.validate(doc_with_budget)
        result_without = engine.validate(doc_without_budget)

        assert result_with.quality_score != result_without.quality_score


# --- Tests: Rule registration ---


class TestRuleRegistration:
    """Test rule registration and category validation."""

    def test_register_rule_to_valid_category(self, engine: RuleEngine):
        """Rules can be registered to all valid categories."""
        for category in ["legal", "completeness", "consistency", "format"]:
            engine.register_rule(category, AlwaysPassRule())

    def test_register_rule_to_invalid_category_raises(self, engine: RuleEngine):
        """Registering a rule to an invalid category raises ValueError."""
        rule = AlwaysPassRule()
        with pytest.raises(ValueError, match="Unknown category"):
            engine.register_rule("nonexistent", rule)

    def test_multiple_rules_per_category(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """Multiple rules in the same category have cumulative deductions."""
        engine.register_rule("legal", SingleErrorRule())  # -20
        engine.register_rule("legal", SingleWarningRule())  # -10

        result = engine.validate(sample_tor_document)
        legal_category = next(cs for cs in result.categories if cs.category == "legal")
        assert legal_category.score == 70.0  # 100 - 20 - 10


# --- Tests: ValidationResult structure ---


class TestValidationResultStructure:
    """Test the structure and contents of ValidationResult."""

    def test_result_contains_all_four_categories(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """Validation result always has exactly 4 category scores."""
        result = engine.validate(sample_tor_document)
        assert len(result.categories) == 4
        category_names = {cs.category for cs in result.categories}
        assert category_names == {"legal", "completeness", "consistency", "format"}

    def test_category_weights_match_design(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """Category weights match the design specification."""
        result = engine.validate(sample_tor_document)
        weight_map = {cs.category: cs.weight for cs in result.categories}
        assert weight_map["legal"] == 0.40
        assert weight_map["completeness"] == 0.30
        assert weight_map["consistency"] == 0.20
        assert weight_map["format"] == 0.10

    def test_findings_include_all_required_fields(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """Each finding has severity, rule_violated, affected_section, and message."""
        engine.register_rule("legal", SingleErrorRule())
        result = engine.validate(sample_tor_document)

        assert len(result.findings) == 1
        finding = result.findings[0]
        assert finding.severity == Severity.ERROR
        assert finding.rule_violated == "TEST_ERROR_001"
        assert finding.affected_section == "s1"
        assert finding.message == "ข้อผิดพลาดทดสอบ"
        assert finding.recommended_correction == "แก้ไขเนื้อหาส่วนนี้"

    def test_finding_without_recommended_correction(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """Findings may have None for recommended_correction."""
        engine.register_rule("completeness", SingleWarningRule())
        result = engine.validate(sample_tor_document)

        finding = result.findings[0]
        assert finding.recommended_correction is None

    def test_findings_aggregated_from_all_categories(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """All findings from all categories appear in result.findings."""
        engine.register_rule("legal", SingleErrorRule())
        engine.register_rule("completeness", SingleWarningRule())
        engine.register_rule("format", SingleSuggestionRule())

        result = engine.validate(sample_tor_document)
        assert len(result.findings) == 3

    def test_quality_score_bounded_0_to_100(
        self, engine: RuleEngine, sample_tor_document: dict
    ):
        """Quality score is always between 0 and 100 inclusive."""
        # Test with max deductions
        engine.register_rule("legal", MultipleErrorsRule())
        engine.register_rule("completeness", MultipleErrorsRule())
        engine.register_rule("consistency", MultipleErrorsRule())
        engine.register_rule("format", MultipleErrorsRule())

        result = engine.validate(sample_tor_document)
        assert 0 <= result.quality_score <= 100


# --- Tests: Severity enum ---


class TestSeverityEnum:
    """Test the Severity enumeration values."""

    def test_severity_values(self):
        """Severity enum has correct string values."""
        assert Severity.ERROR == "error"
        assert Severity.WARNING == "warning"
        assert Severity.SUGGESTION == "suggestion"

    def test_severity_deductions_defined(self):
        """All severity levels have defined deduction values."""
        assert SEVERITY_DEDUCTIONS[Severity.ERROR] == 20.0
        assert SEVERITY_DEDUCTIONS[Severity.WARNING] == 10.0
        assert SEVERITY_DEDUCTIONS[Severity.SUGGESTION] == 5.0
