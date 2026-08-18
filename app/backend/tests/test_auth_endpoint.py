"""Unit tests for the POST /api/v1/auth/register endpoint.

Uses FastAPI's TestClient with mocked app state to test
request validation, password policy enforcement, and response format.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.deps import get_db
from app.main import app


@pytest.fixture(autouse=True)
def setup_app_state():
    """Ensure app.state has the required attributes and override DB dep for tests."""
    # Set up minimal app state so middleware doesn't crash
    app.state.db_session_factory = None
    app.state.db_engine = None
    app.state.redis = None
    app.state.minio = None

    # Override get_db globally for all tests so validation errors surface properly
    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_get_db
    yield
    # Cleanup
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def valid_register_body():
    """A valid registration request body."""
    return {
        "name": "สมชาย ใจดี",
        "email": "somchai@example.go.th",
        "password": "SecureP@ss1",
        "organization": "กระทรวงการพัฒนาสังคม",
        "role": "officer",
    }


class TestRegisterValidation:
    """Tests for request validation on POST /api/v1/auth/register."""

    def test_missing_required_fields_returns_422(self, client):
        """Request with missing fields returns 422 validation error."""
        response = client.post("/api/v1/auth/register", json={})
        assert response.status_code == 422
        data = response.json()
        assert data["ok"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_invalid_email_format_returns_422(self, client):
        """Request with invalid email returns 422."""
        body = {
            "name": "Test User",
            "email": "not-an-email",
            "password": "SecureP@ss1",
            "organization": "Test Org",
        }
        response = client.post("/api/v1/auth/register", json=body)
        assert response.status_code == 422

    def test_password_too_short_returns_422(self, client):
        """Password shorter than 8 chars is rejected by Pydantic min_length."""
        body = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "Ab1!",
            "organization": "Test Org",
        }
        response = client.post("/api/v1/auth/register", json=body)
        assert response.status_code == 422

    def test_invalid_role_returns_422(self, client):
        """Role not in allowed values returns 422."""
        body = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "SecureP@ss1",
            "organization": "Test Org",
            "role": "superadmin",
        }
        response = client.post("/api/v1/auth/register", json=body)
        assert response.status_code == 422

    def test_empty_name_returns_422(self, client):
        """Empty name is rejected by min_length validation."""
        body = {
            "name": "",
            "email": "test@example.com",
            "password": "SecureP@ss1",
            "organization": "Test Org",
        }
        response = client.post("/api/v1/auth/register", json=body)
        assert response.status_code == 422


class TestRegisterWithDb:
    """Tests for registration logic requiring DB interaction."""

    def test_successful_registration_returns_201(self, client, valid_register_body):
        """Successful registration returns 201 with user data."""
        from datetime import datetime

        fake_user_id = uuid4()

        # Create a fake user object that RegisterResponse can validate
        class FakeUser:
            def __init__(self):
                self.id = fake_user_id
                self.name = valid_register_body["name"]
                self.email = valid_register_body["email"]
                self.password_hash = "$2b$12$somefakehash"
                self.organization = valid_register_body["organization"]
                self.role = valid_register_body["role"]
                self.created_at = datetime(2024, 8, 15, 10, 0, 0)
                self.updated_at = datetime(2024, 8, 15, 10, 0, 0)

        fake_user = FakeUser()

        # Mock AuthService.register_user to return the fake user
        with patch("app.api.v1.endpoints.auth.AuthService") as mock_service:
            mock_service.register_user = AsyncMock(return_value=fake_user)

            # Override get_db to provide a mock session
            mock_session = AsyncMock()

            async def mock_get_db():
                yield mock_session

            app.dependency_overrides[get_db] = mock_get_db

            response = client.post("/api/v1/auth/register", json=valid_register_body)

        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["email"] == valid_register_body["email"]
        assert data["data"]["name"] == valid_register_body["name"]
        assert data["data"]["role"] == "officer"
        assert data["data"]["id"] == str(fake_user_id)

    def test_password_policy_violation_returns_400(self, client):
        """Weak password that passes min_length but fails policy returns 400."""
        from app.exceptions import ValidationError

        body = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "password1A",  # no special char
            "organization": "Test Org",
        }

        # Mock AuthService to raise ValidationError
        with patch("app.api.v1.endpoints.auth.AuthService") as mock_service:
            mock_service.register_user = AsyncMock(
                side_effect=ValidationError(
                    message="รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว",
                    field="password",
                    details=["รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว"],
                )
            )

            async def mock_get_db():
                yield AsyncMock()

            app.dependency_overrides[get_db] = mock_get_db

            response = client.post("/api/v1/auth/register", json=body)

        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "อักขระพิเศษ" in data["error"]["message"]

    def test_duplicate_email_returns_400(self, client, valid_register_body):
        """Registration with existing email returns 400."""
        from app.exceptions import ValidationError

        with patch("app.api.v1.endpoints.auth.AuthService") as mock_service:
            mock_service.register_user = AsyncMock(
                side_effect=ValidationError(
                    message="อีเมลนี้ถูกใช้งานแล้ว",
                    field="email",
                )
            )

            async def mock_get_db():
                yield AsyncMock()

            app.dependency_overrides[get_db] = mock_get_db

            response = client.post("/api/v1/auth/register", json=valid_register_body)

        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False
        assert data["error"]["field"] == "email"
        assert "อีเมล" in data["error"]["message"]


class TestRegisterSchemas:
    """Tests for Pydantic schema validation."""

    def test_default_role_is_officer(self):
        """When role is not provided, it defaults to 'officer'."""
        from app.schemas.auth import RegisterRequest

        req = RegisterRequest(
            name="Test User",
            email="test@example.com",
            password="SecureP@ss1",
            organization="Test Org",
        )
        assert req.role == "officer"

    def test_register_request_accepts_valid_data(self):
        """RegisterRequest schema accepts valid data."""
        from app.schemas.auth import RegisterRequest

        req = RegisterRequest(
            name="สมชาย ใจดี",
            email="somchai@example.go.th",
            password="SecureP@ss1",
            organization="กระทรวงการพัฒนาสังคม",
            role="reviewer",
        )
        assert req.name == "สมชาย ใจดี"
        assert req.email == "somchai@example.go.th"
        assert req.role == "reviewer"

    def test_register_response_from_orm_instance(self):
        """RegisterResponse can be created from ORM-like object."""
        from datetime import datetime

        from app.schemas.auth import RegisterResponse

        class FakeUser:
            def __init__(self):
                self.id = uuid4()
                self.name = "Test User"
                self.email = "test@example.com"
                self.organization = "Test Org"
                self.role = "officer"
                self.created_at = datetime(2024, 8, 15, 10, 0, 0)

        fake_user = FakeUser()
        resp = RegisterResponse.model_validate(fake_user, from_attributes=True)
        assert resp.name == "Test User"
        assert resp.email == "test@example.com"
        assert resp.role == "officer"
