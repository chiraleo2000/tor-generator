"""Load and persist agent session graph state."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.agent_session import AgentSession
from app.orchestrator.agent_nodes import (
    confirm_node,
    detect_gaps_node,
    draft_all_node,
    export_node,
    fill_slot_node,
    human_review_node,
    ingest_node,
    map_sections_node,
    validate_draft_node,
)
from app.orchestrator.agent_state import AgentWorkflowState
from app.services.session_cache import SessionCacheService


def default_state(
    session_id: UUID,
    project_id: UUID,
    user_id: UUID,
    metadata: dict | None = None,
) -> AgentWorkflowState:
    settings = get_settings()
    return {
        "session_id": str(session_id),
        "project_id": str(project_id),
        "user_id": str(user_id),
        "phase": "idle",
        "intake_files": [],
        "intake_texts": [],
        "total_chars": 0,
        "slot_map": {},
        "coverage_map": [],
        "readiness_score": 0.0,
        "ready": False,
        "gap_questions": [],
        "gap_iteration": 0,
        "max_gap_iterations": 20,
        "last_answer": "",
        "user_confirmed": False,
        "human_approved": False,
        "human_feedback": "",
        "section_drafts": {},
        "sections_pending": [],
        "draft_quality_scores": {},
        "overall_quality_score": 0.0,
        "validation_findings": [],
        "correction_attempts": {},
        "mandatory_review_sections": [],
        "sections_acknowledged": [],
        "export_docx_url": None,
        "export_pdf_url": None,
        "agent_timeout_seconds": settings.drafting_agent_timeout_seconds(),
        "draft_timeout_seconds": 900,
        "ingestion_timeout_seconds": 600,
        "deployment_mode": settings.deployment_mode,
        "error": None,
        "warnings": [],
        "messages": [],
        "project_metadata": metadata or {},
        "storage_backend": "minio",
    }


def merge_state(base: AgentWorkflowState, patch: dict[str, Any]) -> AgentWorkflowState:
    merged: AgentWorkflowState = dict(base)
    merged.update(patch)
    return merged


def serializable_state(state: AgentWorkflowState) -> dict[str, Any]:
    """Drop request-only handles so graph_state can be stored as JSON."""
    payload = dict(state)
    payload.pop("pending_files", None)
    return payload


async def persist_state(db: AsyncSession, row: AgentSession, state: AgentWorkflowState) -> None:
    payload = serializable_state(state)
    row.phase = str(payload.get("phase") or row.phase)
    row.slot_map = payload.get("slot_map") or {}
    row.gap_iteration = int(payload.get("gap_iteration") or 0)
    row.graph_state = payload
    row.messages = list(payload.get("messages") or [])
    row.warnings = list(payload.get("warnings") or [])
    row.updated_at = datetime.now(timezone.utc)
    db.add(row)
    await db.flush()
    await SessionCacheService().set_session_state(row.id, payload)


def load_state(row: AgentSession) -> AgentWorkflowState:
    raw = row.graph_state if isinstance(row.graph_state, dict) else {}
    state = default_state(row.id, row.project_id, row.user_id)
    state.update(raw)
    state["session_id"] = str(row.id)
    state["project_id"] = str(row.project_id)
    state["user_id"] = str(row.user_id)
    state["phase"] = row.phase or state.get("phase") or "idle"
    state["slot_map"] = row.slot_map or state.get("slot_map") or {}
    state["gap_iteration"] = row.gap_iteration
    state["messages"] = row.messages or []
    state["warnings"] = row.warnings or []
    return state


async def run_start(state: AgentWorkflowState) -> AgentWorkflowState:
    state = merge_state(state, await ingest_node(state))
    if state.get("phase") == "error":
        return state
    state = merge_state(state, await map_sections_node(state))
    return merge_state(state, await detect_gaps_node(state))


async def run_answer(state: AgentWorkflowState, answer: str) -> AgentWorkflowState:
    state = merge_state(state, {"last_answer": answer, "phase": "gap_filling"})
    state = merge_state(state, await fill_slot_node(state))
    return merge_state(state, await detect_gaps_node(state))


async def run_confirm(state: AgentWorkflowState, confirmed: bool) -> AgentWorkflowState:
    state = merge_state(state, {"user_confirmed": confirmed})
    state = merge_state(state, confirm_node(state))
    if not confirmed:
        return merge_state(state, await detect_gaps_node(state))
    state = merge_state(state, await draft_all_node(state))
    return merge_state(state, await validate_draft_node(state))


async def run_review(
    state: AgentWorkflowState,
    approved: bool,
    feedback: str | None,
    acknowledged: list[str],
) -> AgentWorkflowState:
    merged_ack = list(state.get("sections_acknowledged") or [])
    for key in acknowledged:
        if key not in merged_ack:
            merged_ack.append(key)
    state = merge_state(
        state,
        {
            "human_approved": approved,
            "human_feedback": feedback or "",
            "sections_acknowledged": merged_ack,
        },
    )
    state = merge_state(state, human_review_node(state))
    if state.get("phase") == "drafting":
        state = merge_state(state, await draft_all_node(state))
        return merge_state(state, await validate_draft_node(state))
    if state.get("phase") == "exporting":
        return merge_state(state, await export_node(state))
    return state
