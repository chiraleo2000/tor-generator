"""Unit tests for AuditService.

Tests audit log creation, action validation, IP extraction,
and handling of optional fields.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.audit_log import AuditLog
from app.services.audit_service import VALID_ACTIONS, AuditService, get_client_ip


class TestGetClientIp:
    """Tests for get_client_ip helper."""

    def test_extracts_ip_from_x_forwarded_for(self):
        """Should return the first IP from X-Forwarded-For header."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "203.0.113.50, 70.41.3.18, 150.172.238.178"}
        result = get_client_ip(request)
        assert result == "203.0.113.50"

    def test_single_ip_in_x_forwarded_for(self):
        """Should handle a single IP in X-Forwarded-For."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "192.168.1.100"}
        result = get_client_ip(request)
        assert result == "192.168.1.100"

    def test_strips_whitespace_from_forwarded_ip(self):
        """Should strip whitespace from the extracted IP."""
        request = MagicMock()
        request.headers = {"X-Forwarded-For": "  10.0.0.1  , 10.0.0.2"}
        result = get_client_ip(request)
        assert result == "10.0.0.1"

    def test_falls_back_to_client_host(self):
        """Should use request.client.host when no X-Forwarded-For."""
        request = MagicMock()
        request.headers = {}
        request.client.host = "127.0.0.1"
        result = get_client_ip(request)
        assert result == "127.0.0.1"

    def test_returns_unknown_when_no_client(self):
        """Should return 'unknown' when client info is not available."""
        request = MagicMock()
        request.headers = {}
        request.client = None
        result = get_client_ip(request)
        assert result == "unknown"


class TestAuditServiceLog:
    """Tests for AuditService.log."""

    @pytest.fixture
    def mock_db(self):
        """Create a mock async database session."""
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        return db

    @pytest.fixture
    def sample_user_id(self):
        """A fixed UUID for test user references."""
        return uuid.UUID("12345678-1234-5678-1234-567812345678")

    @pytest.fixture
    def sample_resource_id(self):
        """A fixed UUID for test resource references."""
        return uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")

    @pytest.mark.asyncio
    async def test_creates_audit_entry_with_all_fields(
        self, mock_db, sample_user_id, sample_resource_id
    ):
        """Should create an AuditLog with all fields populated."""
        details = {"reason": "user initiated", "browser": "Chrome"}

        result = await AuditService.log(
            db=mock_db,
            action="create",
            resource_type="project",
            user_id=sample_user_id,
            resource_id=sample_resource_id,
            ip_address="192.168.1.100",
            details=details,
        )

        assert isinstance(result, AuditLog)
        assert result.user_id == sample_user_id
        assert result.action == "create"
        assert result.resource_type == "project"
        assert result.resource_id == sample_resource_id
        assert result.ip_address == "192.168.1.100"
        assert result.details == details
        mock_db.add.assert_called_once_with(result)
        mock_db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_creates_entry_with_none_user_id(self, mock_db):
        """Should allow None user_id for system-level events."""
        result = await AuditService.log(
            db=mock_db,
            action="login_failed",
            resource_type="auth",
            user_id=None,
            ip_address="10.0.0.1",
        )

        assert isinstance(result, AuditLog)
        assert result.user_id is None
        assert result.action == "login_failed"
        assert result.resource_type == "auth"

    @pytest.mark.asyncio
    async def test_defaults_details_to_empty_dict(self, mock_db, sample_user_id):
        """Should default details to empty dict when None."""
        result = await AuditService.log(
            db=mock_db,
            action="login",
            resource_type="session",
            user_id=sample_user_id,
            details=None,
        )

        assert result.details == {}

    @pytest.mark.asyncio
    async def test_defaults_ip_to_unknown(self, mock_db, sample_user_id):
        """Should default ip_address to 'unknown'."""
        result = await AuditService.log(
            db=mock_db,
            action="logout",
            resource_type="session",
            user_id=sample_user_id,
        )

        assert result.ip_address == "unknown"

    @pytest.mark.asyncio
    async def test_raises_value_error_for_invalid_action(self, mock_db, sample_user_id):
        """Should raise ValueError for unrecognized action types."""
        with pytest.raises(ValueError, match="Invalid audit action 'hack'"):
            await AuditService.log(
                db=mock_db,
                action="hack",
                resource_type="system",
                user_id=sample_user_id,
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "action",
        ["login", "logout", "login_failed", "create", "update", "delete", "export", "review"],
    )
    async def test_all_valid_action_types(self, mock_db, sample_user_id, action):
        """Should accept all defined valid action types."""
        result = await AuditService.log(
            db=mock_db,
            action=action,
            resource_type="test_resource",
            user_id=sample_user_id,
        )

        assert result.action == action

    @pytest.mark.asyncio
    async def test_resource_id_defaults_to_none(self, mock_db, sample_user_id):
        """Should allow resource_id to be None (e.g., for session actions)."""
        result = await AuditService.log(
            db=mock_db,
            action="login",
            resource_type="session",
            user_id=sample_user_id,
        )

        assert result.resource_id is None

    @pytest.mark.asyncio
    async def test_details_with_complex_jsonb_data(self, mock_db, sample_user_id):
        """Should handle complex nested dict data in details field."""
        details = {
            "changes": {"field": "budget", "old_value": 1000000, "new_value": 2000000},
            "metadata": {"step": 6, "wizard_complete": False},
        }

        result = await AuditService.log(
            db=mock_db,
            action="update",
            resource_type="project",
            user_id=sample_user_id,
            details=details,
        )

        assert result.details == details


class TestValidActions:
    """Tests for the VALID_ACTIONS constant."""

    def test_contains_all_required_actions(self):
        """VALID_ACTIONS should include all 8 specified action types."""
        expected = {
            "login", "logout", "login_failed", "create",
            "update", "delete", "export", "review",
        }
        assert VALID_ACTIONS == expected

    def test_is_frozen_set(self):
        """VALID_ACTIONS should be immutable."""
        assert isinstance(VALID_ACTIONS, frozenset)
