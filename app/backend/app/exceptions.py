"""Custom application exceptions.

All exceptions follow a consistent pattern with:
- HTTP status code
- Machine-readable error code
- Human-readable message (supports Thai)
- Optional field name and additional details
"""


class AppException(Exception):
    """Base application exception.

    All custom exceptions inherit from this class to enable
    unified exception handling in the FastAPI exception handlers.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        field: str | None = None,
        details: object = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field
        self.details = details
        super().__init__(message)


class AuthenticationError(AppException):
    """Raised when authentication fails (invalid credentials, expired token)."""

    def __init__(
        self,
        message: str = "คุณไม่มีสิทธิ์เข้าถึง",
        field: str | None = None,
        details: object = None,
    ) -> None:
        super().__init__(
            status_code=401,
            code="AUTH_ERROR",
            message=message,
            field=field,
            details=details,
        )


class AuthorizationError(AppException):
    """Raised when user lacks permission for the requested resource."""

    def __init__(
        self,
        message: str = "คุณไม่มีสิทธิ์ดำเนินการนี้",
        field: str | None = None,
        details: object = None,
    ) -> None:
        super().__init__(
            status_code=403,
            code="FORBIDDEN",
            message=message,
            field=field,
            details=details,
        )


class NotFoundError(AppException):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        message: str = "ไม่พบข้อมูลที่ต้องการ",
        field: str | None = None,
        details: object = None,
    ) -> None:
        super().__init__(
            status_code=404,
            code="NOT_FOUND",
            message=message,
            field=field,
            details=details,
        )


class RateLimitError(AppException):
    """Raised when user exceeds the configured rate limit."""

    def __init__(
        self,
        message: str = "เกินจำนวนคำขอที่อนุญาต",
        retry_after: int = 60,
        details: object = None,
    ) -> None:
        self.retry_after = retry_after
        super().__init__(
            status_code=429,
            code="RATE_LIMITED",
            message=message,
            field=None,
            details=details,
        )


class ValidationError(AppException):
    """Raised for business-logic validation failures (distinct from Pydantic)."""

    def __init__(
        self,
        message: str = "ข้อมูลไม่ถูกต้อง",
        field: str | None = None,
        details: object = None,
    ) -> None:
        super().__init__(
            status_code=400,
            code="VALIDATION_ERROR",
            message=message,
            field=field,
            details=details,
        )


class TimeoutError(AppException):
    """Raised when an operation exceeds its timeout limit."""

    def __init__(
        self,
        message: str = "การดำเนินการใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง",
        details: object = None,
    ) -> None:
        super().__init__(
            status_code=504,
            code="TIMEOUT",
            message=message,
            field=None,
            details=details,
        )
