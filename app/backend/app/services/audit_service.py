"""Audit logging service.

Records security-relevant events such as login, logout, login_failed,
create, update, delete, export, and review actions.

Validates: Requirements 15.7, 9.7
"""

import uuid
from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

# Valid audit action types
VALID_ACTIONS = frozenset(
    ["login", "logout", "login_failed", "create", "update", "delete", "export", "review"]
)


def get_client_ip(request: Request) -> str:
    """Extract client IP from X-Forwarded-For header or direct connection.

    Supports proxy chains by taking the first (original client) IP from
    the X-Forwarded-For header. Falls back to the direct connection host.

    Args:
        request: The incoming FastAPI Request object.

    Returns:
        The client IP address string, or "unknown" if not determinable.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class AuditService:
    """Service for creating audit log entries.

    All methods are static to allow usage without instantiation,
    following the same pattern as AuthService.
    """

    @staticmethod
    async def log(
        db: AsyncSession,
        action: str,
        resource_type: str,
        user_id: Optional[uuid.UUID] = None,
        resource_id: Optional[uuid.UUID] = None,
        ip_address: str = "unknown",
        details: Optional[dict] = None,
    ) -> AuditLog:
        """Create an audit log entry.

        Args:
            db: Async database session.
            action: The action performed. Must be one of:
                login, logout, login_failed, create, update, delete, export, review.
            resource_type: The type of resource affected (e.g. "user", "project", "tor_section").
            user_id: The ID of the user performing the action (None for system events).
            resource_id: The ID of the specific resource affected (optional).
            ip_address: The client IP address.
            details: Additional context stored as JSONB (optional).

        Returns:
            The created AuditLog ORM instance.

        Raises:
            ValueError: If the action is not a recognized audit action type.
        """
        if action not in VALID_ACTIONS:
            raise ValueError(
                f"Invalid audit action '{action}'. "
                f"Must be one of: {', '.join(sorted(VALID_ACTIONS))}"
            )

        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            details=details or {},
        )
        db.add(entry)
        await db.flush()
        return entry
