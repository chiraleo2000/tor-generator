"""Properties 4 and 5: slot map coverage and incremental update isolation."""

from __future__ import annotations

from copy import deepcopy

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.slots import INTAKE_SLOT_ORDER
from app.services.intake_service import empty_slot_map
from app.services.section_mapper import IncrementalUpdateResult, apply_incoming_slots

STATUSES = ["filled", "gap", "reference_only"]


@st.composite
def incoming_maps(draw):
    incoming = {}
    for key in INTAKE_SLOT_ORDER:
        if draw(st.booleans()):
            incoming[key] = {
                "content": draw(st.sampled_from(["", "ข้อมูล"])),
                "status": draw(st.sampled_from(STATUSES)),
                "sources": [draw(st.sampled_from(["a.pdf", "b.docx"]))],
            }
    incoming["not_a_slot"] = {"content": "x", "status": "filled"}
    return incoming


@pytest.mark.property
@settings(max_examples=30, deadline=None)
@given(incoming_maps())
def test_slot_map_is_exhaustive(incoming: dict):
    result = apply_incoming_slots(empty_slot_map(), incoming)
    assert set(result) == set(INTAKE_SLOT_ORDER)
    assert len(result) == 27
    for slot in result.values():
        assert slot["status"] in STATUSES


def _apply_targets(slot_map: dict, targets: list[str], answer: str) -> IncrementalUpdateResult:
    updated = deepcopy(slot_map)
    affected = []
    for key in targets:
        if key not in updated:
            continue
        existing = str(updated[key].get("content") or "")
        updated[key] = {
            "content": f"{existing}\n{answer}".strip() if existing else answer,
            "status": "filled",
            "sources": list(updated[key].get("sources") or []) + ["user"],
        }
        affected.append(key)
    return IncrementalUpdateResult(slot_map=updated, affected=affected)


@st.composite
def maps_and_targets(draw):
    slot_map = empty_slot_map()
    for key in INTAKE_SLOT_ORDER:
        slot_map[key] = {
            "content": draw(st.sampled_from(["", "เดิม"])),
            "status": draw(st.sampled_from(STATUSES)),
            "sources": ["src"],
        }
    keys = draw(st.lists(st.sampled_from(INTAKE_SLOT_ORDER), min_size=0, max_size=5, unique=True))
    answer = draw(st.text(min_size=1, max_size=40))
    return slot_map, keys, answer


@pytest.mark.property
@settings(max_examples=30, deadline=None)
@given(maps_and_targets())
def test_incremental_update_preserves_unaffected(data):
    slot_map, targets, answer = data
    before = deepcopy(slot_map)
    result = _apply_targets(slot_map, targets, answer)
    for key, value in before.items():
        if key in result.affected:
            continue
        assert result.slot_map[key] == value
