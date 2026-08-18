"""Unit tests for format adherence rules.

Tests cover:
- Thai date format (พ.ศ.) validation
- Section numbering consistency (Thai/Arabic digits)
- Section ordering per procurement law standard
- General Thai document format conventions
- Integration with Rule Engine framework
"""

from __future__ import annotations

import pytest

from app.rule_engine.engine import Finding, RuleEngine, Severity  # noqa: F401
from app.rule_engine.rules.format import (
    SectionNumberingRule,
    SectionOrderingRule,
    ThaiDateFormatRule,
    ThaiDocumentFormatRule,
    get_format_rules,
)

# --- Fixtures ---


@pytest.fixture
def date_rule() -> ThaiDateFormatRule:
    """Create a ThaiDateFormatRule instance."""
    return ThaiDateFormatRule()


@pytest.fixture
def numbering_rule() -> SectionNumberingRule:
    """Create a SectionNumberingRule instance."""
    return SectionNumberingRule()


@pytest.fixture
def ordering_rule() -> SectionOrderingRule:
    """Create a SectionOrderingRule instance."""
    return SectionOrderingRule()


@pytest.fixture
def format_rule() -> ThaiDocumentFormatRule:
    """Create a ThaiDocumentFormatRule instance."""
    return ThaiDocumentFormatRule()


@pytest.fixture
def valid_tor_document() -> dict:
    """A TOR document with proper Thai government formatting."""
    return {
        "title": "ขอบเขตของงาน (Terms of Reference: TOR) โครงการจัดซื้อระบบ IT",
        "s1": (
            "ตามที่กระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม "
            "ได้ดำเนินโครงการพัฒนาระบบสารสนเทศ ตามแผนแม่บท "
            "เทคโนโลยีสารสนเทศ พ.ศ. 2565-2570 ทั้งนี้ "
            "จึงมีความจำเป็นต้องจัดซื้อระบบคอมพิวเตอร์เพิ่มเติม"
        ),
        "s2": (
            "๑. เพื่อพัฒนาระบบสารสนเทศให้มีประสิทธิภาพและรองรับการทำงาน\n"
            "๒. เพื่อรองรับการทำงานของเจ้าหน้าที่ในหน่วยงานภาครัฐ\n"
            "๓. เพื่อให้บริการประชาชนได้อย่างมีประสิทธิภาพยิ่งขึ้น"
        ),
        "s3": (
            "๑. เป็นนิติบุคคลที่จดทะเบียนในประเทศไทยมาแล้วไม่น้อยกว่าสามปี\n"
            "๒. มีทุนจดทะเบียนชำระแล้วไม่น้อยกว่าหนึ่งล้านสองแสนห้าหมื่นบาท\n"
            "๓. ไม่เป็นผู้ถูกแจ้งเวียนชื่อเป็นผู้ทิ้งงานของทางราชการ"
        ),
        "s4": (
            "ขอบเขตของงานครอบคลุมการจัดหาระบบคอมพิวเตอร์พร้อมติดตั้ง "
            "ณ สำนักงานกระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม"
        ),
        "s5": (
            "ระยะเวลาดำเนินงานทั้งสิ้น 180 วันปฏิทิน นับถัดจากวันลงนามในสัญญา "
            "โดยแบ่งเป็นงวดงานตามที่กำหนดในแผนงาน"
        ),
        "s6": "งบประมาณทั้งสิ้นไม่เกิน 5,000,000 บาท (ห้าล้านบาทถ้วน) รวมภาษีมูลค่าเพิ่มแล้ว",
        "s7": (
            "สถานที่ดำเนินการ: สำนักงานกระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม "
            "ตามที่ผู้ว่าจ้างกำหนด"
        ),
        "s8": (
            "แบ่งการจ่ายเงินเป็นจำนวน 3 งวด ตามผลงานที่ส่งมอบ "
            "และผ่านการตรวจรับจากคณะกรรมการตรวจรับพัสดุ"
        ),
        "s9": (
            "ผู้รับจ้างต้องรับประกันผลงานไม่น้อยกว่า 1 ปี "
            "นับจากวันที่ตรวจรับมอบงานงวดสุดท้าย"
        ),
        "s10": (
            "หากผู้รับจ้างไม่สามารถส่งมอบงานได้ตามกำหนด จะปรับเป็นรายวัน "
            "ในอัตราร้อยละ 0.10 ของราคาค่าจ้างตามสัญญา แต่ไม่ต่ำกว่า 100 บาทต่อวัน"
        ),
        "s11": (
            "เกณฑ์การพิจารณาคัดเลือกผู้เสนอราคาต่ำสุดที่ผ่านเกณฑ์ "
            "ตามหลักเกณฑ์ที่กำหนดในเอกสารประกวดราคา"
        ),
        "s12": (
            "เอกสารหลักฐานประกอบการเสนอราคาตามที่กำหนดในเอกสารประกวดราคา "
            "ผู้เสนอราคาต้องยื่นเอกสารให้ครบถ้วน"
        ),
        "s13": (
            "เงื่อนไขอื่นๆ ให้เป็นไปตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้าง "
            "และการบริหารพัสดุภาครัฐ พ.ศ. 2560"
        ),
        "budget": 5_000_000,
        "project_type": "it",
        "timeline_days": 180,
        "section_order": [
            "s1", "s2", "s3", "s4", "s5", "s6",
            "s7", "s8", "s9", "s10", "s11", "s12", "s13",
        ],
    }


# --- Tests: Thai Date Format Rule ---


class TestThaiDateFormatRule:
    """Tests for Buddhist Era date validation."""

    def test_no_findings_for_be_dates(self, date_rule: ThaiDateFormatRule):
        """Documents using พ.ศ. dates should produce no findings."""
        doc = {
            "s1": "โครงการเริ่มดำเนินการเมื่อ พ.ศ. 2565 ตามแผนงาน",
            "s5": "กำหนดแล้วเสร็จภายใน 15/03/2568",
        }
        findings = date_rule.validate(doc)
        assert len(findings) == 0

    def test_flags_gregorian_year_with_ks_prefix(self, date_rule: ThaiDateFormatRule):
        """Gregorian dates with ค.ศ. prefix should be flagged."""
        doc = {
            "s1": "โครงการจัดตั้งตาม ค.ศ. 2024 เพื่อพัฒนาระบบ",
        }
        findings = date_rule.validate(doc)
        assert len(findings) >= 1
        assert any(f.rule_violated == "FORMAT_DATE_BE" for f in findings)
        assert all(f.severity == Severity.WARNING for f in findings)

    def test_flags_bare_gregorian_year(self, date_rule: ThaiDateFormatRule):
        """Bare 4-digit years starting with 19xx/20xx should be flagged."""
        doc = {
            "s1": "ตามแผนแม่บทเทคโนโลยีสารสนเทศ 2024 ถึง 2028",
        }
        findings = date_rule.validate(doc)
        assert len(findings) >= 1
        assert all(f.rule_violated == "FORMAT_DATE_BE" for f in findings)

    def test_does_not_flag_budget_numbers(self, date_rule: ThaiDateFormatRule):
        """Numeric values followed by currency indicators should not be flagged."""
        doc = {
            "s6": "งบประมาณ 2000 บาท",
            "s8": "ชำระ 2024 THB ต่อเดือน",
        }
        findings = date_rule.validate(doc)
        assert len(findings) == 0

    def test_does_not_flag_be_year_2560(self, date_rule: ThaiDateFormatRule):
        """Buddhist Era years (25xx, 26xx) should not be flagged."""
        doc = {
            "s1": "ตาม พ.ร.บ. การจัดซื้อจัดจ้าง พ.ศ. 2560",
            "s5": "ดำเนินการภายใน 30/06/2568",
        }
        findings = date_rule.validate(doc)
        assert len(findings) == 0

    def test_empty_sections_produce_no_findings(self, date_rule: ThaiDateFormatRule):
        """Empty or missing sections should not cause errors."""
        doc = {"s1": "", "s2": None, "budget": 1000000}
        findings = date_rule.validate(doc)
        assert len(findings) == 0

    def test_finding_has_recommended_correction(self, date_rule: ThaiDateFormatRule):
        """Findings should include a recommended correction."""
        doc = {"s1": "เริ่มดำเนินการ ค.ศ. 2024"}
        findings = date_rule.validate(doc)
        assert len(findings) >= 1
        assert findings[0].recommended_correction is not None
        assert "พ.ศ." in findings[0].recommended_correction

    def test_finding_identifies_correct_section(self, date_rule: ThaiDateFormatRule):
        """Finding should reference the specific section where the issue was found."""
        doc = {
            "s1": "ไม่มีวันที่",
            "s5": "ดำเนินการตาม ค.ศ. 2023 ระยะเวลา 1 ปี",
        }
        findings = date_rule.validate(doc)
        assert len(findings) >= 1
        assert findings[0].affected_section == "s5"


# --- Tests: Section Numbering Rule ---


class TestSectionNumberingRule:
    """Tests for section numbering consistency."""

    def test_consistent_thai_numbering_no_findings(
        self, numbering_rule: SectionNumberingRule
    ):
        """All-Thai numbering should produce no findings."""
        doc = {
            "s2": "๑. วัตถุประสงค์ข้อที่ 1\n๒. วัตถุประสงค์ข้อที่ 2\n๓. วัตถุประสงค์ข้อที่ 3",
            "s3": "๑. คุณสมบัติข้อที่ 1\n๒. คุณสมบัติข้อที่ 2",
        }
        findings = numbering_rule.validate(doc)
        assert len(findings) == 0

    def test_consistent_arabic_numbering_no_findings(
        self, numbering_rule: SectionNumberingRule
    ):
        """All-Arabic numbering should produce no findings."""
        doc = {
            "s2": "1. วัตถุประสงค์ข้อที่ 1\n2. วัตถุประสงค์ข้อที่ 2",
            "s3": "1. คุณสมบัติข้อที่ 1\n2. คุณสมบัติข้อที่ 2",
        }
        findings = numbering_rule.validate(doc)
        assert len(findings) == 0

    def test_mixed_numbering_within_section(self, numbering_rule: SectionNumberingRule):
        """Mixed Thai and Arabic numbering within a single section should be flagged."""
        doc = {
            "s2": "๑. วัตถุประสงค์ข้อที่ 1\n2. วัตถุประสงค์ข้อที่ 2\n๓. วัตถุประสงค์ข้อที่ 3",
        }
        findings = numbering_rule.validate(doc)
        assert len(findings) >= 1
        assert any(
            f.rule_violated == "FORMAT_NUMBERING_MIXED_SECTION" for f in findings
        )
        assert findings[0].affected_section == "s2"

    def test_inconsistent_numbering_across_sections(
        self, numbering_rule: SectionNumberingRule
    ):
        """Thai numbering in one section and Arabic in another is a suggestion."""
        doc = {
            "s2": "๑. วัตถุประสงค์\n๒. วัตถุประสงค์อื่น",
            "s3": "1. คุณสมบัติ\n2. คุณสมบัติอื่น",
        }
        findings = numbering_rule.validate(doc)
        assert len(findings) >= 1
        assert any(
            f.rule_violated == "FORMAT_NUMBERING_INCONSISTENT_DOC" for f in findings
        )
        # Cross-document inconsistency is a suggestion-level finding
        inconsistent_finding = next(
            f for f in findings if f.rule_violated == "FORMAT_NUMBERING_INCONSISTENT_DOC"
        )
        assert inconsistent_finding.severity == Severity.SUGGESTION

    def test_no_numbered_sections_no_findings(self, numbering_rule: SectionNumberingRule):
        """Sections without numbered lists should produce no findings."""
        doc = {
            "s1": "ความเป็นมาของโครงการ ไม่มีรายการ",
            "s6": "งบประมาณ 5,000,000 บาท",
        }
        findings = numbering_rule.validate(doc)
        assert len(findings) == 0

    def test_empty_document_no_findings(self, numbering_rule: SectionNumberingRule):
        """Empty document should produce no findings."""
        doc = {}
        findings = numbering_rule.validate(doc)
        assert len(findings) == 0


# --- Tests: Section Ordering Rule ---


class TestSectionOrderingRule:
    """Tests for section ordering validation."""

    def test_correct_order_no_findings(self, ordering_rule: SectionOrderingRule):
        """Sections in correct order should produce no findings."""
        doc = {
            "section_order": ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10"],
        }
        findings = ordering_rule.validate(doc)
        assert len(findings) == 0

    def test_partial_correct_order_no_findings(self, ordering_rule: SectionOrderingRule):
        """Subset of sections in correct relative order should produce no findings."""
        doc = {
            "section_order": ["s1", "s4", "s7", "s13"],
        }
        findings = ordering_rule.validate(doc)
        assert len(findings) == 0

    def test_out_of_order_sections_flagged(self, ordering_rule: SectionOrderingRule):
        """Sections in wrong order should be flagged."""
        doc = {
            "section_order": ["s1", "s4", "s2", "s3"],  # s2 after s4 is wrong
        }
        findings = ordering_rule.validate(doc)
        assert len(findings) >= 1
        assert any(f.rule_violated == "FORMAT_SECTION_ORDER" for f in findings)
        assert findings[0].severity == Severity.WARNING

    def test_reversed_order_flagged(self, ordering_rule: SectionOrderingRule):
        """Completely reversed order should be flagged."""
        doc = {
            "section_order": ["s13", "s10", "s5", "s1"],
        }
        findings = ordering_rule.validate(doc)
        assert len(findings) >= 1
        assert any(f.rule_violated == "FORMAT_SECTION_ORDER" for f in findings)

    def test_no_section_order_key_no_findings(self, ordering_rule: SectionOrderingRule):
        """Document without section_order metadata produces no findings."""
        doc = {"s1": "content", "s2": "content"}
        findings = ordering_rule.validate(doc)
        assert len(findings) == 0

    def test_finding_has_recommended_correction(self, ordering_rule: SectionOrderingRule):
        """Ordering finding should suggest the correct order."""
        doc = {
            "section_order": ["s6", "s1"],  # Budget before Background
        }
        findings = ordering_rule.validate(doc)
        assert len(findings) >= 1
        assert findings[0].recommended_correction is not None
        assert "ลำดับ" in findings[0].recommended_correction


# --- Tests: Thai Document Format Rule ---


class TestThaiDocumentFormatRule:
    """Tests for general Thai document formatting conventions."""

    def test_valid_document_minimal_findings(self, format_rule: ThaiDocumentFormatRule):
        """A well-formatted document should produce minimal findings."""
        doc = {
            "title": "ขอบเขตของงาน (TOR) โครงการจัดซื้อระบบ IT",
            "s1": (
                "ตามที่กระทรวงดิจิทัลเพื่อเศรษฐกิจและสังคม "
                "ได้ดำเนินโครงการพัฒนาระบบสารสนเทศ ทั้งนี้ "
                "จึงมีความจำเป็นต้องจัดซื้อระบบคอมพิวเตอร์เพิ่มเติม "
                "เพื่อรองรับการทำงานของเจ้าหน้าที่ในหน่วยงาน"
            ),
            "s2": "วัตถุประสงค์ของโครงการมีดังต่อไปนี้ เพื่อพัฒนาระบบงาน",
        }
        findings = format_rule.validate(doc)
        # Should not have title or formal tone issues
        assert not any(f.rule_violated == "FORMAT_MISSING_TITLE" for f in findings)
        assert not any(f.rule_violated == "FORMAT_INFORMAL_TONE" for f in findings)

    def test_missing_title_flagged(self, format_rule: ThaiDocumentFormatRule):
        """Document without title should be flagged."""
        doc = {
            "s1": "ความเป็นมาของโครงการที่ต้องการจัดซื้อระบบคอมพิวเตอร์",
        }
        findings = format_rule.validate(doc)
        assert any(f.rule_violated == "FORMAT_MISSING_TITLE" for f in findings)
        title_finding = next(
            f for f in findings if f.rule_violated == "FORMAT_MISSING_TITLE"
        )
        assert title_finding.severity == Severity.WARNING

    def test_short_section_flagged(self, format_rule: ThaiDocumentFormatRule):
        """Very short sections should be flagged as potentially incomplete."""
        doc = {
            "title": "ขอบเขตงาน TOR",
            "s1": "ความเป็นมา",  # Too short (< 50 chars)
        }
        findings = format_rule.validate(doc)
        assert any(f.rule_violated == "FORMAT_SECTION_TOO_SHORT" for f in findings)
        short_finding = next(
            f for f in findings if f.rule_violated == "FORMAT_SECTION_TOO_SHORT"
        )
        assert short_finding.severity == Severity.SUGGESTION
        assert short_finding.affected_section == "s1"

    def test_informal_tone_flagged(self, format_rule: ThaiDocumentFormatRule):
        """Background section without formal indicators should be flagged."""
        doc = {
            "title": "TOR โครงการ",
            "s1": (
                "เราต้องการซื้อระบบคอมพิวเตอร์ใหม่เพราะระบบเก่ามันเสีย "
                "แล้วก็ต้องการให้มีระบบที่ดีกว่านี้ "
                "เลยจะจัดซื้อระบบใหม่มาแทน เพราะว่าของเก่าใช้ไม่ได้แล้ว "
                "จะได้ทำงานได้สะดวกขึ้น"
            ),
        }
        findings = format_rule.validate(doc)
        assert any(f.rule_violated == "FORMAT_INFORMAL_TONE" for f in findings)

    def test_formal_tone_not_flagged(self, format_rule: ThaiDocumentFormatRule):
        """Background section with formal indicators should not be flagged for tone."""
        doc = {
            "title": "ขอบเขตของงาน",
            "s1": (
                "ตามที่สำนักงานปลัดกระทรวง ได้ดำเนินโครงการจัดหาระบบ "
                "ทั้งนี้ จึงมีความจำเป็นในการจัดซื้อจัดจ้าง "
                "เพื่อให้การดำเนินงานเป็นไปด้วยความเรียบร้อย"
            ),
        }
        findings = format_rule.validate(doc)
        assert not any(f.rule_violated == "FORMAT_INFORMAL_TONE" for f in findings)

    def test_document_title_alternative_key(self, format_rule: ThaiDocumentFormatRule):
        """'document_title' key should also be accepted."""
        doc = {
            "document_title": "ขอบเขตของงาน โครงการจัดซื้อ",
        }
        findings = format_rule.validate(doc)
        assert not any(f.rule_violated == "FORMAT_MISSING_TITLE" for f in findings)

    def test_short_background_not_checked_for_tone(
        self, format_rule: ThaiDocumentFormatRule
    ):
        """Short background (< 100 chars) is not checked for formal tone."""
        doc = {
            "title": "TOR",
            "s1": "ข้อมูลสั้นๆ ไม่ครบ",  # < 100 chars, also < 50 chars
        }
        findings = format_rule.validate(doc)
        # Should get short section warning but NOT informal tone
        assert not any(f.rule_violated == "FORMAT_INFORMAL_TONE" for f in findings)


# --- Tests: get_format_rules helper ---


class TestGetFormatRules:
    """Tests for the get_format_rules convenience function."""

    def test_returns_all_four_rules(self):
        """get_format_rules should return all 4 format rule instances."""
        rules = get_format_rules()
        assert len(rules) == 4

    def test_returns_correct_types(self):
        """get_format_rules should return instances of the correct rule classes."""
        rules = get_format_rules()
        rule_types = {type(r) for r in rules}
        expected = {
            ThaiDateFormatRule,
            SectionNumberingRule,
            SectionOrderingRule,
            ThaiDocumentFormatRule,
        }
        assert rule_types == expected

    def test_all_rules_implement_validate(self):
        """All returned rules should have a validate method."""
        rules = get_format_rules()
        doc = {"s1": "test content"}
        for rule in rules:
            result = rule.validate(doc)
            assert isinstance(result, list)


# --- Tests: Integration with Rule Engine ---


class TestFormatRulesIntegration:
    """Tests for format rules integrated with the Rule Engine."""

    def test_register_format_rules_with_engine(self):
        """Format rules can be registered with the Rule Engine."""
        engine = RuleEngine()
        for rule in get_format_rules():
            engine.register_rule("format", rule)

        # Validate a document
        doc = {
            "title": "ขอบเขตของงาน TOR",
            "s1": (
                "ตามที่หน่วยงานได้ดำเนินโครงการ ทั้งนี้ "
                "จึงมีความจำเป็นในการจัดซื้อจัดจ้าง "
                "เพื่อให้การดำเนินงานเป็นไปด้วยความเรียบร้อย"
            ),
            "s2": "๑. วัตถุประสงค์ข้อแรกของโครงการจัดซื้อจัดจ้าง\n๒. วัตถุประสงค์ข้อที่สอง",
            "s3": "๑. คุณสมบัติผู้เสนอราคาข้อที่หนึ่ง\n๒. คุณสมบัติข้อที่สอง",
            "section_order": ["s1", "s2", "s3"],
            "budget": 5_000_000,
        }
        result = engine.validate(doc)

        # Should have a valid result with format category
        format_cat = next(cs for cs in result.categories if cs.category == "format")
        assert format_cat.weight == 0.10
        assert 0 <= format_cat.score <= 100

    def test_well_formatted_document_high_format_score(self, valid_tor_document: dict):
        """A properly formatted document should have a high format score."""
        engine = RuleEngine()
        for rule in get_format_rules():
            engine.register_rule("format", rule)

        result = engine.validate(valid_tor_document)
        format_cat = next(cs for cs in result.categories if cs.category == "format")
        # Well-formatted document should score reasonably high
        assert format_cat.score >= 80

    def test_format_category_contributes_10_percent_to_total(self):
        """Format findings should affect total score by at most 10%."""
        engine = RuleEngine()
        for rule in get_format_rules():
            engine.register_rule("format", rule)

        # A completely non-compliant format with other categories empty
        bad_doc = {
            "s1": "short",
            "s2": "short",
            "s3": "short",
            "section_order": ["s3", "s1", "s2"],
        }
        result = engine.validate(bad_doc)

        # Even with 0 format score, total should be at least 90
        # (because other categories have no rules → score 100)
        # Total = 100*0.4 + 100*0.3 + 100*0.2 + format*0.1
        # Minimum total = 40 + 30 + 20 + 0 = 90
        assert result.quality_score >= 90

    def test_deterministic_format_validation(self, valid_tor_document: dict):
        """Format validation produces identical results across multiple runs."""
        engine = RuleEngine()
        for rule in get_format_rules():
            engine.register_rule("format", rule)

        result1 = engine.validate(valid_tor_document)
        result2 = engine.validate(valid_tor_document)

        format1 = next(cs for cs in result1.categories if cs.category == "format")
        format2 = next(cs for cs in result2.categories if cs.category == "format")

        assert format1.score == format2.score
        assert len(format1.findings) == len(format2.findings)
