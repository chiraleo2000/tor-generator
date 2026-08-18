"""Standardized API response envelope schemas.

All API responses use a consistent envelope format:
- Success: {ok: true, data: ..., meta: {requestId, timestamp}}
- Error:   {ok: false, error: {code, message, field?, details?}, meta: {requestId, timestamp}}
"""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Structured error information."""

    code: str = Field(
        ...,
        description="Machine-readable error code (e.g. VALIDATION_ERROR, AUTH_ERROR, RATE_LIMITED, TIMEOUT)",
    )
    message: str = Field(
        ...,
        description="Human-readable error message (Thai or English)",
    )
    field: str | None = Field(
        default=None,
        description="Specific field that caused the error, if applicable",
    )
    details: Any = Field(
        default=None,
        description="Additional error details (validation errors list, etc.)",
    )


class MetaInfo(BaseModel):
    """Request metadata included in every response."""

    request_id: str = Field(..., description="Unique identifier for this request")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the response")


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    ok: bool = Field(default=False, description="Always false for error responses")
    error: ErrorDetail
    meta: MetaInfo

    model_config = {"json_schema_extra": {"examples": [
        {
            "ok": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "กรุณากรอกข้อมูลให้ครบถ้วน",
                "field": "budget",
                "details": None,
            },
            "meta": {
                "request_id": "req_abc123",
                "timestamp": "2569-08-13T10:00:00Z",
            },
        }
    ]}}


class SuccessResponse(BaseModel):
    """Standard success response envelope."""

    ok: bool = Field(default=True, description="Always true for success responses")
    data: Any = Field(default=None, description="Response payload")
    meta: MetaInfo
