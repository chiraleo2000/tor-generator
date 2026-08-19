"""LangGraph topology and routing for the agent TOR workflow."""

from __future__ import annotations

from typing import Literal

from langgraph.graph import END, StateGraph

from app.orchestrator.agent_nodes import (
    MAX_GAP_ITERATIONS,
    confirm_node,
    detect_gaps_node,
    draft_all_node,
    export_node,
    fill_slot_node,
    handle_error_node,
    human_review_node,
    ingest_node,
    map_sections_node,
    validate_draft_node,
)
from app.orchestrator.agent_state import AgentWorkflowState
from app.services.coverage import compute_ready


def route_after_gaps(state: AgentWorkflowState) -> Literal["confirm", "fill_slot", "handle_error"]:
    if state.get("error") and state.get("phase") == "error":
        return "handle_error"
    if int(state.get("gap_iteration") or 0) >= int(
        state.get("max_gap_iterations") or MAX_GAP_ITERATIONS
    ):
        return "confirm"
    if compute_ready(state.get("slot_map") or {}) or state.get("phase") == "confirming":
        return "confirm"
    if state.get("gap_questions"):
        return "fill_slot"
    return "confirm"


def route_after_confirm(state: AgentWorkflowState) -> Literal["draft_all", "fill_slot"]:
    if state.get("user_confirmed"):
        return "draft_all"
    return "fill_slot"


def route_after_validation(
    state: AgentWorkflowState,
) -> Literal["human_review", "draft_all"]:
    if state.get("phase") == "drafting":
        return "draft_all"
    return "human_review"


def route_after_review(state: AgentWorkflowState) -> Literal["export", "draft_all", "wait"]:
    if state.get("human_approved") and state.get("phase") in {"exporting", "complete"}:
        return "export"
    if str(state.get("human_feedback") or "").strip() and not state.get("human_approved"):
        return "draft_all"
    if state.get("phase") == "exporting":
        return "export"
    return "wait"


def build_agent_workflow_graph() -> StateGraph:
    graph = StateGraph(AgentWorkflowState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("map_sections", map_sections_node)
    graph.add_node("detect_gaps", detect_gaps_node)
    graph.add_node("fill_slot", fill_slot_node)
    graph.add_node("confirm", confirm_node)
    graph.add_node("draft_all", draft_all_node)
    graph.add_node("validate_draft", validate_draft_node)
    graph.add_node("human_review", human_review_node)
    graph.add_node("export", export_node)
    graph.add_node("handle_error", handle_error_node)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "map_sections")
    graph.add_edge("map_sections", "detect_gaps")
    graph.add_conditional_edges(
        "detect_gaps",
        route_after_gaps,
        {"confirm": "confirm", "fill_slot": "fill_slot", "handle_error": "handle_error"},
    )
    graph.add_edge("fill_slot", "detect_gaps")
    graph.add_conditional_edges(
        "confirm",
        route_after_confirm,
        {"draft_all": "draft_all", "fill_slot": "fill_slot"},
    )
    graph.add_edge("draft_all", "validate_draft")
    graph.add_conditional_edges(
        "validate_draft",
        route_after_validation,
        {"human_review": "human_review", "draft_all": "draft_all"},
    )
    graph.add_conditional_edges(
        "human_review",
        route_after_review,
        {"export": "export", "draft_all": "draft_all", "wait": END},
    )
    graph.add_edge("export", END)
    graph.add_edge("handle_error", END)
    return graph


def compile_agent_workflow_graph():
    return build_agent_workflow_graph().compile(
        interrupt_before=["fill_slot", "confirm", "human_review"]
    )
