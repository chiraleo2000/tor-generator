"""Shared LangGraph state for the agent-based TOR drafting workflow."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentWorkflowState(TypedDict, total=False):
    """Shared state for ingest → map → gap-fill → confirm → draft → export."""

    session_id: str
    project_id: str
    user_id: str
    phase: str
    intake_files: list[dict]
    intake_texts: list[dict]
    total_chars: int
    slot_map: dict[str, dict]
    coverage_map: list[dict]
    readiness_score: float
    ready: bool
    gap_questions: list[str]
    gap_iteration: int
    max_gap_iterations: int
    last_answer: str
    user_confirmed: bool
    human_approved: bool
    human_feedback: str
    section_drafts: dict[str, str]
    sections_pending: list[str]
    draft_quality_scores: dict[str, float]
    overall_quality_score: float
    validation_findings: list[dict]
    correction_attempts: dict[str, int]
    mandatory_review_sections: list[str]
    sections_acknowledged: list[str]
    export_docx_url: str | None
    export_pdf_url: str | None
    agent_timeout_seconds: int
    draft_timeout_seconds: int
    ingestion_timeout_seconds: int
    deployment_mode: str
    error: str | None
    warnings: list[str]
    messages: list[dict]
    pending_files: list[Any]
    free_text: str
    storage_backend: str
    project_metadata: dict
