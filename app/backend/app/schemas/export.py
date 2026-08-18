"""Pydantic schemas for export endpoints.

Defines request/response models for:
- POST /projects/{id}/export (trigger export generation)
- GET /projects/{id}/export/status (check generation progress)
- GET /projects/{id}/export/download/{format} (redirect to signed URL)

Validates: Requirements 8.5, 8.6, 8.7, 8.8
"""

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums / Constants
# ---------------------------------------------------------------------------

ExportFormat = Literal["docx", "pdf"]
ExportStatus = Literal["pending", "generating", "completed", "failed"]


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class ExportRequest(BaseModel):
    """Request body for POST /projects/{id}/export."""

    use_thai_numerals: bool = Field(
        default=False,
        description="Use Thai numerals (๑, ๒, ๓) instead of Arabic (1, 2, 3) for section numbering",
    )
    url_ttl_hours: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Download URL validity in hours (1-168, default 24)",
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ExportFileInfo(BaseModel):
    """Information about a single exported file."""

    format: ExportFormat
    storage_path: str = Field(..., description="MinIO object path")
    download_url: Optional[str] = Field(
        default=None, description="Signed download URL (if generation complete)"
    )
    file_size_bytes: Optional[int] = Field(
        default=None, description="File size in bytes"
    )


class ExportJobResponse(BaseModel):
    """Response for export trigger and status endpoints."""

    export_id: uuid.UUID = Field(..., description="Unique export job identifier")
    project_id: uuid.UUID = Field(..., description="Project being exported")
    status: ExportStatus = Field(..., description="Current export job status")
    files: list[ExportFileInfo] = Field(
        default_factory=list, description="Generated file information"
    )
    started_at: datetime = Field(..., description="When the export was initiated")
    completed_at: Optional[datetime] = Field(
        default=None, description="When the export completed (or failed)"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error description if status is 'failed'"
    )
    retry_count: int = Field(
        default=0, description="Number of retry attempts made"
    )


class ExportDownloadResponse(BaseModel):
    """Response for download redirect endpoint."""

    download_url: str = Field(..., description="Signed MinIO download URL")
    format: ExportFormat
    expires_in_seconds: int = Field(
        ..., description="Seconds until the download URL expires"
    )
