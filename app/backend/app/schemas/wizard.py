"""Pydantic schemas for wizard step endpoints.

Defines request/response models for:
- PUT /projects/{id}/steps/{step}: Save step data
- GET /projects/{id}/steps/{step}: Retrieve step data
- POST /projects/{id}/steps/{step}/draft: Trigger AI drafting
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.domain.tor_sections import STEP_SECTION_MAP, VALID_STEPS


# =============================================================================
# Request schemas
# =============================================================================


class StepDataSave(BaseModel):
    """Request body for PUT /projects/{id}/steps/{step}.

    Contains the form data from the wizard step. The content is stored
    as JSONB in the TOR sections for the corresponding step.
    """

    data: dict[str, Any] = Field(
        ...,
        description="Form data for the wizard step (key-value pairs)",
    )

    @field_validator("data")
    @classmethod
    def data_must_not_be_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("ข้อมูลต้องไม่ว่างเปล่า")
        return v


class DraftSectionRequest(BaseModel):
    """Request body for POST /projects/{id}/steps/{step}/draft.

    Optionally includes additional context or preferences for drafting.
    """

    target_section: str | None = Field(
        default=None,
        description="Specific TOR section key to draft (e.g., 's1'). "
        "If not provided, defaults to the primary section for this step.",
    )
    additional_context: dict[str, Any] | None = Field(
        default=None,
        description="Extra context to pass to the AI drafter",
    )


# =============================================================================
# Response schemas
# =============================================================================


class SectionData(BaseModel):
    """A single TOR section's data returned to the client."""

    id: uuid.UUID
    section_key: str
    sub_key: str | None = None
    content: str
    ai_draft: str | None = None
    quality_score: float | None = None
    validation_findings: dict | None = None
    is_approved: bool
    version: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class StepDataResponse(BaseModel):
    """Response for GET /projects/{id}/steps/{step}.

    Returns the step number, associated section data, and project metadata.
    """

    step: int
    project_id: uuid.UUID
    project_name: str
    current_step: int
    sections: list[SectionData]
    form_data: dict[str, Any] = Field(default_factory=dict)


class StepSaveResponse(BaseModel):
    """Response for PUT /projects/{id}/steps/{step}.

    Confirms the saved data and the version snapshot that was created.
    """

    step: int
    project_id: uuid.UUID
    sections_updated: int
    version_number: int
    message: str = "บันทึกข้อมูลเรียบร้อยแล้ว"


class DraftResponse(BaseModel):
    """Response for POST /projects/{id}/steps/{step}/draft.

    Returns the AI-generated draft along with quality information.
    """

    step: int
    project_id: uuid.UUID
    target_section: str
    draft_content: str
    quality_score: float | None = None
    validation_findings: list[dict] | None = None
    rag_retrieval_failed: bool = False
    message: str = "สร้างร่างเอกสารเรียบร้อยแล้ว"
