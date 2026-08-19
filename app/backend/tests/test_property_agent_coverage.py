"""Property 1: coverage readiness score is the ratio of filled fact-required slots."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.slots import FACT_REQUIRED_SLOTS, INTAKE_SLOT_ORDER
from app.services.coverage import (
    build_coverage_map,
    compute_readiness_score,
    compute_ready,
)

STATUSES = ["filled", "gap", "reference_only"]


def _slot(status: str, content: str) -> dict:
    return {"content": content, "status": status, "sources": []}


@st.composite
def slot_maps(draw):
    mapping = {}
    for key in INTAKE_SLOT_ORDER:
        status = draw(st.sampled_from(STATUSES))
        content = draw(st.sampled_from(["", "มีข้อมูลโครงการ"]))
        if status != "filled":
            content = draw(st.sampled_from(["", "อ้างอิงกฎหมาย"]))
        mapping[key] = _slot(status, content)
    return mapping


@pytest.mark.property
@settings(max_examples=40, deadline=None)
@given(slot_maps())
def test_readiness_is_filled_fact_required_ratio(slot_map: dict):
    filled = 0
    for key in FACT_REQUIRED_SLOTS:
        slot = slot_map[key]
        if slot["status"] == "filled" and str(slot["content"]).strip():
            filled += 1
    expected = filled / 6
    assert compute_readiness_score(slot_map) == expected
    assert compute_ready(slot_map) is (filled == len(FACT_REQUIRED_SLOTS))


@pytest.mark.property
@settings(max_examples=20, deadline=None)
@given(slot_maps())
def test_coverage_map_has_27_slots(slot_map: dict):
    rows = build_coverage_map(slot_map)
    assert len(rows) == 27
    assert {row["key"] for row in rows} == set(INTAKE_SLOT_ORDER)
