"""Property-based tests for Quality Score Bounded Range (Property 9).

Verifies that for any TOR document:
- The Quality_Score produced by the Rule Engine is an integer in [0, 100].
- The weighted breakdown (legal 40% + completeness 30% + consistency 20% + format 10%)
  sums to the total score.

**Validates: Requirements 6.6**

# Feature: tor-drafting-review-app, Property 9: Quality Score Bounded Range
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.rule_engine.engine import (
    CATEGORY_WEIGHTS,
    RuleEngine,
)
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
        "การรับประกันผลงานไม่น้อยกว่า 1 ปี นับถัดจากวันตรวจรับ",
        "Microsoft Windows Server หรือเทียบเท่า",
        "1. รายการที่หนึ่ง\n2. รายการที่สอง\n3. รายการที่สาม",
        "๑. หัวข้อแรก\n๒. หัวข้อที่สอง",
    ]),
)

budget_strategy = st.one_of(
    st.none(),
    st.integers(min_value=100_000, max_value=10_000_000_000),
)

timeline_strategy = st.one_of(
    st.none(),
    st.integers(min_value=30, max_value=730),
)

project_type_strategy = st.one_of(
    st.none(),
    st.sampled_from(["it", "construction", "consulting", "general"]),
)

payment_installments_strategy = st.one_of(
    st.none(),
    st.lists(
        st.floats(min_value=5.0, max_value=50.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=10,
    ),
)

penalty_rate_strategy = st.one_of(
    st.none(),
    st.floats(min_value=0.001, max_value=0.5, allow_nan=False, allow_infinity=False),
)

vendor_capital_strategy = st.one_of(
    st.none(),
    st.integers(min_value=10_000, max_value=2_500_000_000),
)

section_order_strategy = st.one_of(
    st.none(),
    st.permutations([f"s{i}" for i in range(1, 14)]),
)


@st.composite
def tor_document_strategy(draw):
    """Generate a random TOR document with varying sections and metadata.

    The generated document may be valid or invalid — the property must hold
    regardless of document validity.
    """
    doc = {}

    # Generate section content (s1..s13)
    for i in range(1, 14):
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

    section_order = draw(section_order_strategy)
    if section_order is not None:
        doc["section_order"] = list(section_order)

    return doc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def create_fully_loaded_engine() -> RuleEngine:
    """Create a Rule Engine with ALL rules registered across all categories."""
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


# ---------------------------------------------------------------------------
# Property Tests
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestQualityScoreBoundedRange:
    """Property 9: Quality Score Bounded Range.

    For any TOR document, the Quality_Score produced by the Rule Engine SHALL
    be an integer in the range [0, 100], and the weighted breakdown
    (legal 40% + completeness 30% + consistency 20% + format 10%) SHALL sum
    to the total score.
    """

    @given(tor_doc=tor_document_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 9: Quality Score Bounded Range
    def test_quality_score_is_integer_in_0_to_100(self, tor_doc: dict):
        """For any TOR document, quality_score is an integer in [0, 100].

        **Validates: Requirements 6.6**
        """
        engine = create_fully_loaded_engine()
        result = engine.validate(tor_doc)

        assert isinstance(result.quality_score, int), (
            f"quality_score must be int, got {type(result.quality_score)}"
        )
        assert 0 <= result.quality_score <= 100, (
            f"quality_score must be in [0, 100], got {result.quality_score}"
        )

    @given(tor_doc=tor_document_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 9: Quality Score Bounded Range
    def test_weighted_breakdown_sums_to_total_score(self, tor_doc: dict):
        """For any TOR document, the weighted category breakdown sums to the total score.

        Formula: total = round(sum(category_score * category_weight))
        The total must equal quality_score (both clamped to [0, 100]).

        **Validates: Requirements 6.6**
        """
        engine = create_fully_loaded_engine()
        result = engine.validate(tor_doc)

        # If halted (missing required sections), categories may be empty
        if result.halted:
            assert result.quality_score == 0
            return

        # Compute weighted sum from category breakdown
        weighted_sum = 0.0
        for cs in result.categories:
            weighted_sum += cs.score * cs.weight

        expected_score = max(0, min(100, round(weighted_sum)))

        assert result.quality_score == expected_score, (
            f"Weighted breakdown sum ({expected_score}) does not match "
            f"quality_score ({result.quality_score}). "
            f"Categories: {[(c.category, c.score, c.weight) for c in result.categories]}"
        )

    @given(tor_doc=tor_document_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 9: Quality Score Bounded Range
    def test_each_category_score_in_0_to_100(self, tor_doc: dict):
        """For any TOR document, each category score is in [0, 100].

        **Validates: Requirements 6.6**
        """
        engine = create_fully_loaded_engine()
        result = engine.validate(tor_doc)

        if result.halted:
            return

        for cs in result.categories:
            assert 0.0 <= cs.score <= 100.0, (
                f"Category '{cs.category}' score must be in [0, 100], got {cs.score}"
            )

    @given(tor_doc=tor_document_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 9: Quality Score Bounded Range
    def test_category_weights_match_specification(self, tor_doc: dict):
        """For any TOR document, category weights are legal=0.4, completeness=0.3,
        consistency=0.2, format=0.1.

        **Validates: Requirements 6.6**
        """
        engine = create_fully_loaded_engine()
        result = engine.validate(tor_doc)

        if result.halted:
            return

        expected_weights = {
            "legal": 0.40,
            "completeness": 0.30,
            "consistency": 0.20,
            "format": 0.10,
        }

        # Verify all 4 categories are present with correct weights
        assert len(result.categories) == 4, (
            f"Expected 4 categories, got {len(result.categories)}"
        )

        for cs in result.categories:
            assert cs.category in expected_weights, (
                f"Unexpected category '{cs.category}'"
            )
            assert cs.weight == expected_weights[cs.category], (
                f"Category '{cs.category}' weight should be "
                f"{expected_weights[cs.category]}, got {cs.weight}"
            )

    @given(tor_doc=tor_document_strategy())
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 9: Quality Score Bounded Range
    def test_weights_sum_to_one(self, tor_doc: dict):
        """For any TOR document result, the category weights sum to exactly 1.0.

        **Validates: Requirements 6.6**
        """
        engine = create_fully_loaded_engine()
        result = engine.validate(tor_doc)

        if result.halted:
            return

        total_weight = sum(cs.weight for cs in result.categories)
        assert abs(total_weight - 1.0) < 1e-9, (
            f"Category weights must sum to 1.0, got {total_weight}"
        )
