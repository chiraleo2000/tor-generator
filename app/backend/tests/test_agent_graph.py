"""Agent graph compile and routing tests."""

from __future__ import annotations

from app.orchestrator.agent_graph import (
    build_agent_workflow_graph,
    compile_agent_workflow_graph,
    route_after_confirm,
    route_after_gaps,
    route_after_review,
    route_after_validation,
)
from app.services.intake_service import empty_slot_map


def test_graph_compiles():
    compiled = compile_agent_workflow_graph()
    assert compiled is not None
    graph = build_agent_workflow_graph()
    assert "ingest" in graph.nodes


def test_route_after_gaps_fill_when_questions():
    slot_map = empty_slot_map()
    nxt = route_after_gaps(
        {"slot_map": slot_map, "gap_questions": ["q"], "gap_iteration": 0}
    )
    assert nxt == "fill_slot"


def test_route_after_gaps_confirm_when_ready():
    slot_map = empty_slot_map()
    for key in ("s1", "s2", "s5", "s6", "s7", "s4.1"):
        slot_map[key] = {"content": "ข้อมูล", "status": "filled", "sources": []}
    nxt = route_after_gaps(
        {"slot_map": slot_map, "gap_questions": [], "gap_iteration": 0}
    )
    assert nxt == "confirm"


def test_route_after_gaps_max_iterations():
    nxt = route_after_gaps(
        {"slot_map": {}, "gap_iteration": 20, "max_gap_iterations": 20}
    )
    assert nxt == "confirm"


def test_route_after_confirm():
    assert route_after_confirm({"user_confirmed": True}) == "draft_all"
    assert route_after_confirm({"user_confirmed": False}) == "fill_slot"


def test_route_after_validation():
    assert route_after_validation({"phase": "drafting"}) == "draft_all"
    assert route_after_validation({"phase": "human_review"}) == "human_review"


def test_route_after_review():
    assert route_after_review({"human_approved": True, "phase": "exporting"}) == "export"
    assert route_after_review({"human_approved": False, "human_feedback": "แก้"}) == "draft_all"
    assert route_after_review({"human_approved": False, "phase": "human_review"}) == "wait"
