"""Unit tests for the shared consultant and training budget calculator."""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from app.domain.consultant_budget import (
    budget_rule_findings,
    load_rate_catalog,
    suggest_budget,
)
from app.orchestrator.agents.budget_agent import BudgetDraftingAgent
from app.orchestrator.agents.review_agent import ReviewAgent
from app.rag.chunking import chunk_text
from app.rag.extraction import extract_pdf, markdown_tables_from_page, printed_page_number
from app.services.cost_training import normalize_cost_worksheet


def _rows() -> list[dict]:
    return load_rate_catalog()["rows"]


def _min_private(degree: str, years: int) -> int:
    prices = [
        row["private_independent"]
        for row in _rows()
        if row["degree"] == degree
        and isinstance(row.get("experience_years"), int)
        and row["experience_years"] >= years
    ]
    return min(prices)


def test_catalog_keeps_a_printed_master_row():
    row = next(
        item
        for item in _rows()
        if item["group"].endswith("วิศวกรรม")
        and item["degree"] == "master"
        and item["experience_years"] == 2
    )
    assert row["salary"] == 30090
    assert row["private_independent"] == 43028
    assert row["state_institution"] == 52958
    assert row["file_page"] == 19


def test_default_two_years_private_and_alternating_degrees():
    result = suggest_budget(team_size=2)
    people = result["consultants"]
    assert [person["degree"] for person in people] == ["master", "doctorate"]
    assert [person["years"] for person in people] == [2, 2]
    assert result["sector"] == "private"
    assert result["years"] == 2
    for person, degree in zip(people, ("master", "doctorate"), strict=True):
        assert person["column"] == "private_independent"
        assert person["monthly_rate"] == _min_private(degree, 2)
        assert person["monthly_rate"] < person["state_rate"]


def test_specified_years_use_the_cheapest_matching_private_row():
    result = suggest_budget(team_size=1, years=5)
    person = result["consultants"][0]
    assert person["degree"] == "master"
    assert person["years"] >= 5
    assert person["monthly_rate"] == _min_private("master", 5)
    assert person["sector"] == "private"


def test_state_sector_is_not_the_default_column():
    private = suggest_budget(team_size=1, years=2)
    state = suggest_budget(team_size=1, years=2, sector="state")
    assert private["consultants"][0]["column"] == "private_independent"
    assert state["consultants"][0]["column"] == "state_institution"
    assert state["consultants"][0]["monthly_rate"] > private["consultants"][0]["monthly_rate"]


def test_half_day_is_one_meal_and_one_snack():
    result = suggest_budget(training_days=1, day_part="half_morning", attendees=3)
    assert result["meal_count"] == 1
    assert result["snack_count"] == 1
    assert result["venue_key"] == "private"
    assert result["food"] == 600 * 3
    assert result["snack"] == 50 * 3
    assert result["documents"] == 70 * 3
    assert result["venue"] == 0
    afternoon = suggest_budget(training_days=1, day_part="half_afternoon", attendees=3)
    assert afternoon["meal_count"] == 1
    assert afternoon["snack_count"] == 1
    assert afternoon["food"] == result["food"]
    assert afternoon["snack"] == result["snack"]


def test_full_day_is_two_meals_and_two_snacks():
    result = suggest_budget(training_days=1, day_part="full", attendees=3)
    assert result["meal_count"] == 2
    assert result["snack_count"] == 2
    assert result["food"] == 800 * 3
    assert result["snack"] == 50 * 2 * 3
    assert result["documents"] == 70 * 3


def test_documents_repeat_for_every_training_day_and_attendee():
    result = suggest_budget(training_days=2, day_part="full", attendees=4)
    assert result["documents"] == 70 * 4 * 2
    assert result["snack"] == 50 * 2 * 4 * 2


def test_equipment_without_a_unit_price_does_not_invent_a_market_price():
    result = suggest_budget(equipment_quantity=5, equipment_unit_price=None, equipment_amount=0)
    assert result["equipment"] == 0
    assert any("ไม่ใส่ราคาตลาด" in note for note in result["assumptions"])
    priced = suggest_budget(equipment_quantity=2, equipment_unit_price=1500)
    assert priced["equipment"] == 3000


def test_worksheet_total_matches_the_calculator():
    direct = suggest_budget(team_size=2, training_days=1, day_part="full", attendees=4)
    sheet = normalize_cost_worksheet(
        {
            "apply_calculated": True,
            "team_size": 2,
            "training_days": 1,
            "day_part": "full",
            "attendees": 4,
        }
    )
    assert sheet["consultant"] == direct["consultant"]
    assert sheet["food"] == direct["food"]
    assert sheet["snack"] == direct["snack"]
    assert sheet["documents"] == direct["documents"]
    assert sheet["training"] == direct["training"]
    assert sheet["total"] == direct["total"]
    assert sheet["total"] == (
        sheet["personnel"]
        + sheet["equipment"]
        + sheet["procurement"]
        + sheet["consultant"]
        + sheet["training"]
    )
    assert sheet["is_announced_price"] is False


def test_budget_agent_locks_calculated_figures():
    calculated = suggest_budget(
        team_size=2,
        years=2,
        training_days=1,
        day_part="half_morning",
        attendees=2,
    )
    message = BudgetDraftingAgent().build_user_message(
        {"budget": 1_000, "calculated_budget": calculated},
        [],
    )
    assert "ห้ามเปลี่ยนตัวเลข" in message
    rate = f"{calculated['consultants'][0]['monthly_rate']:,}"
    assert rate in message
    assert "ห้ามเปลี่ยนตัวเลข" in BudgetDraftingAgent().get_system_prompt()


def test_budget_rule_findings_cover_the_shared_rules():
    text = (
        "วงเงินงบประมาณสำหรับจัดซื้อครุภัณฑ์ตามขอบเขตงาน "
        "ใช้บุคลากรของรัฐเป็นอัตราค่าจ้างที่ปรึกษา "
        "จัดการฝึกอบรมครึ่งวันแต่กำหนดอาหาร 2 มื้อ ที่สถานที่ของหน่วยงาน "
        "เกณฑ์ราคาพิจารณาจากวงเงินรวม"
    )
    findings = budget_rule_findings(text)
    by_id = {item["rule_id"]: item for item in findings}
    assert "government_staff_default" in by_id
    assert "agency_venue" in by_id
    assert "training_meal_mismatch" in by_id
    assert "missing_training_documents" in by_id
    assert "evaluation_budget_coverage" in by_id
    assert "missing_consultant_category" not in by_id
    for item in findings:
        assert set(item) == {"rule_id", "severity", "message", "suggestion", "evidence"}
        assert item["severity"] in {"suggestion", "warning", "error"}
        assert item["suggestion"]
    assert "ภาคเอกชน" in by_id["government_staff_default"]["suggestion"]
    assert "1 มื้อ" in by_id["training_meal_mismatch"]["suggestion"]
    assert "เอกสาร" in by_id["missing_training_documents"]["suggestion"]
    assert "โรงแรมหรือสถานที่เอกชน" in by_id["agency_venue"]["suggestion"]

    bare = "วงเงินงบประมาณรวมห้าล้านบาทสำหรับจัดซื้อครุภัณฑ์คอมพิวเตอร์ตามรายการ"
    bare_ids = {item["rule_id"] for item in budget_rule_findings(bare)}
    assert "missing_consultant_category" in bare_ids
    assert "missing_training_category" in bare_ids
    assert budget_rule_findings("สั้น") == []


def test_review_budget_scope_alignment_uses_the_same_replacement_text():
    agent = ReviewAgent()
    suggestions = agent._run_deterministic_checks(
        {
            "s4": "ขอบเขตการฝึกอบรมครึ่งวันแต่กำหนดอาหาร 2 มื้อ ที่สถานที่ของหน่วยงาน",
            "s6": "งบประมาณใช้บุคลากรของรัฐเป็นอัตราค่าจ้างที่ปรึกษา",
        },
        {},
    )
    text = " ".join(item.suggested_text for item in suggestions if item.section_key == "s6")
    assert "ภาคเอกชน" in text
    assert "1 มื้อ" in text
    assert "สถานที่เอกชน" in text


def test_printed_page_number_accepts_only_a_nearby_footer():
    assert printed_page_number("เนื้อหา\n\n16", 16) == "16"
    assert printed_page_number("เนื้อหา\n\n- 16 -", 18) == "16"
    assert printed_page_number("เนื้อหา\n\n2567", 16) is None
    assert printed_page_number("หน้า 1-14\n", 14) is None


def test_extract_pdf_keeps_text_and_records_pages(tmp_path: Path):
    pdf_path = tmp_path / "one.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "first page body text for extraction", fontsize=12)
    page.insert_text((72, 760), "1", fontsize=12)
    doc.save(pdf_path)
    doc.close()
    result = extract_pdf(str(pdf_path))
    assert "first page body text" in result.text
    assert len(result.pages) == 1
    assert result.pages[0]["index"] == 1
    assert result.pages[0]["printed"] == "1"
    assert "first page body text" in str(result.pages[0]["text"])


def _rate_pdf() -> Path:
    root = Path(__file__).resolve().parents[3] / "documents" / "sources"
    matches = [path for path in root.rglob("*.pdf") if "อบรม" in path.name and "อัตรา" in path.name]
    if not matches:
        pytest.skip("rate PDF is not in the workspace")
    return matches[0]


def test_rate_pdf_page_tables_become_markdown():
    doc = fitz.open(_rate_pdf())
    try:
        markdown = markdown_tables_from_page(doc[18])
    finally:
        doc.close()
    assert "|" in markdown
    assert "30090" in markdown.replace(",", "")


def test_table_chunks_repeat_the_header_and_stay_within_the_token_cap():
    header = "| รายการ | อัตรา |"
    separator = "| --- | --- |"
    rows = [f"| แถวที่ {index} | {1000 + index} |" for index in range(1, 41)]
    result = chunk_text(
        "\n".join([header, separator, *rows]),
        document_id="rates",
        min_chunk_size=10,
        max_chunk_size=40,
        overlap_size=0,
    )
    assert len(result.chunks) > 1
    for chunk in result.chunks:
        assert chunk.text.startswith(header)
        assert separator in chunk.text
        assert len(chunk.tokens) <= 40
