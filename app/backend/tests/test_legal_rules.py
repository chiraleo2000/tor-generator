"""Unit tests for legal compliance rules.

Tests cover:
- VendorPaidUpCapitalRule: capital = floor(budget/4)
- PenaltyRateRule: rates within 0.01%–0.20%, min 100 baht/day
- BrandLockFairnessRule: brand names without "or equivalent"
- RequiredLegalReferencesRule: legal references and required clauses
- Helper functions: compute_vendor_capital, validate_penalty_rate
"""

from __future__ import annotations

import math

import pytest

from app.rule_engine.engine import Finding, RuleEngine, Severity
from app.rule_engine.rules.legal import (
    PENALTY_MIN_BAHT_PER_DAY,
    PENALTY_RATE_MAX_PERCENT,
    PENALTY_RATE_MIN_PERCENT,
    BrandLockFairnessRule,
    PenaltyRateRule,
    RequiredLegalReferencesRule,
    VendorPaidUpCapitalRule,
    compute_vendor_capital,
    validate_penalty_rate,
)


# --- Fixtures ---


@pytest.fixture
def capital_rule() -> VendorPaidUpCapitalRule:
    return VendorPaidUpCapitalRule()


@pytest.fixture
def penalty_rule() -> PenaltyRateRule:
    return PenaltyRateRule()


@pytest.fixture
def brand_rule() -> BrandLockFairnessRule:
    return BrandLockFairnessRule()


@pytest.fixture
def legal_ref_rule() -> RequiredLegalReferencesRule:
    return RequiredLegalReferencesRule()


@pytest.fixture
def full_tor_document() -> dict:
    """A fully compliant TOR document for testing."""
    return {
        "s1": "ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560 ความเป็นมา...",
        "s2": "วัตถุประสงค์ของโครงการ...",
        "s3": "คุณสมบัติผู้เสนอราคา ต้องมีทุนจดทะเบียนไม่น้อยกว่า 1,250,000 บาท",
        "s4": "ขอบเขตของงาน...",
        "s5": "ระยะเวลาดำเนินงาน...",
        "s6": "งบประมาณ 5,000,000 บาท",
        "s7": "เงื่อนไขการชำระเงิน...",
        "s8": "หลักเกณฑ์การพิจารณา...",
        "s9": "การรับประกัน...",
        "s10": "ค่าปรับ อัตราร้อยละ 0.10 ต่อวัน ขั้นต่ำ 100 บาท/วัน",
        "s11": "เอกสารประกอบ...",
        "s12": "เงื่อนไขอื่นๆ...",
        "s13": "ภาคผนวก...",
        "budget": 5_000_000,
        "vendor_capital": 1_250_000,
        "penalty_rate_percent": 0.10,
        "penalty_min_baht_per_day": 100,
        "project_type": "it",
        "timeline_days": 180,
    }


# --- Tests: compute_vendor_capital helper ---


class TestComputeVendorCapital:
    """Test the compute_vendor_capital helper function."""

    def test_basic_division(self):
        """5,000,000 / 4 = 1,250,000."""
        assert compute_vendor_capital(5_000_000) == 1_250_000

    def test_floor_rounding(self):
        """5,000,001 / 4 = 1,250,000 (floor, not round)."""
        assert compute_vendor_capital(5_000_001) == 1_250_000

    def test_floor_rounding_remainder_3(self):
        """5,000,003 / 4 = 1,250,000 (remainder discarded)."""
        assert compute_vendor_capital(5_000_003) == 1_250_000

    def test_small_budget(self):
        """100 / 4 = 25."""
        assert compute_vendor_capital(100) == 25

    def test_one_baht(self):
        """1 / 4 = 0."""
        assert compute_vendor_capital(1) == 0

    def test_large_budget(self):
        """1,000,000,000 / 4 = 250,000,000."""
        assert compute_vendor_capital(1_000_000_000) == 250_000_000

    def test_float_budget(self):
        """Float budget is also supported."""
        assert compute_vendor_capital(5_000_000.75) == 1_250_000

    def test_negative_budget_raises(self):
        """Negative budget raises ValueError."""
        with pytest.raises(ValueError):
            compute_vendor_capital(-1_000_000)

    def test_zero_budget_raises(self):
        """Zero budget raises ValueError."""
        with pytest.raises(ValueError):
            compute_vendor_capital(0)

    def test_result_is_integer(self):
        """Result is always an integer."""
        result = compute_vendor_capital(7)
        assert isinstance(result, int)
        assert result == 1  # floor(7/4) = 1


# --- Tests: validate_penalty_rate helper ---


class TestValidatePenaltyRate:
    """Test the validate_penalty_rate helper function."""

    def test_min_rate_valid(self):
        """Minimum rate (0.01%) is valid."""
        assert validate_penalty_rate(0.01) is True

    def test_max_rate_valid(self):
        """Maximum rate (0.20%) is valid."""
        assert validate_penalty_rate(0.20) is True

    def test_mid_rate_valid(self):
        """Middle rate (0.10%) is valid."""
        assert validate_penalty_rate(0.10) is True

    def test_below_min_invalid(self):
        """Rate below 0.01% is invalid."""
        assert validate_penalty_rate(0.005) is False

    def test_above_max_invalid(self):
        """Rate above 0.20% is invalid."""
        assert validate_penalty_rate(0.25) is False

    def test_zero_rate_invalid(self):
        """Zero rate is invalid."""
        assert validate_penalty_rate(0.0) is False


# --- Tests: VendorPaidUpCapitalRule ---


class TestVendorPaidUpCapitalRule:
    """Test the VendorPaidUpCapitalRule validation."""

    def test_correct_capital_no_findings(
        self, capital_rule: VendorPaidUpCapitalRule, full_tor_document: dict
    ):
        """Correct vendor capital produces no findings."""
        findings = capital_rule.validate(full_tor_document)
        assert len(findings) == 0

    def test_mismatched_capital_produces_error(
        self, capital_rule: VendorPaidUpCapitalRule
    ):
        """Vendor capital not matching floor(budget/4) produces ERROR."""
        doc = {
            "budget": 5_000_000,
            "vendor_capital": 2_000_000,  # Should be 1,250,000
            "s3": "คุณสมบัติ ทุนจดทะเบียน 2,000,000 บาท",
        }
        findings = capital_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].rule_violated == "LEGAL_CAPITAL_MISMATCH"
        assert findings[0].affected_section == "s3"

    def test_missing_budget_produces_error(self, capital_rule: VendorPaidUpCapitalRule):
        """Missing budget produces ERROR."""
        doc = {"s3": "คุณสมบัติ...", "vendor_capital": 1_000_000}
        findings = capital_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].rule_violated == "LEGAL_CAPITAL_NO_BUDGET"

    def test_no_capital_in_section_produces_warning(
        self, capital_rule: VendorPaidUpCapitalRule
    ):
        """Missing capital specification (no vendor_capital key, no mention in s3)."""
        doc = {
            "budget": 5_000_000,
            "s3": "ผู้เสนอราคาต้องเป็นนิติบุคคล",  # No mention of ทุนจดทะเบียน
        }
        findings = capital_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert findings[0].rule_violated == "LEGAL_CAPITAL_NOT_SPECIFIED"

    def test_capital_mentioned_in_text_no_warning(
        self, capital_rule: VendorPaidUpCapitalRule
    ):
        """If s3 mentions ทุนจดทะเบียน but vendor_capital not explicit, no warning."""
        doc = {
            "budget": 5_000_000,
            "s3": "ผู้เสนอราคาต้องมีทุนจดทะเบียนไม่น้อยกว่า 1,250,000 บาท",
        }
        findings = capital_rule.validate(doc)
        assert len(findings) == 0

    def test_negative_budget_produces_error(
        self, capital_rule: VendorPaidUpCapitalRule
    ):
        """Negative budget produces invalid budget error."""
        doc = {"budget": -1_000_000, "s3": "คุณสมบัติ..."}
        findings = capital_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].rule_violated == "LEGAL_CAPITAL_INVALID_BUDGET"

    def test_invalid_capital_type_produces_error(
        self, capital_rule: VendorPaidUpCapitalRule
    ):
        """Non-numeric vendor_capital produces error."""
        doc = {
            "budget": 5_000_000,
            "vendor_capital": "one million",
            "s3": "คุณสมบัติ...",
        }
        findings = capital_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].rule_violated == "LEGAL_CAPITAL_INVALID_VALUE"


# --- Tests: PenaltyRateRule ---


class TestPenaltyRateRule:
    """Test the PenaltyRateRule validation."""

    def test_valid_rate_no_findings(
        self, penalty_rule: PenaltyRateRule, full_tor_document: dict
    ):
        """Valid penalty rate produces no findings."""
        findings = penalty_rule.validate(full_tor_document)
        assert len(findings) == 0

    def test_rate_too_low_produces_error(self, penalty_rule: PenaltyRateRule):
        """Rate below 0.01% produces ERROR."""
        doc = {
            "penalty_rate_percent": 0.005,
            "s10": "ค่าปรับ...",
        }
        findings = penalty_rule.validate(doc)
        assert any(f.rule_violated == "LEGAL_PENALTY_RATE_TOO_LOW" for f in findings)
        error = next(f for f in findings if f.rule_violated == "LEGAL_PENALTY_RATE_TOO_LOW")
        assert error.severity == Severity.ERROR

    def test_rate_too_high_produces_error(self, penalty_rule: PenaltyRateRule):
        """Rate above 0.20% produces ERROR."""
        doc = {
            "penalty_rate_percent": 0.25,
            "s10": "ค่าปรับ...",
        }
        findings = penalty_rule.validate(doc)
        assert any(f.rule_violated == "LEGAL_PENALTY_RATE_TOO_HIGH" for f in findings)
        error = next(f for f in findings if f.rule_violated == "LEGAL_PENALTY_RATE_TOO_HIGH")
        assert error.severity == Severity.ERROR

    def test_rate_at_min_boundary_valid(self, penalty_rule: PenaltyRateRule):
        """Rate exactly at 0.01% is valid (no error finding)."""
        doc = {
            "penalty_rate_percent": 0.01,
            "s10": "ค่าปรับ...",
        }
        findings = penalty_rule.validate(doc)
        rate_findings = [
            f
            for f in findings
            if f.rule_violated in ("LEGAL_PENALTY_RATE_TOO_LOW", "LEGAL_PENALTY_RATE_TOO_HIGH")
        ]
        assert len(rate_findings) == 0

    def test_rate_at_max_boundary_valid(self, penalty_rule: PenaltyRateRule):
        """Rate exactly at 0.20% is valid (no error finding)."""
        doc = {
            "penalty_rate_percent": 0.20,
            "s10": "ค่าปรับ...",
        }
        findings = penalty_rule.validate(doc)
        rate_findings = [
            f
            for f in findings
            if f.rule_violated in ("LEGAL_PENALTY_RATE_TOO_LOW", "LEGAL_PENALTY_RATE_TOO_HIGH")
        ]
        assert len(rate_findings) == 0

    def test_missing_penalty_section_and_rate_produces_error(
        self, penalty_rule: PenaltyRateRule
    ):
        """No penalty info at all produces ERROR."""
        doc = {"s1": "ความเป็นมา..."}
        findings = penalty_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].rule_violated == "LEGAL_PENALTY_MISSING"
        assert findings[0].severity == Severity.ERROR

    def test_penalty_min_baht_too_low_produces_warning(
        self, penalty_rule: PenaltyRateRule
    ):
        """Min baht below 100 produces WARNING."""
        doc = {
            "penalty_rate_percent": 0.10,
            "penalty_min_baht_per_day": 50,
            "s10": "ค่าปรับ...",
        }
        findings = penalty_rule.validate(doc)
        assert any(f.rule_violated == "LEGAL_PENALTY_MIN_TOO_LOW" for f in findings)
        warning = next(f for f in findings if f.rule_violated == "LEGAL_PENALTY_MIN_TOO_LOW")
        assert warning.severity == Severity.WARNING

    def test_penalty_min_baht_exactly_100_valid(self, penalty_rule: PenaltyRateRule):
        """Min baht exactly 100 is valid."""
        doc = {
            "penalty_rate_percent": 0.10,
            "penalty_min_baht_per_day": 100,
            "s10": "ค่าปรับ...",
        }
        findings = penalty_rule.validate(doc)
        min_findings = [f for f in findings if f.rule_violated == "LEGAL_PENALTY_MIN_TOO_LOW"]
        assert len(min_findings) == 0

    def test_invalid_rate_type_produces_error(self, penalty_rule: PenaltyRateRule):
        """Non-numeric rate produces ERROR."""
        doc = {
            "penalty_rate_percent": "high",
            "s10": "ค่าปรับ...",
        }
        findings = penalty_rule.validate(doc)
        assert any(f.rule_violated == "LEGAL_PENALTY_INVALID_TYPE" for f in findings)


# --- Tests: BrandLockFairnessRule ---


class TestBrandLockFairnessRule:
    """Test the BrandLockFairnessRule validation."""

    def test_no_brands_no_findings(self, brand_rule: BrandLockFairnessRule):
        """Document without brand names produces no findings."""
        doc = {
            "s3": "ผู้เสนอราคาต้องเป็นนิติบุคคล",
            "s4": "จัดหาระบบคอมพิวเตอร์สำหรับหน่วยงาน",
        }
        findings = brand_rule.validate(doc)
        assert len(findings) == 0

    def test_brand_without_equivalent_produces_warning(
        self, brand_rule: BrandLockFairnessRule
    ):
        """Brand name without 'or equivalent' produces WARNING."""
        doc = {
            "s4": "จัดหาเครื่องคอมพิวเตอร์ Dell รุ่น OptiPlex",
        }
        findings = brand_rule.validate(doc)
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert findings[0].rule_violated == "LEGAL_BRAND_LOCK"
        assert "Dell" in findings[0].message

    def test_brand_with_or_equivalent_no_finding(
        self, brand_rule: BrandLockFairnessRule
    ):
        """Brand name with 'หรือเทียบเท่า' produces no finding."""
        doc = {
            "s4": "จัดหาเครื่องคอมพิวเตอร์ Dell หรือเทียบเท่า",
        }
        findings = brand_rule.validate(doc)
        assert len(findings) == 0

    def test_brand_with_english_equivalent_no_finding(
        self, brand_rule: BrandLockFairnessRule
    ):
        """Brand name with 'or equivalent' produces no finding."""
        doc = {
            "s4": "Server: Dell PowerEdge or equivalent",
        }
        findings = brand_rule.validate(doc)
        assert len(findings) == 0

    def test_multiple_brands_multiple_findings(
        self, brand_rule: BrandLockFairnessRule
    ):
        """Multiple brands without equivalent each produce a finding."""
        doc = {
            "s4": "ใช้ Microsoft Windows และ Cisco Router",
        }
        findings = brand_rule.validate(doc)
        assert len(findings) == 2
        brands_found = {f.message.split("'")[1] for f in findings}
        assert "Microsoft" in brands_found
        assert "Cisco" in brands_found

    def test_brand_in_section_not_checked_produces_no_finding(
        self, brand_rule: BrandLockFairnessRule
    ):
        """Brand names in sections not in the check list (e.g. s1) produce no finding."""
        doc = {
            "s1": "โครงการนี้ใช้ระบบ Microsoft Office",  # s1 is not checked
        }
        findings = brand_rule.validate(doc)
        assert len(findings) == 0

    def test_thai_brand_name_detected(self, brand_rule: BrandLockFairnessRule):
        """Thai transliteration of brands also detected."""
        doc = {
            "s4": "ใช้ระบบปฏิบัติการไมโครซอฟท์ วินโดวส์",
        }
        findings = brand_rule.validate(doc)
        assert len(findings) >= 1
        assert any("ไมโครซอฟท์" in f.message for f in findings)

    def test_same_brand_mentioned_twice_one_finding(
        self, brand_rule: BrandLockFairnessRule
    ):
        """Same brand mentioned multiple times in one section produces one finding."""
        doc = {
            "s4": "ใช้ Dell Server และ Dell Desktop",
        }
        findings = brand_rule.validate(doc)
        dell_findings = [f for f in findings if "Dell" in f.message]
        assert len(dell_findings) == 1

    def test_empty_section_no_error(self, brand_rule: BrandLockFairnessRule):
        """Empty sections don't cause errors."""
        doc = {"s4": "", "s3": None}
        findings = brand_rule.validate(doc)
        assert len(findings) == 0


# --- Tests: RequiredLegalReferencesRule ---


class TestRequiredLegalReferencesRule:
    """Test the RequiredLegalReferencesRule validation."""

    def test_full_reference_present_no_finding(
        self, legal_ref_rule: RequiredLegalReferencesRule
    ):
        """Document with full legal reference produces no reference finding."""
        doc = {
            "s1": "ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560",
            "s3": "คุณสมบัติผู้เสนอราคา...",
            "s4": "ขอบเขตของงาน...",
            "s9": "การรับประกัน...",
            "s10": "ค่าปรับ...",
        }
        findings = legal_ref_rule.validate(doc)
        ref_findings = [f for f in findings if f.rule_violated == "LEGAL_REF_MISSING_ACT"]
        assert len(ref_findings) == 0

    def test_short_reference_accepted(
        self, legal_ref_rule: RequiredLegalReferencesRule
    ):
        """Short form reference is also accepted."""
        doc = {
            "s1": "ตาม พ.ร.บ. จัดซื้อจัดจ้าง 2560",
            "s3": "คุณสมบัติ...",
            "s4": "ขอบเขต...",
            "s9": "รับประกัน...",
            "s10": "ค่าปรับ...",
        }
        findings = legal_ref_rule.validate(doc)
        ref_findings = [f for f in findings if f.rule_violated == "LEGAL_REF_MISSING_ACT"]
        assert len(ref_findings) == 0

    def test_partial_reference_accepted(
        self, legal_ref_rule: RequiredLegalReferencesRule
    ):
        """Partial reference with key terms is accepted."""
        doc = {
            "s1": "อ้างอิง พ.ร.บ. การจัดซื้อจัดจ้าง ปี 2560",
            "s3": "คุณสมบัติ...",
            "s4": "ขอบเขต...",
            "s9": "รับประกัน...",
            "s10": "ค่าปรับ...",
        }
        findings = legal_ref_rule.validate(doc)
        ref_findings = [f for f in findings if f.rule_violated == "LEGAL_REF_MISSING_ACT"]
        assert len(ref_findings) == 0

    def test_no_legal_reference_produces_warning(
        self, legal_ref_rule: RequiredLegalReferencesRule
    ):
        """Document without any legal reference produces WARNING."""
        doc = {
            "s1": "ความเป็นมาของโครงการ ระบบสารสนเทศ",
            "s3": "คุณสมบัติ...",
            "s4": "ขอบเขต...",
            "s9": "รับประกัน...",
            "s10": "ค่าปรับ...",
        }
        findings = legal_ref_rule.validate(doc)
        ref_findings = [f for f in findings if f.rule_violated == "LEGAL_REF_MISSING_ACT"]
        assert len(ref_findings) == 1
        assert ref_findings[0].severity == Severity.WARNING

    def test_missing_required_clause_produces_error(
        self, legal_ref_rule: RequiredLegalReferencesRule
    ):
        """Missing required clause section produces ERROR."""
        doc = {
            "s1": "พ.ร.บ. จัดซื้อจัดจ้าง 2560",
            "s3": "คุณสมบัติ...",
            "s4": "ขอบเขต...",
            # s9 (warranty) missing
            "s10": "ค่าปรับ...",
        }
        findings = legal_ref_rule.validate(doc)
        clause_findings = [
            f for f in findings if "LEGAL_CLAUSE_MISSING" in f.rule_violated
        ]
        assert len(clause_findings) == 1
        assert clause_findings[0].severity == Severity.ERROR
        assert "การรับประกัน" in clause_findings[0].message

    def test_empty_required_section_produces_error(
        self, legal_ref_rule: RequiredLegalReferencesRule
    ):
        """Empty required clause section produces ERROR."""
        doc = {
            "s1": "พ.ร.บ. จัดซื้อจัดจ้าง 2560",
            "s3": "คุณสมบัติ...",
            "s4": "",  # Empty scope
            "s9": "รับประกัน...",
            "s10": "ค่าปรับ...",
        }
        findings = legal_ref_rule.validate(doc)
        clause_findings = [
            f for f in findings if "LEGAL_CLAUSE_MISSING" in f.rule_violated
        ]
        assert len(clause_findings) == 1
        assert "ขอบเขตของงาน" in clause_findings[0].message

    def test_all_clauses_present_no_clause_findings(
        self, legal_ref_rule: RequiredLegalReferencesRule, full_tor_document: dict
    ):
        """Document with all required clauses produces no clause findings."""
        findings = legal_ref_rule.validate(full_tor_document)
        clause_findings = [
            f for f in findings if "LEGAL_CLAUSE_MISSING" in f.rule_violated
        ]
        assert len(clause_findings) == 0


# --- Tests: Integration with Rule Engine ---


class TestLegalRulesIntegration:
    """Test that legal rules integrate correctly with the RuleEngine."""

    def test_legal_rules_register_under_legal_category(self):
        """All legal rules can be registered under the 'legal' category."""
        engine = RuleEngine()
        engine.register_rule("legal", VendorPaidUpCapitalRule())
        engine.register_rule("legal", PenaltyRateRule())
        engine.register_rule("legal", BrandLockFairnessRule())
        engine.register_rule("legal", RequiredLegalReferencesRule())

        result = engine.validate(
            {
                "s1": "พ.ร.บ. จัดซื้อจัดจ้าง 2560 ความเป็นมา...",
                "s3": "คุณสมบัติ ทุนจดทะเบียน...",
                "s4": "ขอบเขตของงาน...",
                "s9": "การรับประกัน...",
                "s10": "ค่าปรับ อัตรา 0.10% ต่อวัน",
                "budget": 5_000_000,
                "vendor_capital": 1_250_000,
                "penalty_rate_percent": 0.10,
                "penalty_min_baht_per_day": 100,
            }
        )
        # All valid → legal category should be high score
        legal_cat = next(cs for cs in result.categories if cs.category == "legal")
        assert legal_cat.score == 100.0

    def test_legal_violations_affect_weighted_score(self):
        """Legal errors reduce the overall quality score by 40% weight."""
        engine = RuleEngine()
        engine.register_rule("legal", VendorPaidUpCapitalRule())

        # Missing budget → ERROR (-20 from legal category)
        result = engine.validate({"s3": "คุณสมบัติ..."})

        legal_cat = next(cs for cs in result.categories if cs.category == "legal")
        assert legal_cat.score == 80.0  # 100 - 20 (one ERROR)

        # Total: 80*0.4 + 100*0.3 + 100*0.2 + 100*0.1 = 32 + 30 + 20 + 10 = 92
        assert result.quality_score == 92

    def test_fully_compliant_document_scores_100(self, full_tor_document: dict):
        """A fully compliant document scores 100 with all legal rules."""
        engine = RuleEngine()
        engine.register_rule("legal", VendorPaidUpCapitalRule())
        engine.register_rule("legal", PenaltyRateRule())
        engine.register_rule("legal", BrandLockFairnessRule())
        engine.register_rule("legal", RequiredLegalReferencesRule())

        result = engine.validate(full_tor_document)
        legal_cat = next(cs for cs in result.categories if cs.category == "legal")
        assert legal_cat.score == 100.0
        assert result.quality_score == 100
