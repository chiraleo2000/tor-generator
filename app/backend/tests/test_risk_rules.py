"""Risk and announced-price rules for two-bucket TOR review."""

from __future__ import annotations

from app.rule_engine.engine import (
    KIND_LEGAL,
    KIND_RISK,
    Finding,
    Severity,
    attach_legal_basis,
    finding_as_dict,
    resolve_finding_kind,
)
from app.rule_engine.rules.risk import (
    AnnouncedPriceRule,
    CostAbnormalityRule,
    ProcurementMethodRule,
    VagueLanguageRule,
)


def test_vague_language_is_risk():
    findings = VagueLanguageRule().validate(
        {"s4": "ผู้รับจ้างต้องส่งมอบงานตามความเหมาะสมและมีคุณภาพดีโดยไม่มีตัวชี้วัด"}
    )
    assert findings
    assert findings[0].finding_kind == KIND_RISK
    assert findings[0].risk_type == "vague"
    assert findings[0].rule_violated == "RISK_VAGUE_LANGUAGE"


def test_missing_announced_price_is_legal():
    findings = AnnouncedPriceRule().validate(
        {"s6": "วงเงินงบประมาณ 5,000,000 บาท จากเงินงบประมาณรายจ่ายประจำปี"}
    )
    assert findings[0].rule_violated == "LEGAL_ANNOUNCED_PRICE_MISSING"
    assert findings[0].finding_kind == KIND_LEGAL


def test_thai_digits_are_not_treated_as_ascii_amounts():
    findings = AnnouncedPriceRule().validate(
        {"s6": "วงเงินงบประมาณ ๑๐๐๐๐๐๐ บาท ราคากลาง คำนวณจากราคาที่เคยจ้าง"}
    )
    assert not any(item.rule_violated == "RISK_PRICE_GAP" for item in findings)
    findings = AnnouncedPriceRule().validate(
        {
            "s6": (
                "วงเงินงบประมาณ 10,000,000 บาท ราคากลาง 5,000,000 บาท "
                "คำนวณจากราคาที่เคยจ้าง"
            )
        }
    )
    assert any(item.rule_violated == "RISK_PRICE_GAP" for item in findings)
    assert all(item.finding_kind == KIND_RISK for item in findings if item.rule_violated == "RISK_PRICE_GAP")


def test_payment_sum_not_100_is_cost_risk():
    findings = CostAbnormalityRule().validate(
        {"s8": "งวดที่ 1 ร้อยละ 40 งวดที่ 2 ร้อยละ 40"}
    )
    assert findings[0].rule_violated == "RISK_PAYMENT_SUM"
    assert findings[0].risk_type == "cost"


def test_procurement_method_required_for_high_budget():
    findings = ProcurementMethodRule().validate(
        {"budget": 2_000_000, "s6": "วงเงิน 2,000,000 บาท จากงบประมาณรายจ่าย"}
    )
    assert findings[0].rule_violated == "LEGAL_PROCUREMENT_METHOD_MISSING"
    assert findings[0].finding_kind == KIND_LEGAL


def test_procurement_method_passes_when_named():
    findings = ProcurementMethodRule().validate(
        {
            "budget": 2_000_000,
            "s6": "จัดซื้อด้วยวิธีประกาศเชิญชวนทั่วไป (e-bidding) วงเงิน 2,000,000 บาท",
        }
    )
    assert findings == []


def test_resolve_finding_kind_from_rule_prefix():
    finding = Finding(
        severity=Severity.WARNING,
        rule_violated="CONSISTENCY_BUDGET_SCOPE",
        affected_section="s6",
        message="ไม่สอดคล้อง",
    )
    assert resolve_finding_kind(finding) == KIND_RISK


def test_attach_legal_basis_fills_legal_only():
    legal = Finding(
        severity=Severity.WARNING,
        rule_violated="LEGAL_ANNOUNCED_PRICE_MISSING",
        affected_section="s6",
        message="ขาดราคากลาง",
        finding_kind=KIND_LEGAL,
    )
    risk = Finding(
        severity=Severity.WARNING,
        rule_violated="RISK_VAGUE_LANGUAGE",
        affected_section="s4",
        message="คลุมเครือ",
        finding_kind=KIND_RISK,
    )
    attach_legal_basis(
        [legal, risk],
        "[คู่มือ]\nพ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560 มาตรา 8",
    )
    assert "มาตรา" in (legal.legal_basis or "")
    assert risk.legal_basis is None
    dumped = finding_as_dict(legal, aliases=True)
    assert dumped["finding_kind"] == KIND_LEGAL
    assert dumped["rule"] == legal.rule_violated


def test_parse_ascii_amounts_and_ignore_thai_digits():
    from app.rule_engine.rules.risk import _joined_text, _parse_amounts, _parse_baht_percents, _section_text

    assert 5_000_000 in _parse_amounts("วงเงิน 5,000,000 บาท")
    assert 12345 in _parse_amounts("วงเงิน 12345 บาท")
    assert _parse_amounts("งบ 1234 บาท") == []
    assert _parse_amounts("งบ ๑๒๓๔๕ บาท") == []
    assert _parse_baht_percents("ร้อยละ   40 และร้อยละ") == [40]
    from app.rule_engine.rules.risk import _consume_grouped_amount

    assert _consume_grouped_amount(",123", 0)[0] is None
    assert _consume_grouped_amount("1,12", 0)[0] is None
    assert _consume_grouped_amount("1,2345", 0)[0] is None
    nested = {"sections": {"s6": "งบ 1,000,000 บาท"}}
    assert "1,000,000" in _section_text(nested, "s6")
    assert "งบ" in _joined_text(nested)


def test_cost_effort_mismatch_is_risk():
    findings = CostAbnormalityRule().validate(
        {
            "s4": "ประมาณการ 120 man-day สำหรับพัฒนาระบบ",
            "s6": "วงเงินงบประมาณ 100,000 บาท",
        }
    )
    assert any(item.rule_violated == "RISK_COST_EFFORT_MISMATCH" for item in findings)


def test_procurement_method_from_s6_amount_without_budget_field():
    findings = ProcurementMethodRule().validate({"s6": "วงเงิน 2,000,000 บาท จากงบประมาณรายจ่าย"})
    assert findings[0].rule_violated == "LEGAL_PROCUREMENT_METHOD_MISSING"
