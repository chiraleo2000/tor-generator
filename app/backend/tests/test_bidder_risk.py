"""Bidder risk money, page references, and the fixed bid recommendation."""

from __future__ import annotations

from app.services.bidder_risk import (
    PAGE_NOT_FOUND,
    assess_bidder_risk,
    read_printed_page,
    strip_page_markers,
)
from app.services.tor_analysis import PART_WEIGHTS, analyze_tor

_PHASED_WHOLE_CONTRACT = """
วงเงินงบประมาณ 27,340,000 บาท
ส่งมอบงานเป็นงวด งวดที่ 1 ร้อยละ 30 เมื่อส่งรายงาน งวดที่ 2 ร้อยละ 70 เมื่อส่งระบบ
ค่าปรับอัตราร้อยละ 0.10 ต่อวัน ของมูลค่าสัญญาทั้งหมด
"""


def test_penalty_uses_whole_contract_even_when_delivery_is_phased():
    report = assess_bidder_risk(_PHASED_WHOLE_CONTRACT)
    penalty = report.penalty
    assert penalty.budget == 27_340_000
    assert penalty.baht_per_day == 27_340
    assert penalty.amount_30_days == 820_200
    assert penalty.amount_60_days == 1_640_400
    assert penalty.base == "whole_contract"
    assert "สัญญาทั้งหมด" in penalty.base_label


def test_missing_budget_and_page_are_not_invented():
    report = assess_bidder_risk("ค่าปรับร้อยละ 0.10 ต่อวัน ของมูลค่าสัญญาทั้งหมด หากส่งมอบล่าช้า")
    assert report.penalty.budget is None
    assert report.penalty.baht_per_day is None
    assert report.penalty.amount_30_days is None
    assert report.penalty.amount_60_days is None
    assert "27,340" not in report.markdown
    assert "27340" not in report.markdown
    penalty_rows = next(
        category.rows for category in report.categories if category.key == "penalty"
    )
    assert penalty_rows
    assert penalty_rows[0].page_ref == PAGE_NOT_FOUND
    assert "ไม่พบเลขหน้า" in penalty_rows[0].requirement


def test_critical_signal_recommends_not_to_bid():
    report = assess_bidder_risk(
        "ผู้รับจ้างต้องย้ายข้อมูลทั้งหมดของระบบเดิมตามที่ผู้ว่าจ้างกำหนด และยังไม่มีปริมาณข้อมูล"
    )
    assert report.recommendation_kind == "do_not_bid"
    assert "ไม่ควรยื่น" in report.recommendation
    signals = [
        (row.signal, row.level)
        for category in report.categories
        for row in category.rows
    ]
    assert ("data_migration", "สูงมาก") in signals


def test_only_high_signal_can_be_considered_after_gates():
    report = assess_bidder_risk(
        "ผู้ว่าจ้างจัดเครื่องแม่ข่าย VM สำหรับประมวลผลให้ผู้รับจ้างใช้ตลอดสัญญา"
    )
    assert report.recommendation_kind == "consider"
    assert "พิจารณาได้เมื่อปิดด่าน" in report.recommendation
    assert "ไม่ควรยื่น" not in report.recommendation


def test_no_decision_signal_is_not_a_certificate_to_bid():
    report = assess_bidder_risk(
        "ขอบเขตงานพัฒนาระบบรายงานภายใน 180 วัน โดยส่งมอบคู่มือการใช้งานของระบบ"
    )
    assert report.recommendation_kind == "no_high_risk"
    assert "ไม่พบความเสี่ยงสูงจากข้อความที่มี" in report.recommendation
    assert "ไม่ใช่คำรับรองว่าควรยื่น" in report.recommendation


def test_printed_page_is_used_when_close_to_the_file_index():
    pages = [
        {
            "index": 16,
            "printed": None,
            "text": "ค่าปรับร้อยละ 0.10 ต่อวัน ของมูลค่าสัญญาทั้งหมด\n\n- 16 -",
        }
    ]
    report = assess_bidder_risk(
        "ค่าปรับร้อยละ 0.10 ต่อวัน ของมูลค่าสัญญาทั้งหมด",
        pages=pages,
        budget=27_340_000,
    )
    row = next(category.rows[0] for category in report.categories if category.key == "penalty")
    assert row.page_ref == "หน้า 16"
    assert read_printed_page("เนื้อหา\n\n16", 16) == 16
    assert read_printed_page("เนื้อหา\n\n16", 2) is None


def test_unreadable_footer_says_file_page_and_pages_win_over_markers():
    unreadable = assess_bidder_risk(
        "ค่าปรับร้อยละ 0.10 ต่อวัน",
        pages=[{"index": 4, "printed": None, "text": "ค่าปรับร้อยละ 0.10 ต่อวัน\n\nดูรายละเอียดแนบท้าย"}],
        budget=1_000_000,
    )
    row = next(category.rows[0] for category in unreadable.categories if category.key == "penalty")
    assert row.page_ref == "หน้าตามไฟล์ที่ 4"
    assert "หน้า 16" not in row.requirement

    far = assess_bidder_risk(
        "ค่าปรับร้อยละ 0.10 ต่อวัน",
        pages=[{"index": 2, "printed": None, "text": "ค่าปรับร้อยละ 0.10 ต่อวัน\n\n16"}],
        budget=1_000_000,
    )
    far_row = next(category.rows[0] for category in far.categories if category.key == "penalty")
    assert far_row.page_ref == "หน้าตามไฟล์ที่ 2"

    preferred = assess_bidder_risk(
        "[[page file=1 printed=99]]\nค่าปรับร้อยละ 0.10 ต่อวัน",
        pages=[{"index": 5, "printed": 5, "text": "ค่าปรับร้อยละ 0.10 ต่อวัน"}],
        budget=1_000_000,
    )
    preferred_row = next(
        category.rows[0] for category in preferred.categories if category.key == "penalty"
    )
    assert preferred_row.page_ref == "หน้า 5"
    assert "99" not in preferred_row.requirement


def test_page_markers_do_not_change_three_part_scores():
    plain = {
        "s1": (
            "ความเป็นมา ตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ "
            "พ.ศ. 2560 และระเบียบกระทรวงการคลัง พ.ศ. 2560"
        ),
        "s4": "จัดซื้อครุภัณฑ์คอมพิวเตอร์สำหรับหน่วยงาน พร้อมส่งมอบรายงาน",
        "s10": "ค่าปรับร้อยละ 0.10 ต่อวัน",
        "budget": 5_000_000,
        "project_type": "buy_goods",
        "penalty_rate_percent": 0.10,
    }
    marked = {
        **plain,
        "s4": "[[page file=4 printed=4]]\n" + plain["s4"],
        "s10": "<!-- page 10 -->\n" + plain["s10"],
        "_source_text": "[[page file=1 printed=1]]\n" + "\n".join(
            value for value in plain.values() if isinstance(value, str)
        ),
    }
    before = analyze_tor(plain)
    after = analyze_tor(marked)
    assert (before.legal.score, before.lock_in.score, before.project.score, before.total) == (
        after.legal.score,
        after.lock_in.score,
        after.project.score,
        after.total,
    )
    assert PART_WEIGHTS == {"legal": 0.40, "lock_in": 0.30, "project": 0.30}
    assert "[[page" not in strip_page_markers(marked["s4"])
    assert after.bidder_risk["recommendation"]


def test_budget_rule_findings_join_the_project_part(monkeypatch):
    def fake(document_text: str) -> list[dict]:
        assert document_text.strip()
        return [
            {
                "rule_id": "training_meals",
                "severity": "suggestion",
                "message": "ควรแยกค่าอบรมตามจำนวนมื้อ",
                "suggestion": "เพิ่มหมวดค่าอบรม",
                "evidence": "ไม่พบค่าอบรมในวงเงิน",
            }
        ]

    monkeypatch.setattr(
        "app.services.tor_analysis.load_budget_rule_findings",
        fake,
    )
    result = analyze_tor({"s4": "พัฒนาระบบสารสนเทศ", "s6": "วงเงินงบประมาณ 100000 บาท"})
    assert any("ควรแยกค่าอบรม" in item.reason for item in result.project.findings)
    assert any(item.source_quote == "ไม่พบค่าอบรมในวงเงิน" for item in result.project.findings)
    assert PART_WEIGHTS["project"] == 0.30


def test_categories_stay_in_fixed_order():
    report = assess_bidder_risk("ขอบเขตงานพัฒนาระบบรายงานภายใน 180 วัน โดยส่งมอบคู่มือ")
    assert [category.key for category in report.categories] == [
        "clarity",
        "external",
        "schedule",
        "infrastructure",
        "penalty",
        "security",
    ]
