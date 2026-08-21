"""Unit tests for intake phase gating."""

from unittest.mock import MagicMock

from app.models.project import Project
from app.services.intake_service import (
    can_set_phase,
    clamp_draft_phase,
    has_intake_material,
    intake_unlocked_phase,
    slot_content,
)


def _project(**kwargs):
    project = MagicMock(spec=Project)
    project.status = kwargs.get("status", "draft")
    project.current_phase = kwargs.get("phase", 0)
    project.analysis_json = kwargs.get("analysis", {})
    project.extracted_fields = kwargs.get("extracted", {})
    return project


def test_empty_project_stays_at_phase_zero():
    empty = _project(phase=0)
    assert has_intake_material(empty) is False
    assert intake_unlocked_phase(empty) == 0
    assert can_set_phase(empty, 2) is False
    skipped = _project(phase=2)
    assert clamp_draft_phase(skipped) is True
    assert skipped.current_phase == 0


def test_pasted_text_does_not_unlock_until_analyzed():
    project = _project(
        extracted={"intake_texts": [{"name": "ข้อความผู้ใช้.txt", "text": "โครงการทดสอบวงเงินหนึ่งแสน"}]}
    )
    assert has_intake_material(project) is True
    assert intake_unlocked_phase(project) == 0
    assert can_set_phase(project, 1) is False
    assert can_set_phase(project, 2) is False


def test_analyzed_unlocks_qa_not_compose():
    project = _project(phase=1, analysis={"analyzed": True, "slot_map": {"s1": {"status": "gap"}}})
    assert intake_unlocked_phase(project) == 2
    assert can_set_phase(project, 2) is True
    assert can_set_phase(project, 3) is False


def test_ready_to_compose_unlocks_draft_phase_three():
    slots = {
        key: {"content": "ข้อมูลข้อเท็จจริง", "status": "filled"}
        for key in ("s1", "s2", "s5", "s6", "s7", "s4.1")
    }
    project = _project(phase=2, analysis={"ready_to_compose": True, "slot_map": slots})
    assert intake_unlocked_phase(project) == 3
    assert can_set_phase(project, 3) is True
    assert can_set_phase(project, 4) is False
    project.current_phase = 3
    project.analysis_json = {**project.analysis_json, "phase4_confirmed": True}
    assert intake_unlocked_phase(project) == 4
    assert can_set_phase(project, 4) is True


def test_clamp_skips_submitted_projects():
    project = _project(status="in_review", phase=3)
    assert clamp_draft_phase(project) is False
    assert project.current_phase == 3


def test_slot_content_reads_only_dict_slots():
    assert slot_content({"s1": {"content": "  x  "}}, "s1") == "  x  "
    assert slot_content({"s1": "not-a-slot"}, "s1") == ""
    assert slot_content({}, "s1") == ""
