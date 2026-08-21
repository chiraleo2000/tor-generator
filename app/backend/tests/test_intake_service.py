"""Unit tests for intake analysis helpers (no live LLM)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.slots import FACT_REQUIRED_SLOTS
from app.models.project import Project
from app.services.intake_service import (
    ANALYZE_PROMPT,
    analyze_pack,
    append_intake_text,
    apply_chat_answer_to_slots,
    build_phase2_opening,
    coverage_table,
    empty_slot_map,
    fill_non_fact_reference_slots,
    fill_reference_slot,
    has_been_analyzed,
    has_intake_material,
    is_ready_to_compose,
    merge_analysis,
    next_asking_slot,
    ready_criteria_met,
    resolve_draft_section_key,
    slot_content,
)


def _project(**kwargs):
    project = MagicMock(spec=Project)
    project.id = kwargs.get("id", uuid4())
    project.status = kwargs.get("status", "draft")
    project.current_phase = kwargs.get("phase", 0)
    project.analysis_json = kwargs.get("analysis", {})
    project.extracted_fields = kwargs.get("extracted", {})
    return project


def test_coverage_table_marks_fact_slots():
    slots = empty_slot_map()
    slots["s1"] = {"content": "โครงการ", "status": "filled", "sources": []}
    rows = {row["key"]: row for row in coverage_table(slots)}
    assert rows["s1"]["filled"] is True
    assert rows["s1"]["fact_required"] is True
    assert rows["s10"]["fact_required"] is False
    assert rows["s10"]["status"] == "gap"
    assert rows["s1"]["preview"] == "โครงการ"


def test_ready_criteria_requires_filled_facts():
    slots = empty_slot_map()
    assert ready_criteria_met(slots) is False
    for key in FACT_REQUIRED_SLOTS:
        slots[key] = {"content": "ข้อมูล", "status": "filled"}
    assert ready_criteria_met(slots) is True


def test_has_been_analyzed_from_flag_or_slot_map():
    empty = _project()
    assert has_been_analyzed(empty) is False
    flagged = _project(analysis={"analyzed": True})
    assert has_been_analyzed(flagged) is True
    mapped = _project(analysis={"slot_map": {"s1": {"status": "gap"}}})
    assert has_been_analyzed(mapped) is True


def test_is_ready_to_compose_needs_flag_and_facts():
    slots = {key: {"content": "ข้อมูล", "status": "filled"} for key in FACT_REQUIRED_SLOTS}
    not_ready = _project(analysis={"slot_map": slots})
    assert is_ready_to_compose(not_ready) is False
    ready = _project(analysis={"ready_to_compose": True, "slot_map": slots})
    assert is_ready_to_compose(ready) is True


def test_append_intake_text_and_material():
    project = _project()
    append_intake_text(project, "ข้อความผู้ใช้.txt", "โครงการจัดซื้อครุภัณฑ์คอมพิวเตอร์วงเงิน")
    assert has_intake_material(project) is True
    pack = project.extracted_fields["intake_texts"]
    assert pack[0]["name"] == "ข้อความผู้ใช้.txt"
    assert "จัดซื้อ" in pack[0]["text"]


def test_merge_analysis_keeps_previous_keys():
    merged = merge_analysis({"intake_files": ["a.pdf"]}, {"analyzed": True})
    assert merged["intake_files"] == ["a.pdf"]
    assert merged["analyzed"] is True


@pytest.mark.asyncio
async def test_analyze_pack_parses_llm_json():
    payload = {
        "slot_map": {
            "s1": {"content": "โครงการจัดซื้อ", "status": "filled", "sources": ["ไฟล์"]},
            "s99": {"content": "ignore", "status": "filled"},
            "s2": {"content": "", "status": "unknown"},
        },
        "gap_questions": ["ขอวงเงินงบประมาณ"],
    }
    llm = MagicMock()
    llm.invoke = AsyncMock(return_value=MagicMock(content='{"slot_map": {}}'))
    with (
        patch("app.services.intake_service.ProviderFactory") as factory,
        patch("app.services.intake_service.parse_json_lenient", return_value=payload),
    ):
        factory.return_value.get_llm.return_value = llm
        result = await analyze_pack(_project(), "เนื้อหา", ["a.txt"])
    assert result["analyzed"] is True
    assert result["slot_map"]["s1"]["status"] == "filled"
    assert result["slot_map"]["s2"]["status"] == "gap"
    assert "s99" not in result["slot_map"]
    assert result["gap_questions"] == ["ขอวงเงินงบประมาณ"]
    llm.invoke.assert_awaited()
    assert ANALYZE_PROMPT in llm.invoke.await_args.args[0][0]["content"]


@pytest.mark.asyncio
async def test_analyze_pack_falls_back_when_json_invalid():
    llm = MagicMock()
    llm.invoke = AsyncMock(return_value=MagicMock(content="not-json"))
    with (
        patch("app.services.intake_service.ProviderFactory") as factory,
        patch(
            "app.services.intake_service.parse_json_lenient",
            side_effect=ValueError("bad"),
        ),
    ):
        factory.return_value.get_llm.return_value = llm
        result = await analyze_pack(_project(), "เนื้อหา", ["a.txt"])
    assert result["analyzed"] is True
    assert result["slot_map"]["s1"]["status"] == "gap"
    assert result["gap_questions"]


@pytest.mark.asyncio
async def test_fill_non_fact_reference_slots_skips_facts():
    slots = empty_slot_map()
    slots["s3"]["status"] = "gap"
    project = _project(analysis={"slot_map": slots})
    with patch(
        "app.services.intake_service.fill_reference_slot",
        new_callable=AsyncMock,
        return_value={"content": "อ้างระเบียบ", "sources": ["พ.ร.บ."]},
    ) as fill:
        result = await fill_non_fact_reference_slots(project, uuid4())
    assert "s3" in result["filled_keys"] or result["filled_keys"]
    assert all(key not in FACT_REQUIRED_SLOTS for key in result["filled_keys"])
    assert result["slot_map"]["s3"]["status"] == "reference_only"
    assert fill.await_count >= 1
    assert len(result["filled_keys"]) <= 8


@pytest.mark.asyncio
async def test_fill_reference_slot_joins_chunks():
    chunk = MagicMock()
    chunk.text = "วงเงินจัดซื้อโดยวิธีเฉพาะเจาะจง"
    hybrid = MagicMock()
    hybrid.chunks = [chunk]
    with patch(
        "app.services.intake_service.hybrid_retrieve",
        new_callable=AsyncMock,
        return_value=(hybrid, [{"label": "กฎกระทรวง"}], False),
    ):
        filled = await fill_reference_slot("s10", uuid4())
    assert "วงเงิน" in filled["content"]
    assert filled["sources"] == ["กฎกระทรวง"]
    assert filled["graph_degraded"] is False


@pytest.mark.asyncio
async def test_apply_slot_map_writes_sections():
    from app.services.intake_service import apply_slot_map_to_sections, slot_content

    slots = empty_slot_map()
    slots["s1"] = {"content": "โครงการจัดซื้อ", "status": "filled"}
    slots["s4.1"] = {"content": "ขอบเขตงานหลัก", "status": "filled"}
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    await apply_slot_map_to_sections(mock_db, uuid4(), slots)
    assert mock_db.add.call_count >= 1
    assert "โครงการจัดซื้อ" in slot_content(slots, "s1")


def test_apply_chat_answer_fills_next_fact_not_legal_gap():
    slots = empty_slot_map()
    slots["s1"] = {"content": "โครงการจัดซื้อ", "status": "filled", "sources": []}
    slots["s4.2"] = {"content": "", "status": "gap", "sources": []}
    updated = apply_chat_answer_to_slots(slots, "วงเงินงบประมาณสองล้านห้าแสนบาทถ้วน")
    assert updated == ["s2"]
    assert slots["s2"]["status"] == "filled"
    assert slots["s1"]["content"] == "โครงการจัดซื้อ"
    assert slots["s4.2"]["status"] == "gap"


def test_apply_chat_answer_fills_s1_first():
    slots = empty_slot_map()
    updated = apply_chat_answer_to_slots(slots, "กรมบัญชีกลางจัดซื้อระบบบริหารสัญญา")
    assert updated == ["s1"]
    assert "กรมบัญชีกลาง" in slots["s1"]["content"]


def test_apply_chat_answer_fills_only_remaining_fact():
    slots = empty_slot_map()
    for key in FACT_REQUIRED_SLOTS:
        slots[key] = {"content": "มีแล้ว", "status": "filled", "sources": []}
    slots["s7"] = {"content": "", "status": "gap", "sources": []}
    updated = apply_chat_answer_to_slots(slots, "ที่ทำการกรมบัญชีกลาง กรุงเทพมหานคร")
    assert updated == ["s7"]
    assert "กรมบัญชีกลาง" in slots["s7"]["content"]


def test_apply_chat_answer_does_not_overwrite_filled():
    slots = empty_slot_map()
    slots["s1"] = {"content": "ต้นฉบับจากเอกสาร", "status": "filled", "sources": []}
    apply_chat_answer_to_slots(slots, "จัดซื้อครุภัณฑ์คอมพิวเตอร์วงเงินหนึ่งแสนบาท")
    assert slots["s1"]["content"] == "ต้นฉบับจากเอกสาร"


def test_phase2_opening_includes_phase1_text():
    slots = empty_slot_map()
    slots["s1"] = {
        "content": "กรมบัญชีกลางจัดซื้อระบบบริหารสัญญา",
        "status": "filled",
        "sources": [],
    }
    brief = build_phase2_opening(slots, ["ขอวงเงินงบประมาณ"])
    assert "กรมบัญชีกลางจัดซื้อระบบบริหารสัญญา" in brief
    assert "ยังขาด" in brief
    assert "ไม่ต้องกรอกตาราง" in brief


def test_next_asking_slot_keeps_current_until_filled():
    slots = empty_slot_map()
    assert next_asking_slot(slots, "s1") == "s1"
    slots["s1"] = {"content": "โครงการจัดซื้อ", "status": "filled", "sources": []}
    assert next_asking_slot(slots, "s1") == "s2"
    assert next_asking_slot(slots, None) == "s2"


def test_resolve_draft_section_key_prefers_labels_and_หมวด_numbers():
    assert resolve_draft_section_key("แก้ความเป็นมาให้สั้นลง") == "s1"
    assert resolve_draft_section_key("ร่างหมวด 13 ใหม่") == "s13"
    assert resolve_draft_section_key("หมวด 1") == "s1"
    assert resolve_draft_section_key("สวัสดี") is None

