"""Unit tests for RBAC module.

Tests the Role enum, require_project_access, and check_project_access utilities.
The require_role dependency is tested via integration (endpoint) tests since it
depends on FastAPI's dependency injection mechanism.
"""

import uuid

import pytest

from app.exceptions import AuthorizationError
from app.rbac import Role, check_project_access, require_project_access


class FakeUser:
    """Minimal user stand-in for RBAC testing (no DB needed)."""

    def __init__(self, user_id: uuid.UUID, role: str):
        self.id = user_id
        self.role = role


# Fixed UUIDs for deterministic tests
OWNER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
PROJECT_OWNER_ID = OWNER_ID


class TestRoleEnum:
    """Tests for the Role StrEnum."""

    def test_role_values(self):
        """Role enum has the three expected values."""
        assert Role.OFFICER.value == "officer"
        assert Role.REVIEWER.value == "reviewer"
        assert Role.ADMIN.value == "admin"

    def test_role_is_string(self):
        """Role values can be compared directly to strings."""
        assert Role.OFFICER.value == "officer"
        assert Role.ADMIN.value == "admin"

    def test_role_membership_check(self):
        """Role values can be checked with 'in' operator on lists."""
        allowed = [Role.ADMIN, Role.REVIEWER]
        assert Role.ADMIN in allowed
        assert Role.REVIEWER in allowed
        assert Role.OFFICER not in allowed

    def test_role_string_membership(self):
        """String role values work with Role enum in lists."""
        allowed = [Role.ADMIN, Role.REVIEWER]
        assert "admin" in allowed
        assert "reviewer" in allowed
        assert "officer" not in allowed


class TestRequireProjectAccess:
    """Tests for require_project_access (raising variant)."""

    def test_owner_can_access_own_project(self):
        """Project owner (officer) can access their own project."""
        user = FakeUser(OWNER_ID, Role.OFFICER)
        require_project_access(PROJECT_OWNER_ID, user)

    def test_admin_can_access_any_project(self):
        """Admin can access any project regardless of ownership."""
        user = FakeUser(OTHER_ID, Role.ADMIN)
        require_project_access(PROJECT_OWNER_ID, user)

    def test_reviewer_can_access_any_project(self):
        """Reviewer can access any project for review purposes."""
        user = FakeUser(OTHER_ID, Role.REVIEWER)
        require_project_access(PROJECT_OWNER_ID, user)

    def test_non_owner_officer_is_denied(self):
        """Officer who doesn't own the project gets AuthorizationError."""
        user = FakeUser(OTHER_ID, Role.OFFICER)
        with pytest.raises(AuthorizationError) as exc_info:
            require_project_access(PROJECT_OWNER_ID, user)
        assert exc_info.value.status_code == 403
        assert "คุณไม่มีสิทธิ์เข้าถึงโครงการนี้" in exc_info.value.message

    def test_string_uuid_comparison(self):
        """Owner ID comparison works even when types differ (str vs UUID)."""
        user = FakeUser(OWNER_ID, Role.OFFICER)
        # Pass project_owner_id as string
        require_project_access(str(PROJECT_OWNER_ID), user)

    def test_denied_includes_details(self):
        """AuthorizationError includes project_owner_id and user info in details."""
        user = FakeUser(OTHER_ID, Role.OFFICER)
        with pytest.raises(AuthorizationError) as exc_info:
            require_project_access(PROJECT_OWNER_ID, user)
        details = exc_info.value.details
        assert details["project_owner_id"] == str(PROJECT_OWNER_ID)
        assert details["user_id"] == str(OTHER_ID)
        assert details["user_role"] == "officer"


class TestCheckProjectAccess:
    """Tests for check_project_access (non-raising variant)."""

    def test_owner_returns_true(self):
        """Owner gets True for their own project."""
        user = FakeUser(OWNER_ID, Role.OFFICER)
        assert check_project_access(PROJECT_OWNER_ID, user) is True

    def test_admin_returns_true(self):
        """Admin gets True for any project."""
        user = FakeUser(OTHER_ID, Role.ADMIN)
        assert check_project_access(PROJECT_OWNER_ID, user) is True

    def test_reviewer_returns_true(self):
        """Reviewer gets True for any project."""
        user = FakeUser(OTHER_ID, Role.REVIEWER)
        assert check_project_access(PROJECT_OWNER_ID, user) is True

    def test_non_owner_officer_returns_false(self):
        """Non-owner officer gets False without raising an exception."""
        user = FakeUser(OTHER_ID, Role.OFFICER)
        assert check_project_access(PROJECT_OWNER_ID, user) is False

    def test_string_uuid_comparison(self):
        """Works with string UUIDs for project_owner_id."""
        user = FakeUser(OWNER_ID, Role.OFFICER)
        assert check_project_access(str(PROJECT_OWNER_ID), user) is True
