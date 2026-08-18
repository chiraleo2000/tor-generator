"""Pydantic schemas for template management endpoints.

Defines request/response models for:
- Template creation, update, listing, and detail
- Template publishing/unpublishing lifecycle
- Affected projects warning on unpublish/delete

Validates: Requirements 7.1, 7.2, 7.4, 7.5, 7.6, 7.8
"""

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums / Constants
# ---------------------------------------------------------------------------

TemplateStatus = Literal["draft", "published"]
TemplateIndustry = Literal["it", "construction", "consulting", "general"]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class TemplateCreateRequest(BaseModel):
    """Request body for POST /templates."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Template name",
        examples=["เทมเพลต TOR ระบบ IT"],
    )
    industry: TemplateIndustry = Field(
        ...,
        description="Industry category",
        examples=["it"],
    )
    section_structure: dict[str, Any] = Field(
        ...,
        description="Section structure definition (JSONB)",
        examples=[{"sections": [{"key": "s1", "name": "ความเป็นมา"}]}],
    )
    placeholder_guidance: dict[str, Any] = Field(
        ...,
        description="Placeholder guidance text per section (JSONB)",
        examples=[{"s1": "อธิบายความเป็นมาของโครงการ"}],
    )


class TemplateUpdateRequest(BaseModel):
    """Request body for PUT /templates/{id}."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Updated template name",
    )
    industry: Optional[TemplateIndustry] = Field(
        default=None,
        description="Updated industry category",
    )
    section_structure: Optional[dict[str, Any]] = Field(
        default=None,
        description="Updated section structure (JSONB)",
    )
    placeholder_guidance: Optional[dict[str, Any]] = Field(
        default=None,
        description="Updated placeholder guidance (JSONB)",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TemplateResponse(BaseModel):
    """Single template response data."""

    id: uuid.UUID
    name: str
    industry: str
    status: str
    section_structure: dict[str, Any]
    placeholder_guidance: dict[str, Any]
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateListItem(BaseModel):
    """Template item in list response."""

    id: uuid.UUID
    name: str
    industry: str
    status: str
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TemplateListResponse(BaseModel):
    """List of templates."""

    items: list[TemplateListItem]
    total: int


class AffectedProjectInfo(BaseModel):
    """Info about a project affected by template unpublish/delete."""

    id: uuid.UUID
    name: str
    status: str
    owner_id: uuid.UUID


class TemplateWarningResponse(BaseModel):
    """Warning response when unpublishing/deleting a template with active references."""

    warning: str = Field(
        ...,
        description="Warning message about affected projects",
    )
    affected_projects: list[AffectedProjectInfo]
    affected_count: int


class TemplateDeleteResponse(BaseModel):
    """Response after deleting a template."""

    message: str
    id: str
    had_affected_projects: bool = False
    affected_project_count: int = 0
