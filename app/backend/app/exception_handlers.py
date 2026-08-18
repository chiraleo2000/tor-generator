"""FastAPI exception handler functions.

Registers global exception handlers that wrap all errors in the standard
ErrorResponse envelope with Thai-language messages for user-facing errors.
"""

import logging
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import AppException, RateLimitError
from app.schemas.responses import ErrorDetail, ErrorResponse, MetaInfo

logger = logging.getLogger("tor_app.errors")


# ---------------------------------------------------------------------------
# Thai field-level error messages for common Pydantic validation errors
# ---------------------------------------------------------------------------

_THAI_FIELD_ERRORS: dict[str, str] = {
    "value_error.missing": "กรุณากรอกข้อมูลให้ครบถ้วน",
    "value_error.any_str.min_length": "ข้อมูลสั้นเกินไป",
    "value_error.any_str.max_length": "ข้อมูลยาวเกินไป",
    "type_error.integer": "กรุณาระบุเป็นตัวเลขจำนวนเต็ม",
    "type_error.float": "กรุณาระบุเป็นตัวเลข",
    "type_error.none.not_allowed": "กรุณากรอกข้อมูลให้ครบถ้วน",
    "value_error.email": "รูปแบบอีเมลไม่ถูกต้อง",
    "value_error.url": "รูปแบบ URL ไม่ถูกต้อง",
    "value_error.number.not_gt": "ค่าต้องมากกว่าค่าต่ำสุดที่กำหนด",
    "value_error.number.not_ge": "ค่าต้องมากกว่าหรือเท่ากับค่าต่ำสุดที่กำหนด",
    "value_error.number.not_lt": "ค่าต้องน้อยกว่าค่าสูงสุดที่กำหนด",
    "value_error.number.not_le": "ค่าต้องน้อยกว่าหรือเท่ากับค่าสูงสุดที่กำหนด",
}

# Mapping for Pydantic V2 error types
_THAI_TYPE_ERRORS: dict[str, str] = {
    "missing": "กรุณากรอกข้อมูลให้ครบถ้วน",
    "string_too_short": "ข้อมูลสั้นเกินไป",
    "string_too_long": "ข้อมูลยาวเกินไป",
    "int_parsing": "กรุณาระบุเป็นตัวเลขจำนวนเต็ม",
    "float_parsing": "กรุณาระบุเป็นตัวเลข",
    "value_error": "ข้อมูลไม่ถูกต้อง",
    "enum": "ค่าที่ระบุไม่อยู่ในตัวเลือกที่อนุญาต",
    "string_pattern_mismatch": "รูปแบบข้อมูลไม่ถูกต้อง",
    "too_short": "จำนวนรายการน้อยเกินไป",
    "too_long": "จำนวนรายการมากเกินไป",
    "greater_than": "ค่าต้องมากกว่าค่าต่ำสุดที่กำหนด",
    "greater_than_equal": "ค่าต้องมากกว่าหรือเท่ากับค่าต่ำสุดที่กำหนด",
    "less_than": "ค่าต้องน้อยกว่าค่าสูงสุดที่กำหนด",
    "less_than_equal": "ค่าต้องน้อยกว่าหรือเท่ากับค่าสูงสุดที่กำหนด",
    "json_invalid": "รูปแบบ JSON ไม่ถูกต้อง",
    "url_parsing": "รูปแบบ URL ไม่ถูกต้อง",
    "uuid_parsing": "รูปแบบ UUID ไม่ถูกต้อง",
}


def _get_request_id(request: Request) -> str:
    """Retrieve request_id from request state, fallback to 'unknown'."""
    return getattr(request.state, "request_id", "unknown")


def _get_timestamp() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def _translate_validation_type(error_type: str) -> str:
    """Translate a Pydantic validation error type to Thai message."""
    # Check Pydantic V2 type mapping first
    if error_type in _THAI_TYPE_ERRORS:
        return _THAI_TYPE_ERRORS[error_type]
    # Check legacy V1 style mapping
    if error_type in _THAI_FIELD_ERRORS:
        return _THAI_FIELD_ERRORS[error_type]
    # Default
    return "ข้อมูลไม่ถูกต้อง"


def _build_error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    field: str | None = None,
    details: object = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build a JSONResponse wrapped in the standard error envelope."""
    response = ErrorResponse(
        ok=False,
        error=ErrorDetail(
            code=code,
            message=message,
            field=field,
            details=details,
        ),
        meta=MetaInfo(
            request_id=_get_request_id(request),
            timestamp=_get_timestamp(),
        ),
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(),
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Exception Handlers
# ---------------------------------------------------------------------------


async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom AppException subclasses."""
    logger.warning(
        "AppException [%s] %s: %s (field=%s)",
        exc.code,
        exc.status_code,
        exc.message,
        exc.field,
    )
    headers = None
    if isinstance(exc, RateLimitError):
        headers = {"Retry-After": str(exc.retry_after)}

    return _build_error_response(
        request=request,
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        field=exc.field,
        details=exc.details,
        headers=headers,
    )


async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic request validation errors with Thai messages."""
    errors = exc.errors()

    # Build field-level error details
    field_errors = []
    for err in errors:
        loc = err.get("loc", ())
        # Skip the first element if it's 'body', 'query', or 'path'
        field_parts = [str(part) for part in loc if part not in ("body", "query", "path")]
        field_name = ".".join(field_parts) if field_parts else None

        error_type = err.get("type", "value_error")
        thai_message = _translate_validation_type(error_type)

        field_errors.append({
            "field": field_name,
            "message": thai_message,
            "type": error_type,
        })

    # Use first error's field as the top-level field
    first_field = field_errors[0]["field"] if field_errors else None

    logger.info(
        "Validation error on %s %s: %d field errors",
        request.method,
        request.url.path,
        len(field_errors),
    )

    return _build_error_response(
        request=request,
        status_code=422,
        code="VALIDATION_ERROR",
        message="กรุณากรอกข้อมูลให้ครบถ้วน",
        field=first_field,
        details=field_errors,
    )


async def handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle Starlette/FastAPI HTTPException and wrap in standard envelope."""
    # Map common status codes to Thai messages
    status_messages: dict[int, tuple[str, str]] = {
        400: ("VALIDATION_ERROR", "ข้อมูลไม่ถูกต้อง"),
        401: ("AUTH_ERROR", "คุณไม่มีสิทธิ์เข้าถึง"),
        403: ("FORBIDDEN", "คุณไม่มีสิทธิ์ดำเนินการนี้"),
        404: ("NOT_FOUND", "ไม่พบข้อมูลที่ต้องการ"),
        405: ("METHOD_NOT_ALLOWED", "ไม่รองรับวิธีการร้องขอนี้"),
        429: ("RATE_LIMITED", "เกินจำนวนคำขอที่อนุญาต"),
        500: ("INTERNAL_ERROR", "เกิดข้อผิดพลาดภายในระบบ"),
        502: ("BAD_GATEWAY", "ไม่สามารถเชื่อมต่อบริการภายนอกได้"),
        503: ("SERVICE_UNAVAILABLE", "ระบบไม่พร้อมให้บริการชั่วคราว"),
        504: ("TIMEOUT", "การดำเนินการใช้เวลานานเกินไป"),
    }

    code, message = status_messages.get(
        exc.status_code,
        ("ERROR", str(exc.detail) if exc.detail else "เกิดข้อผิดพลาด"),
    )

    # Use the detail from the exception if it's a custom string message
    if exc.detail and isinstance(exc.detail, str) and exc.status_code not in status_messages:
        message = exc.detail

    logger.warning(
        "HTTPException %d on %s %s: %s",
        exc.status_code,
        request.method,
        request.url.path,
        exc.detail,
    )

    headers = None
    if exc.status_code == 429 and hasattr(exc, "headers") and exc.headers:
        headers = dict(exc.headers)

    return _build_error_response(
        request=request,
        status_code=exc.status_code,
        code=code,
        message=message,
        headers=headers,
    )


async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with a generic Thai error message.

    Never exposes internal error details to the client.
    """
    logger.exception(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        str(exc),
    )

    return _build_error_response(
        request=request,
        status_code=500,
        code="INTERNAL_ERROR",
        message="เกิดข้อผิดพลาดภายในระบบ กรุณาลองใหม่อีกครั้ง",
    )


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application instance."""
    app.add_exception_handler(AppException, handle_app_exception)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, handle_request_validation_error)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, handle_generic_exception)  # type: ignore[arg-type]
