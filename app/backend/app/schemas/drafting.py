"""Pydantic schemas for AI drafting and review endpoints.

Defines request/response models for:
- POST /projects/{id}/draft-section: Draft a specific TOR section
- POST /projects/{id}/review: Run full Rule Engine review
- GET /projects/{id}/suggestions: Get AI suggestions
- PUT /projects/{id}/suggestions/{sid}: Accept/dismiss suggestion
- POST /projects/{id}/validate: Real-time validation

Validates: Requirements 5.1, 6.1, 10.1, 10.3, 10.5
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Enums
# =============================================================================


class SuggestionCategory(StrEnum):
    """Categories for AI-generated suggestions."""

    COMPLIANCE = "compliance"
    CLARITY = "clarity"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"


class SuggestionStatus(StrEnum):
    """Status values for a suggestion."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"


# =============================================================================
# Draft Section
# =============================================================================


class DraftSectionRequest(BaseModel):
    """Request body for POST /projects/{id}/draft-section.

    Triggers AI-assisted drafting of a specific TOR section via the Orchestrator.
    """

    section_key: str = Field(
        ...,
        description="Target TOR section key (e.g., 's1', 's4', 's4.1')",
        pattern=r"^s([1-9]|1[0-3])(\.[0-9]{1,2})?$",
    )
    additional_context: dict[str, Any] | None = Field(
        default=None,
        description="Extra context to pass to the AI drafter (user hints, preferences)",
    )


class DraftSectionResponse(BaseModel):
    """Response for POST /projects/{id}/draft-section."""

    project_id: uuid.UUID
    section_key: str
    draft_content: str
    quality_score: float | None = None
    validation_findings: list[dict[str, Any]] = Field(default_factory=list)
    rag_retrieval_failed: bool = False
    message: str = "สร้างร่างเอกสารเรียบร้อยแล้ว"


# =============================================================================
# Review
# =============================================================================


class ReviewRequest(BaseModel):
    """Request body for POST /projects/{id}/review.

    Triggers a full Rule Engine review on the assembled TOR document.
    Optionally includes specific sections to focus on.
    """

    focus_sections: list[str] | None = Field(
        default=None,
        description="Specific section keys to focus review on (optional). "
        "If None, reviews entire document.",
    )


class FindingResponse(BaseModel):
    """A single validation finding from the Rule Engine."""

    severity: str = Field(..., description="error|warning|suggestion")
    rule_violated: str
    affected_section: str
    message: str
    recommended_correction: str | None = None


class CategoryScoreResponse(BaseModel):
    """Score breakdown for a single validation category."""

    category: str
    label: str | None = None
    score: float
    weight: float


class ReviewResponse(BaseModel):
    """Response for POST /projects/{id}/review.

    Returns quality score, category breakdown, and findings.
    """

    project_id: uuid.UUID
    quality_score: int = Field(..., ge=0, le=100)
    is_valid: bool
    halted: bool = False
    missing_sections: dict[str, str] = Field(default_factory=dict)
    categories: list[CategoryScoreResponse] = Field(default_factory=list)
    findings: list[FindingResponse] = Field(default_factory=list)
    suggestions_generated: int = 0
    message: str = "ตรวจสอบเอกสารเรียบร้อยแล้ว"


# =============================================================================
# Suggestions
# =============================================================================


class SuggestionResponse(BaseModel):
    """A single AI-generated suggestion item."""

    id: uuid.UUID
    project_id: uuid.UUID
    section_key: str
    category: str
    current_text: str
    suggested_text: str
    predicted_score_improvement: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SuggestionListResponse(BaseModel):
    """Response for GET /projects/{id}/suggestions."""

    items: list[SuggestionResponse]
    total: int
    quality_score: int | None = None


class SuggestionUpdateRequest(BaseModel):
    """Request body for PUT /projects/{id}/suggestions/{sid}.

    Allows accepting or dismissing a suggestion.
    """

    status: SuggestionStatus = Field(
        ...,
        description="New status: 'accepted' or 'dismissed'",
    )

    @field_validator("status")
    @classmethod
    def status_must_be_action(cls, v: SuggestionStatus) -> SuggestionStatus:
        if v == SuggestionStatus.PENDING:
            raise ValueError("สถานะใหม่ต้องเป็น 'accepted' หรือ 'dismissed' เท่านั้น")
        return v


class SuggestionUpdateResponse(BaseModel):
    """Response for PUT /projects/{id}/suggestions/{sid}."""

    id: uuid.UUID
    status: str
    message: str = "อัปเดตข้อเสนอแนะเรียบร้อยแล้ว"


# =============================================================================
# Validate
# =============================================================================


class ValidateRequest(BaseModel):
    """Request body for POST /projects/{id}/validate.

    Triggers real-time validation on specific sections (debounced server-side).
    """

    section_key: str | None = Field(
        default=None,
        description="Specific section to validate. If None, validates all sections.",
    )
    content: str | None = Field(
        default=None,
        description="Content to validate (for real-time validation of unsaved content). "
        "If None, validates persisted content.",
    )


class ValidateResponse(BaseModel):
    """Response for POST /projects/{id}/validate.

    Returns quick validation results for real-time feedback.
    """

    project_id: uuid.UUID
    quality_score: int = Field(..., ge=0, le=100)
    is_valid: bool
    findings: list[FindingResponse] = Field(default_factory=list)
    message: str = "ตรวจสอบเรียบร้อยแล้ว"
