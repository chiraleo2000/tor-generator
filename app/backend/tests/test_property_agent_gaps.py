"""Properties 2 and 3: gap priority and question batch size."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.slots import FACT_REQUIRED_SLOTS, INTAKE_SLOT_ORDER
from app.services.gap_detector import MAX_QUESTIONS_PER_ROUND, GapDetector
from app.services.intake_service import empty_slot_map

STATUSES = ["filled", "gap", "reference_only"]


@st.composite
def slot_maps(draw):
    mapping = empty_slot_map()
    for key in INTAKE_SLOT_ORDER:
        status = draw(st.sampled_from(STATUSES))
        content = "ข้อมูล" if status == "filled" else ""
        mapping[key] = {"content": content, "status": status, "sources": []}
    return mapping


@pytest.mark.property
@settings(max_examples=40, deadline=None)
@given(slot_maps())
def test_fact_required_gaps_come_first(slot_map: dict):
    gaps = GapDetector().detect_gaps(slot_map)
    critical_keys: set[str] = set()
    for key in FACT_REQUIRED_SLOTS:
        if slot_map[key].get("status") != "filled":
            critical_keys.add(key)
            continue
        if not str(slot_map[key].get("content") or "").strip():
            critical_keys.add(key)
    if not critical_keys:
        return
    seen_non_critical = False
    for gap in gaps:
        if not gap.critical:
            seen_non_critical = True
            continue
        assert not seen_non_critical


@pytest.mark.property
@settings(max_examples=30, deadline=None)
@given(slot_maps())
def test_question_batch_bounded(slot_map: dict):
    detector = GapDetector()
    gaps = detector.detect_gaps(slot_map)
    questions = detector.generic_questions(gaps)
    assert len(questions) <= MAX_QUESTIONS_PER_ROUND
    assert MAX_QUESTIONS_PER_ROUND == 5
