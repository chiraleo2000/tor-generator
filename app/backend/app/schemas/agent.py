"""Pydantic schemas for the agent TOR workflow API."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    """Multipart create also accepts these form fields."""

    free_text: str | None = None
    name: str | None = None
    ministry: str | None = None
    budget: int | None = None
    project_type: str | None = None
    project_id: uuid.UUID | None = None


class CreateSessionResponse(BaseModel):
    session_id: uuid.UUID
    project_id: uuid.UUID
    phase: str
    coverage_map: list[dict[str, Any]] = Field(default_factory=list)
    readiness_score: float = 0.0
    ready: bool = False
    gap_questions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None


class AnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=20000)


class AnswerResponse(BaseModel):
    coverage_map: list[dict[str, Any]]
    readiness_score: float
    ready: bool
    gap_questions: list[str] = Field(default_factory=list)
    affected_slots: list[str] = Field(default_factory=list)
    phase: str
    gap_iteration: int = 0


class ConfirmRequest(BaseModel):
    user_confirmed: bool = True


class CoverageResponse(BaseModel):
    coverage_map: list[dict[str, Any]]
    readiness_score: float
    ready: bool
    gap_questions: list[str] = Field(default_factory=list)
    phase: str


class DraftResponse(BaseModel):
    section_drafts: dict[str, str]
    quality_scores: dict[str, float]
    overall_quality_score: float
    validation_findings: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    phase: str
    mandatory_review_sections: list[str] = Field(default_factory=list)


class ReviewRequest(BaseModel):
    human_approved: bool
    human_feedback: str | None = None
    acknowledged_sections: list[str] = Field(default_factory=list)


class ExportResponse(BaseModel):
    docx_url: str | None = None
    pdf_url: str | None = None
    phase: str
    error: str | None = None


class StatusResponse(BaseModel):
    session_id: uuid.UUID
    project_id: uuid.UUID
    phase: str
    readiness_score: float = 0.0
    ready: bool = False
    gap_iteration: int = 0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
