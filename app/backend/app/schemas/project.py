"""Pydantic schemas for project CRUD endpoints.

Defines request/response models for:
- Project creation, update, listing, and detail
- Project version listing and restore
- Pagination metadata

Validates: Requirements 9.4, 9.5, 9.6, 9.9
"""

import json
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# ---------------------------------------------------------------------------
# Enums / Constants
# ---------------------------------------------------------------------------

ProjectStatus = Literal["draft", "in_review", "approved", "rejected", "archived"]
ProjectType = Literal["it", "construction", "consulting", "general"]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ProjectCreateRequest(BaseModel):
    """Request body for POST /projects."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Project name",
        examples=["โครงการจัดซื้อระบบคอมพิวเตอร์"],
    )
    ministry: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Ministry or organization name",
        examples=["กระทรวงการพัฒนาสังคมและความมั่นคงของมนุษย์"],
    )
    budget: int = Field(
        ...,
        gt=0,
        description="Project budget in baht (positive integer)",
        examples=[5000000],
    )
    project_type: ProjectType = Field(
        default="general",
        description="Project type category",
        examples=["it"],
    )
    template_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional template to use for pre-populating TOR structure",
    )


class ProjectUpdateRequest(BaseModel):
    """Request body for PUT /projects/{id}."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Updated project name",
    )
    ministry: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated ministry",
    )
    budget: Optional[int] = Field(
        default=None,
        gt=0,
        description="Updated budget in baht",
    )
    project_type: Optional[ProjectType] = Field(
        default=None,
        description="Updated project type",
    )
    status: Optional[ProjectStatus] = Field(
        default=None,
        description="Updated project status",
    )
    template_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Updated template reference",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ProjectResponse(BaseModel):
    """Single project response data."""

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    ministry: str
    budget: int
    project_type: str
    status: str
    current_step: int
    current_phase: int = 0
    analysis_json: dict = Field(default_factory=dict)
    extracted_fields: dict = Field(default_factory=dict)
    quality_score: Optional[int] = None
    template_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("current_phase", mode="before")
    @classmethod
    def _phase(cls, value: object) -> int:
        return value if isinstance(value, int) else 0

    @field_validator("analysis_json", "extracted_fields", mode="before")
    @classmethod
    def _json_dict(cls, value: object) -> dict:
        return value if isinstance(value, dict) else {}


class ProjectListItem(BaseModel):
    """Project item in paginated list (same as detail for now)."""

    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    ministry: str
    budget: int
    project_type: str
    status: str
    current_step: int
    current_phase: int = 0
    quality_score: Optional[int] = None
    template_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("current_phase", mode="before")
    @classmethod
    def _list_phase(cls, value: object) -> int:
        return value if isinstance(value, int) else 0


class PhaseUpdateRequest(BaseModel):
    """PATCH /projects/{id}/phase."""

    phase: int = Field(..., ge=0, le=4)


class AnalysisUpdateRequest(BaseModel):
    """PUT /projects/{id}/analysis — Phase 1 structured intake."""

    analysis: dict = Field(default_factory=dict)

    @field_validator("analysis")
    @classmethod
    def _cap_analysis(cls, value: dict) -> dict:
        if len(json.dumps(value, ensure_ascii=False)) > 200_000:
            raise ValueError("ข้อมูลวิเคราะห์ยาวเกินไป")
        return value


class SectionSaveRequest(BaseModel):
    """PUT /projects/{id}/sections/{sectionKey}."""

    content: str = Field(default="", max_length=50000)
    fields: dict = Field(default_factory=dict)
    filled: bool = True
    human_confirmed: bool = False


class IntakeFileMeta(BaseModel):
    """Phase 0 classified upload metadata stored in analysis_json.intake."""

    doc_class: str = Field(..., max_length=40)
    filename: str = Field(..., max_length=500)


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int = Field(..., description="Current page number (1-indexed)")
    per_page: int = Field(..., description="Items per page")
    total: int = Field(..., description="Total number of items")
    total_pages: int = Field(..., description="Total number of pages")


class ProjectListResponse(BaseModel):
    """Paginated list of projects."""

    items: list[ProjectListItem]
    pagination: PaginationMeta


class ProjectVersionResponse(BaseModel):
    """Single project version entry."""

    id: uuid.UUID
    project_id: uuid.UUID
    version_number: int
    step_number: int
    snapshot_data: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class ProjectVersionListResponse(BaseModel):
    """List of project versions."""

    items: list[ProjectVersionResponse]
    total: int
