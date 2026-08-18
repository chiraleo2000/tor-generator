"""Pydantic schemas for file upload endpoints.

Defines request validation and response models for:
- POST /files/upload (multipart upload)
- GET /files/{id}/extracted-text
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UploadedFileResponse(BaseModel):
    """Response schema for an uploaded file."""

    id: uuid.UUID = Field(..., description="Unique file identifier")
    project_id: Optional[uuid.UUID] = Field(None, description="Associated project ID (optional)")
    original_name: str = Field(..., description="Original filename as uploaded")
    mime_type: str = Field(..., description="MIME type of the uploaded file")
    file_size_bytes: int = Field(..., description="File size in bytes")
    ocr_status: str = Field(..., description="OCR processing status: pending|completed|failed|timeout")
    uploaded_at: datetime = Field(..., description="Upload timestamp")

    model_config = {"from_attributes": True}


class ExtractedTextResponse(BaseModel):
    """Response schema for extracted text content."""

    id: uuid.UUID = Field(..., description="File identifier")
    original_name: str = Field(..., description="Original filename")
    extracted_text: Optional[str] = Field(None, description="Extracted text content")
    ocr_status: str = Field(..., description="OCR processing status")
    warnings: list[str] = Field(default_factory=list, description="OCR/extraction warnings")

    model_config = {"from_attributes": True}
