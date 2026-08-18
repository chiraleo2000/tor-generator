"""Role-Based Access Control (RBAC) module.

Provides:
- Role enum (officer, reviewer, admin)
- require_role() — FastAPI dependency that enforces user role membership
- require_project_access() — Utility that verifies a user can access a project
  based on ownership or elevated role

Validates: Requirements 9.3, 9.7
"""

from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from fastapi import Depends

from app.exceptions import AuthorizationError

if TYPE_CHECKING:
    from app.models.user import User


class Role(StrEnum):
    """System roles for RBAC.

    - officer: Can create/edit own TOR projects.
    - reviewer: Can review and approve TOR projects (read access to all).
    - admin: Full access to manage templates, users, and system settings.
    """

    OFFICER = "officer"
    REVIEWER = "reviewer"
    ADMIN = "admin"


def _get_current_user_dependency():
    """Lazy import for get_current_user to avoid circular imports.

    Task 4.2 will add get_current_user to app/deps.py. We import lazily
    so this module can be loaded even before that dependency exists.
    """
    from app.deps import get_current_user  # noqa: WPS433

    return get_current_user


def require_role(allowed_roles: list[str]):
    """Create a FastAPI dependency that checks user role membership.

    Usage in an endpoint:
        @router.get("/admin-only")
        async def admin_endpoint(
            current_user: User = Depends(require_role([Role.ADMIN]))
        ):
            ...

    Args:
        allowed_roles: List of role strings that are permitted.
            Use Role enum values for type safety.

    Returns:
        A FastAPI dependency function that resolves to the current user
        if their role is in allowed_roles, otherwise raises AuthorizationError (403).
    """
    get_current_user = _get_current_user_dependency()

    # Nested deps must use `= Depends(...)`. Annotated[...] here is not
    # injected on Python 3.14 + FastAPI 0.115 (treated as a missing body field).
    def role_checker(current_user=Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise AuthorizationError(
                message="คุณไม่มีสิทธิ์ดำเนินการนี้",
                details={
                    "required_roles": [str(role) for role in allowed_roles],
                    "user_role": current_user.role,
                },
            )
        return current_user

    return role_checker


def require_project_access(
    project_owner_id: uuid.UUID | str,
    current_user: "User",
) -> None:
    """Verify a user can access a specific project.

    Access is granted if:
    - The user is the project owner, OR
    - The user has an elevated role (admin or reviewer)

    If access is denied, raises AuthorizationError (HTTP 403).
    """
    if check_project_access(project_owner_id, current_user):
        return
    raise AuthorizationError(
        message="คุณไม่มีสิทธิ์เข้าถึงโครงการนี้",
        details={
            "project_owner_id": str(project_owner_id),
            "user_id": str(current_user.id),
            "user_role": current_user.role,
        },
    )


def check_project_access(
    project_owner_id: uuid.UUID | str,
    current_user: "User",
) -> bool:
    """Non-raising variant of project access check.

    Returns True/False without raising an exception.
    Useful for filtering project lists or conditional logic.

    Args:
        project_owner_id: The UUID of the project's owner.
        current_user: The authenticated user requesting access.

    Returns:
        True if the user can access the project, False otherwise.
    """
    if current_user.role in (Role.ADMIN, Role.REVIEWER):
        return True
    return str(project_owner_id) == str(current_user.id)
