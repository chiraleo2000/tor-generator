"""Property-based tests for Rule Engine Quality Score Determinism (Property 2).

Verifies that the Rule Engine is purely deterministic:
- For any TOR document content, invoking the Rule Engine multiple times with
  identical input SHALL produce identical Quality_Score values and identical
  validation findings.
- The Rule Engine contains no randomness — results depend only on input.

**Validates: Requirements 6.6, 6.7**

# Feature: tor-drafting-review-app, Property 2: Rule Engine Quality Score Determinism
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.rule_engine.engine import RuleEngine, ValidationResult
from app.rule_engine.rules.completeness import (
    MinimumContentRule,
    RequiredSubsectionsRule,
    SectionPresenceRule,
)
from app.rule_engine.rules.consistency import (
    BudgetScopeConsistencyRule,
    QualificationsComplexityConsistencyRule,
    TimelineDeliverablesConsistencyRule,
)
from app.rule_engine.rules.format import (
    SectionNumberingRule,
    SectionOrderingRule,
    ThaiDateFormatRule,
    ThaiDocumentFormatRule,
)
from app.rule_engine.rules.legal import (
    BrandLockFairnessRule,
    PenaltyRateRule,
    RequiredLegalReferencesRule,
    VendorPaidUpCapitalRule,
)
from app.rule_engine.rules.payment import PaymentScheduleRule
from app.rule_engine.rules.timeline import TimelineFeasibilityRule


# ---------------------------------------------------------------------------
# Strategies for generating random TOR documents
# ---------------------------------------------------------------------------

# Thai section content strategy - realistic Thai government text snippets
thai_section_content = st.one_of(
    st.just(""),
    st.text(
        alphabet=st.characters(
            whitelist_categories=("L", "N", "P", "Z"),
            whitelist_characters="ก-ฮๅๆ็่้๊๋์ื\n",
        ),
        min_size=0,
        max_size=500,
    ),
    st.sampled_from([
        "ตามที่หน่วยงานได้ดำเนินการจัดซื้อจัดจ้างตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560",
        "วัตถุประสงค์เพื่อพัฒนาระบบสารสนเทศสำหรับการบริหารจัดการข้อมูล",
        "ผู้เสนอราคาต้องมีทุนจดทะเบียนไม่น้อยกว่า 1,250,000 บาท มีประสบการณ์ไม่น้อยกว่า 3 ปี",
        "ขอบเขตของงานประกอบด้วยการพัฒนาระบบ Cloud AI ระบบเครือข่าย และ Data Center",
        "ระยะเวลาดำเนินการ 180 วัน นับถัดจากวันลงนามในสัญญา",
        "เกณฑ์การพิจารณาใช้ราคาและคุณภาพ โดยให้น้ำหนักด้านราคาร้อยละ 30",
        "งบประมาณ 5,000,000 บาท ตามแผนงบประมาณรายจ่ายประจำปี พ.ศ. 2567",
        "การจ่ายเงินแบ่งออกเป็น 3 งวด งวดที่ 1 ร้อยละ 30 งวดที่ 2 ร้อยละ 40 งวดที่ 3 ร้อยละ 30",
        "ค่าปรับในอัตราร้อยละ 0.10 ต่อวัน ของวงเงินตามสัญญา หรือเทียบเท่า",
        "เอกสารหลักฐานการเสนอราคาประกอบด้วยสำเนาหนังสือรับรองการจดทะเบียน",
        "สถานที่ส่งมอบงาน ณ สำนักงานใหญ่ ดังนี้",
        "การรับประกันผลงานไม่น้อยกว่า 1 ปี นับถัดจากวันตรวจรับ",
        "เงื่อนไขอื่นๆ ให้เป็นไปตามที่กำหนดในเอกสารประกวดราคา ทั้งนี้ โดย ตาม",
        "Microsoft Windows Server หรือเทียบเท่า",
        "1. รายการที่หนึ่ง\n2. รายการที่สอง\n3. รายการที่สาม",
        "๑. หัวข้อแรก\n๒. หัวข้อที่สอง",
    ]),
)

# Budget strategy - positive integers in typical range
budget_strategy = st.one_of(
    st.none(),
    st.integers(min_value=100_000, max_value=10_000_000_000),
)

# Timeline days strategy
timeline_strategy = st.one_of(
    st.none(),
    st.integers(min_value=30, max_value=730),
)

# Project type strategy
project_type_strategy = st.one_of(
    st.none(),
    st.sampled_from(["it", "construction", "consulting", "general"]),
)

# Payment installments strategy
payment_installments_strategy = st.one_of(
    st.none(),
    st.lists(
        st.floats(min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=10,
    ),
)

# Penalty rate strategy
penalty_rate_strategy = st.one_of(
    st.none(),
    st.floats(min_value=0.001, max_value=0.5, allow_nan=False, allow_infinity=False),
)

# Vendor capital strategy
vendor_capital_strategy = st.one_of(
    st.none(),
    st.integers(min_value=10_000, max_value=2_500_000_000),
)

# Section order strategy
section_order_strategy = st.one_of(
    st.none(),
    st.permutations([f"s{i}" for i in range(1, 14)]),
)


@st.composite
def tor_document_strategy(draw):
    """Generate a random TOR document with varying sections and metadata.

    The generated document may be valid or invalid — the purpose is to verify
    that the Rule Engine produces deterministic results regardless of input.
    """
    doc = {}

    # Generate section content (s1..s13)
    for i in range(1, 14):
        # Randomly include or exclude sections
        include = draw(st.booleans())
        if include:
            doc[f"s{i}"] = draw(thai_section_content)

    # Add metadata fields
    budget = draw(budget_strategy)
    if budget is not None:
        doc["budget"] = budget

    timeline_days = draw(timeline_strategy)
    if timeline_days is not None:
        doc["timeline_days"] = timeline_days

    project_type = draw(project_type_strategy)
    if project_type is not None:
        doc["project_type"] = project_type

    payment_installments = draw(payment_installments_strategy)
    if payment_installments is not None:
        doc["payment_installments"] = payment_installments

    penalty_rate = draw(penalty_rate_strategy)
    if penalty_rate is not None:
        doc["penalty_rate_percent"] = penalty_rate

    vendor_capital = draw(vendor_capital_strategy)
    if vendor_capital is not None:
        doc["vendor_capital"] = vendor_capital

    # Optionally add section_order metadata
    section_order = draw(section_order_strategy)
    if section_order is not None:
        doc["section_order"] = list(section_order)

    # Optionally add document title
    include_title = draw(st.booleans())
    if include_title:
        doc["title"] = draw(
            st.sampled_from([
                "ขอบเขตของงาน (TOR) โครงการจัดหาระบบสารสนเทศ",
                "Terms of Reference: โครงการก่อสร้างอาคาร",
                "",
            ])
        )

    return doc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_fully_loaded_engine() -> RuleEngine:
    """Create a Rule Engine with ALL rules registered across all categories.

    This ensures the determinism property is tested against the full
    validation pipeline, not just a subset.
    """
    engine = RuleEngine()

    # Legal rules (40% weight)
    engine.register_rule("legal", VendorPaidUpCapitalRule())
    engine.register_rule("legal", PenaltyRateRule())
    engine.register_rule("legal", BrandLockFairnessRule())
    engine.register_rule("legal", RequiredLegalReferencesRule())
    engine.register_rule("legal", PaymentScheduleRule())

    # Completeness rules (30% weight)
    engine.register_rule("completeness", SectionPresenceRule())
    engine.register_rule("completeness", RequiredSubsectionsRule())
    engine.register_rule("completeness", MinimumContentRule())

    # Consistency rules (20% weight)
    engine.register_rule("consistency", BudgetScopeConsistencyRule())
    engine.register_rule("consistency", TimelineDeliverablesConsistencyRule())
    engine.register_rule("consistency", QualificationsComplexityConsistencyRule())

    # Format rules (10% weight)
    engine.register_rule("format", ThaiDateFormatRule())
    engine.register_rule("format", SectionNumberingRule())
    engine.register_rule("format", SectionOrderingRule())
    engine.register_rule("format", ThaiDocumentFormatRule())

    return engine


def results_are_identical(result1: ValidationResult, result2: ValidationResult) -> bool:
    """Compare two ValidationResult objects for full equality.

    Checks: quality_score, is_valid, halted, missing_sections,
    all category scores, and all findings (in order).
    """
    if result1.quality_score != result2.quality_score:
        return False
    if result1.is_valid != result2.is_valid:
        return False
    if result1.halted != result2.halted:
        return False
    if result1.missing_sections != result2.missing_sections:
        return False
    if len(result1.categories) != len(result2.categories):
        return False
    if len(result1.findings) != len(result2.findings):
        return False

    # Compare categories
    for cs1, cs2 in zip(result1.categories, result2.categories):
        if cs1.category != cs2.category:
            return False
        if cs1.score != cs2.score:
            return False
        if cs1.weight != cs2.weight:
            return False
        if len(cs1.findings) != len(cs2.findings):
            return False

    # Compare findings
    for f1, f2 in zip(result1.findings, result2.findings):
        if f1.severity != f2.severity:
            return False
        if f1.rule_violated != f2.rule_violated:
            return False
        if f1.affected_section != f2.affected_section:
            return False
        if f1.message != f2.message:
            return False
        if f1.recommended_correction != f2.recommended_correction:
            return False

    return True


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestRuleEngineQualityScoreDeterminism:
    """Property 2: Rule Engine Quality Score Determinism.

    For any TOR document content, invoking the Rule Engine multiple times with
    identical input SHALL produce identical Quality_Score values and identical
    validation findings — the Rule Engine is purely deterministic with no randomness.
    """

    @given(tor_doc=tor_document_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 2: Rule Engine Quality Score Determinism
    def test_same_input_produces_same_quality_score(self, tor_doc: dict):
        """For any TOR document, two invocations produce identical quality_score.

        **Validates: Requirements 6.6, 6.7**
        """
        engine = create_fully_loaded_engine()

        result1 = engine.validate(tor_doc)
        result2 = engine.validate(tor_doc)

        assert result1.quality_score == result2.quality_score

    @given(tor_doc=tor_document_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 2: Rule Engine Quality Score Determinism
    def test_same_input_produces_same_findings(self, tor_doc: dict):
        """For any TOR document, two invocations produce identical findings list.

        **Validates: Requirements 6.6, 6.7**
        """
        engine = create_fully_loaded_engine()

        result1 = engine.validate(tor_doc)
        result2 = engine.validate(tor_doc)

        assert len(result1.findings) == len(result2.findings)
        for f1, f2 in zip(result1.findings, result2.findings):
            assert f1.severity == f2.severity
            assert f1.rule_violated == f2.rule_violated
            assert f1.affected_section == f2.affected_section
            assert f1.message == f2.message
            assert f1.recommended_correction == f2.recommended_correction

    @given(tor_doc=tor_document_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 2: Rule Engine Quality Score Determinism
    def test_multiple_invocations_fully_identical(self, tor_doc: dict):
        """For any TOR document, 5 consecutive invocations produce fully identical results.

        Checks quality_score, is_valid, halted, categories, and all findings.

        **Validates: Requirements 6.6, 6.7**
        """
        engine = create_fully_loaded_engine()

        first_result = engine.validate(tor_doc)

        for _ in range(4):
            subsequent_result = engine.validate(tor_doc)
            assert results_are_identical(first_result, subsequent_result), (
                f"Non-deterministic result detected: "
                f"score {first_result.quality_score} vs {subsequent_result.quality_score}, "
                f"findings count {len(first_result.findings)} vs {len(subsequent_result.findings)}"
            )

    @given(tor_doc=tor_document_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 2: Rule Engine Quality Score Determinism
    def test_separate_engine_instances_produce_same_result(self, tor_doc: dict):
        """For any TOR document, two separately constructed engines produce identical results.

        This verifies that determinism does not depend on engine instance state.

        **Validates: Requirements 6.6, 6.7**
        """
        engine1 = create_fully_loaded_engine()
        engine2 = create_fully_loaded_engine()

        result1 = engine1.validate(tor_doc)
        result2 = engine2.validate(tor_doc)

        assert results_are_identical(result1, result2), (
            f"Different engine instances produced different results: "
            f"score {result1.quality_score} vs {result2.quality_score}"
        )
