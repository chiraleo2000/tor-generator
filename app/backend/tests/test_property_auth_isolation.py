"""Property-based tests for Authentication Token Isolation (Property 11).

Verifies that JWT tokens enforce strict project ownership boundaries:
- A valid JWT for User A never grants access to User B's projects (officer role)
- A user's own token always grants access to their own project
- Admin/reviewer tokens grant access to any project regardless of ownership

**Validates: Requirements 9.3, 9.7**

# Feature: tor-drafting-review-app, Property 11: Authentication Token Isolation
"""

import os
import uuid

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

# Ensure a stable JWT secret for testing
os.environ.setdefault("JWT_SECRET", "test_secret_key_for_property_tests_1234567890")

from app.exceptions import AuthorizationError
from app.rbac import Role, check_project_access, require_project_access
from app.services.auth_service import AuthService


class FakeUser:
    """Minimal user stand-in for RBAC testing without database dependency."""

    def __init__(self, user_id: uuid.UUID, role: str):
        self.id = user_id
        self.role = role


# Strategies for generating test data
user_uuid_strategy = st.uuids()
officer_role = st.just(Role.OFFICER)
elevated_role = st.sampled_from([Role.ADMIN, Role.REVIEWER])


@pytest.mark.property
class TestAuthTokenIsolation:
    """Property 11: Authentication Token Isolation.

    For any two distinct authenticated users, a valid JWT token for User A
    SHALL never grant access to projects owned exclusively by User B —
    project ownership is enforced at every data access point.
    """

    @given(
        user_a_id=user_uuid_strategy,
        user_b_id=user_uuid_strategy,
    )
    @settings(max_examples=200, deadline=None)
    # Feature: tor-drafting-review-app, Property 11: Authentication Token Isolation
    def test_token_for_user_a_never_grants_access_to_user_b_projects(
        self, user_a_id: uuid.UUID, user_b_id: uuid.UUID
    ):
        """JWT for User A (officer) never grants access to User B's projects.

        For any two distinct user IDs with officer role, creating a JWT for
        User A and checking access against a project owned by User B will
        always be denied.

        **Validates: Requirements 9.3, 9.7**
        """
        assume(user_a_id != user_b_id)

        # Create token for User A (officer role)
        token = AuthService.create_token(str(user_a_id), Role.OFFICER)

        # Decode to verify it belongs to User A
        payload = AuthService.decode_token(token)
        assert payload["sub"] == str(user_a_id)
        assert payload["role"] == Role.OFFICER

        # Simulate User A trying to access User B's project
        user_a = FakeUser(user_a_id, Role.OFFICER)

        # The raising variant should deny access
        with pytest.raises(AuthorizationError) as exc_info:
            require_project_access(user_b_id, user_a)

        assert exc_info.value.status_code == 403

        # The non-raising variant should return False
        has_access = check_project_access(user_b_id, user_a)
        assert has_access is False

    @given(
        user_id=user_uuid_strategy,
    )
    @settings(max_examples=200, deadline=None)
    # Feature: tor-drafting-review-app, Property 11: Authentication Token Isolation
    def test_own_token_always_grants_access_to_own_project(
        self, user_id: uuid.UUID
    ):
        """A user's own JWT always grants access to their own project.

        For any user ID, creating a token for that user and checking access
        against their own project always succeeds.

        **Validates: Requirements 9.3, 9.7**
        """
        # Create token for user
        token = AuthService.create_token(str(user_id), Role.OFFICER)

        # Decode to verify identity
        payload = AuthService.decode_token(token)
        assert payload["sub"] == str(user_id)

        # User accessing their own project should always succeed
        user = FakeUser(user_id, Role.OFFICER)

        # The raising variant should grant access (returns True)
        require_project_access(user_id, user)

        # The non-raising variant should return True
        has_access = check_project_access(user_id, user)
        assert has_access is True

    @given(
        admin_id=user_uuid_strategy,
        project_owner_id=user_uuid_strategy,
        role=elevated_role,
    )
    @settings(max_examples=200, deadline=None)
    # Feature: tor-drafting-review-app, Property 11: Authentication Token Isolation
    def test_admin_reviewer_tokens_grant_access_to_any_project(
        self, admin_id: uuid.UUID, project_owner_id: uuid.UUID, role: str
    ):
        """Admin/reviewer tokens grant access to any project regardless of ownership.

        For any admin or reviewer user, their JWT token grants access to any
        project, even if they are not the owner.

        **Validates: Requirements 9.3, 9.7**
        """
        # Create token for admin/reviewer
        token = AuthService.create_token(str(admin_id), role)

        # Decode to verify role
        payload = AuthService.decode_token(token)
        assert payload["sub"] == str(admin_id)
        assert payload["role"] == role

        # Admin/reviewer accessing any project should always succeed
        user = FakeUser(admin_id, role)

        # The raising variant should grant access (returns True)
        require_project_access(project_owner_id, user)

        # The non-raising variant should return True
        has_access = check_project_access(project_owner_id, user)
        assert has_access is True

    @given(
        user_a_id=user_uuid_strategy,
        user_b_id=user_uuid_strategy,
    )
    @settings(max_examples=100, deadline=None)
    # Feature: tor-drafting-review-app, Property 11: Authentication Token Isolation
    def test_token_identity_matches_creator(
        self, user_a_id: uuid.UUID, user_b_id: uuid.UUID
    ):
        """JWT token identity cannot be confused between users.

        Creating tokens for two different users produces tokens that
        decode to their respective user IDs — never crossed.

        **Validates: Requirements 9.3, 9.7**
        """
        assume(user_a_id != user_b_id)

        token_a = AuthService.create_token(str(user_a_id), Role.OFFICER)
        token_b = AuthService.create_token(str(user_b_id), Role.OFFICER)

        payload_a = AuthService.decode_token(token_a)
        payload_b = AuthService.decode_token(token_b)

        # Token A always identifies User A
        assert payload_a["sub"] == str(user_a_id)
        assert payload_a["sub"] != str(user_b_id)

        # Token B always identifies User B
        assert payload_b["sub"] == str(user_b_id)
        assert payload_b["sub"] != str(user_a_id)

        # Tokens are different strings
        assert token_a != token_b
