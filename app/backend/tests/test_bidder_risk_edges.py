"""Branches in bidder-risk helpers that the main report tests do not hit."""

from types import SimpleNamespace

from app.services.bidder_risk import (
    PAGE_NOT_FOUND,
    _add_row,
    _append_cashflow_row,
    _as_budget,
    _daily_rate,
    _grouped_or_plain_amount,
    _hourly_baht_amount,
    _hourly_note,
    _migration_level,
    _PageLocator,
    _penalty_base,
    _ref_from_form_feed,
    _ref_from_marker,
    _ref_from_pages,
    _security_rows,
    _short_quote,
    assess_bidder_risk,
    file_page_label,
    normalize_pages,
    printed_is_close,
)


def test_amount_tokens_and_hourly_notes():
    assert _grouped_or_plain_amount("12") is True
    assert _grouped_or_plain_amount("๑๒") is False
    assert _grouped_or_plain_amount("1,234") is True
    assert _grouped_or_plain_amount(",234") is False
    assert _hourly_baht_amount("ค่าปรับ 500 บาทต่อชั่วโมง") == "500"
    assert _hourly_baht_amount("ไม่มีตัวเลข") is None
    assert "500" in _hourly_note("ค่าปรับ 500 บาทต่อชั่วโมง", 1000)
    assert _hourly_note("ค่าปรับต่อชั่วโมงโดยไม่มีตัวเลข", None)
    assert "ไม่มีวงเงิน" in _hourly_note("ค่าปรับร้อยละ 0.1 ต่อชั่วโมง", None)
    assert "บาทต่อชั่วโมง" in _hourly_note("ค่าปรับร้อยละ 0.1 ต่อชั่วโมง", 1_000_000)
    assert _as_budget(True) is None
    assert _as_budget(0) is None
    assert _as_budget("1,200") == 1200
    assert _as_budget("nope") is None


def test_page_refs_reject_distant_and_missing_numbers():
    assert printed_is_close(0, 1) is False
    assert printed_is_close(9, 1) is False
    assert file_page_label(0) == "หน้าตามไฟล์ที่ 1"
    pages = normalize_pages(
        [
            SimpleNamespace(index="nope", text="- 2 -\nเนื้อหา", printed=True),
            {"index": 3, "text": "ไม่มีเลขท้าย", "printed": "99"},
        ]
    )
    assert pages[0]["index"] == 1
    assert _ref_from_pages("", pages) is None
    assert _ref_from_pages("ไม่มีเลขท้าย", pages) == file_page_label(3)
    assert _ref_from_marker({"printed": 40, "file": 1}) == file_page_label(1)
    assert _ref_from_marker({"printed": None, "file": None}) == PAGE_NOT_FOUND
    marked = "[[page file=2]]\nย้ายข้อมูล\n\f\n- 1 -\nค่าปรับ"
    assert _ref_from_form_feed("\f- 1 -\nค่าปรับล่าช้า", "ค่าปรับ") == "หน้า 1"
    assert _ref_from_form_feed("ไม่มีตัวแบ่ง", "ค่าปรับ") == PAGE_NOT_FOUND
    assert _short_quote("ไม่มีคำนี้", "ค่าปรับ") == ""
    locator = _PageLocator(marked, None)
    rows: list = []
    _add_row(
        rows,
        locator,
        needle="ไม่มีในข้อความ",
        issue="x",
        impact="y",
        level="สูง",
        mitigation="z",
    )
    assert rows == []


def test_penalty_phase_rate_and_security_rows():
    text = "ค่าปรับร้อยละ 30 ของค่างวดที่ส่งมอบ"
    assert _penalty_base(text)[0] == "phase"
    assert _daily_rate("ร้อยละ 30 ของงวด") is None
    rate = _daily_rate("ค่าปรับร้อยละ 0.10")
    assert rate is not None
    assert _migration_level("ย้ายข้อมูลตามที่ผู้ว่าจ้างกำหนด") 
    report = assess_bidder_risk(
        "\n".join(
            [
                "ย้ายข้อมูลตามที่ผู้ว่าจ้างกำหนด จำนวน 10 รายการ",
                "ค่าปรับร้อยละ 0.10 ต่อวัน ของมูลค่าสัญญาทั้งหมด",
                "งวดที่ 1 ร้อยละ 10 งวดที่ 2 ร้อยละ 20",
                "กระแสเงินสดยังไม่มีเงินเข้า",
                "ต้องใช้ PQC จริง",
                "ทดสอบช่องโหว่หนึ่งรอบ",
                "งวดใดไม่ครบให้ปรับเป็นรายงวด",
            ]
        ),
        budget=1_000_000,
    )
    keys = {row.issue for category in report.categories for row in category.rows}
    assert any("PQC" in issue or "ช่องโหว่" in issue or "กระแสเงินสด" in issue for issue in keys)
    locator = _PageLocator("งวดที่ 1 ร้อยละ 10 งวดที่ 2 ร้อยละ 20 กระแสเงินสด", None)
    rows = []
    _append_cashflow_row(rows, locator, locator.text)
    assert rows
    assert _security_rows(_PageLocator("ธรรมาภิบาล AI และซอร์สโค้ดเป็นของผู้ว่าจ้าง", None))
