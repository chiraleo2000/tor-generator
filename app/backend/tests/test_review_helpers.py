"""Review helper packing for Phase 0 + slot facts."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from app.api.v1.endpoints.review import _project_requirements_text


def test_project_requirements_text_includes_intake_slots_and_extra():
    project = SimpleNamespace(
        analysis_json={
            "slot_map": {
                "s1": {"content": "ความเป็นมาของระบบ"},
                "_meta": {"content": "ignore"},
                "bad": "not-a-dict",
            }
        },
        custom_requirements_text=" เงื่อนไขเพิ่มเติม ",
    )
    with patch(
        "app.services.intake_service.project_intake_pack",
        return_value="เอกสารขั้นที่ 0",
    ):
        text = _project_requirements_text(project)
    assert "เอกสารขั้นที่ 0" in text
    assert "s1: ความเป็นมาของระบบ" in text
    assert "ignore" not in text
    assert "เงื่อนไขเพิ่มเติม" in text
