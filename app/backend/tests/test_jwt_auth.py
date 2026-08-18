"""Unit tests for JWT authentication (Task 4.2).

Tests JWT token creation, decoding, login/logout service methods,
get_current_user dependency, and login/logout/me endpoints.
"""

import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.deps import get_db, get_redis
from app.main import app
from app.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def setup_app_state():
    """Ensure app.state has the required attributes and mock deps for tests."""
    app.state.db_session_factory = None
    app.state.db_engine = None
    app.state.redis = None
    app.state.minio = None

    # Override get_db and get_redis globally for all tests
    async def mock_get_db():
        yield AsyncMock()

    async def mock_get_redis():
        return AsyncMock()

    app.dependency_overrides[get_db] = mock_get_db
    app.dependency_overrides[get_redis] = mock_get_redis
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def fake_user():
    """Create a fake user object for testing."""
    user_id = uuid4()

    class FakeUser:
        def __init__(self):
            self.id = user_id
            self.name = "สมชาย ใจดี"
            self.email = "somchai@example.go.th"
            self.password_hash = AuthService.hash_password("SecureP@ss1")
            self.organization = "กระทรวงการพัฒนาสังคม"
            self.role = "officer"
            self.created_at = datetime(2024, 8, 15, 10, 0, 0)
            self.updated_at = datetime(2024, 8, 15, 10, 0, 0)

    return FakeUser()


# ---------------------------------------------------------------------------
# AuthService.create_token Tests
# ---------------------------------------------------------------------------


class TestCreateToken:
    """Tests for AuthService.create_token."""

    def test_returns_string_token(self):
        """create_token returns a non-empty string."""
        token = AuthService.create_token("some-user-id", "officer")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_has_three_parts(self):
        """JWT token has three dot-separated parts (header.payload.signature)."""
        token = AuthService.create_token("some-user-id", "officer")
        parts = token.split(".")
        assert len(parts) == 3

    def test_token_contains_expected_claims(self):
        """Decoded token contains sub, role, jti, iat, and exp claims."""
        user_id = str(uuid4())
        token = AuthService.create_token(user_id, "admin")
        payload = AuthService.decode_token(token)

        assert payload["sub"] == user_id
        assert payload["role"] == "admin"
        assert "jti" in payload
        assert "iat" in payload
        assert "exp" in payload

    def test_token_jti_is_unique(self):
        """Each token has a unique JTI."""
        token1 = AuthService.create_token("user1", "officer")
        token2 = AuthService.create_token("user1", "officer")
        payload1 = AuthService.decode_token(token1)
        payload2 = AuthService.decode_token(token2)
        assert payload1["jti"] != payload2["jti"]

    @patch("app.services.auth_service.get_settings")
    def test_token_expiry_matches_config(self, mock_settings):
        """Token expiry is set to configured jwt_expiry_hours from now."""
        settings = MagicMock()
        settings.jwt_secret = "test_secret_key_for_jwt_testing_123"
        settings.jwt_expiry_hours = 24
        mock_settings.return_value = settings

        token = AuthService.create_token("user-id", "officer")

        # Decode with the same secret
        from jose import jwt

        payload = jwt.decode(token, "test_secret_key_for_jwt_testing_123", algorithms=["HS256"])

        # exp should be approximately 24 hours from now
        now = int(time.time())
        expected_exp = now + 24 * 3600
        assert abs(payload["exp"] - expected_exp) < 5  # within 5 seconds


# ---------------------------------------------------------------------------
# AuthService.decode_token Tests
# ---------------------------------------------------------------------------


class TestDecodeToken:
    """Tests for AuthService.decode_token."""

    def test_valid_token_decodes_successfully(self):
        """A token created by create_token can be decoded back."""
        user_id = str(uuid4())
        token = AuthService.create_token(user_id, "reviewer")
        payload = AuthService.decode_token(token)
        assert payload["sub"] == user_id
        assert payload["role"] == "reviewer"

    def test_invalid_token_raises_authentication_error(self):
        """An invalid token string raises AuthenticationError."""
        from app.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError):
            AuthService.decode_token("invalid.token.string")

    def test_empty_string_raises_authentication_error(self):
        """Empty string raises AuthenticationError."""
        from app.exceptions import AuthenticationError

        with pytest.raises(AuthenticationError):
            AuthService.decode_token("")

    @patch("app.services.auth_service.get_settings")
    def test_expired_token_raises_authentication_error(self, mock_settings):
        """An expired token raises AuthenticationError with appropriate message."""
        from datetime import timedelta

        from jose import jwt as jose_jwt

        from app.exceptions import AuthenticationError

        settings = MagicMock()
        settings.jwt_secret = "test_secret_for_expired_token"
        settings.jwt_expiry_hours = 24
        mock_settings.return_value = settings

        # Create an already-expired token
        expired_payload = {
            "sub": "user-id",
            "role": "officer",
            "jti": str(uuid4()),
            "iat": datetime.now(timezone.utc) - timedelta(hours=25),
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jose_jwt.encode(
            expired_payload, "test_secret_for_expired_token", algorithm="HS256"
        )

        with pytest.raises(AuthenticationError) as exc_info:
            AuthService.decode_token(expired_token)
        assert "หมดอายุ" in exc_info.value.message

    @patch("app.services.auth_service.get_settings")
    def test_wrong_secret_raises_authentication_error(self, mock_settings):
        """Token signed with a different secret raises AuthenticationError."""
        from jose import jwt as jose_jwt

        from app.exceptions import AuthenticationError

        settings = MagicMock()
        settings.jwt_secret = "correct_secret"
        settings.jwt_expiry_hours = 24
        mock_settings.return_value = settings

        # Create token with a different secret
        payload = {
            "sub": "user-id",
            "role": "officer",
            "jti": str(uuid4()),
            "exp": int(time.time()) + 3600,
        }
        bad_token = jose_jwt.encode(payload, "wrong_secret", algorithm="HS256")

        with pytest.raises(AuthenticationError):
            AuthService.decode_token(bad_token)


# ---------------------------------------------------------------------------
# Login Endpoint Tests
# ---------------------------------------------------------------------------


class TestLoginEndpoint:
    """Tests for POST /api/v1/auth/login."""

    def test_missing_fields_returns_422(self, client):
        """Request without required fields returns 422."""
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_invalid_email_returns_422(self, client):
        """Request with invalid email format returns 422."""
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "not-an-email", "password": "SomePass1!"},
        )
        assert response.status_code == 422

    def test_successful_login_returns_200(self, client, fake_user):
        """Successful login returns 200 with token and user data."""
        with patch("app.api.v1.endpoints.auth.AuthService") as mock_service:
            mock_service.login = AsyncMock(return_value=(fake_user, "fake.jwt.token"))

            response = client.post(
                "/api/v1/auth/login",
                json={"email": "somchai@example.go.th", "password": "SecureP@ss1"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["token"] == "fake.jwt.token"
        assert data["data"]["user"]["email"] == "somchai@example.go.th"
        assert data["data"]["user"]["name"] == "สมชาย ใจดี"
        assert data["data"]["expires_in"] == 86400  # 24h in seconds

    def test_invalid_credentials_returns_401(self, client):
        """Invalid credentials returns 401."""
        from app.exceptions import AuthenticationError

        with patch("app.api.v1.endpoints.auth.AuthService") as mock_service:
            mock_service.login = AsyncMock(
                side_effect=AuthenticationError(
                    message="อีเมลหรือรหัสผ่านไม่ถูกต้อง",
                )
            )

            response = client.post(
                "/api/v1/auth/login",
                json={"email": "wrong@example.com", "password": "WrongPass1!"},
            )

        assert response.status_code == 401
        data = response.json()
        assert data["ok"] is False
        assert data["error"]["code"] == "AUTH_ERROR"


# ---------------------------------------------------------------------------
# Logout Endpoint Tests
# ---------------------------------------------------------------------------


class TestLogoutEndpoint:
    """Tests for POST /api/v1/auth/logout."""

    def test_logout_without_token_returns_401(self, client):
        """Request without Authorization header returns 401."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401

    def test_logout_with_invalid_token_returns_401(self, client):
        """Request with invalid Bearer token returns 401."""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_successful_logout_returns_200(self, client, fake_user):
        """Authenticated user can logout successfully."""
        from app.deps import get_current_user

        async def mock_get_current_user_dep():
            return fake_user

        app.dependency_overrides[get_current_user] = mock_get_current_user_dep

        # Create a real token for the logout logic
        token = AuthService.create_token(str(fake_user.id), fake_user.role)

        with patch("app.api.v1.endpoints.auth.AuthService") as mock_service:
            mock_service.logout = AsyncMock()

            response = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "ออกจากระบบ" in data["data"]["message"]


# ---------------------------------------------------------------------------
# Me Endpoint Tests
# ---------------------------------------------------------------------------


class TestMeEndpoint:
    """Tests for GET /api/v1/auth/me."""

    def test_me_without_token_returns_401(self, client):
        """Request without token returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_me_with_valid_token_returns_user(self, client, fake_user):
        """Authenticated request returns current user profile."""
        from app.deps import get_current_user

        async def mock_get_current_user_dep():
            return fake_user

        app.dependency_overrides[get_current_user] = mock_get_current_user_dep

        token = AuthService.create_token(str(fake_user.id), fake_user.role)

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["email"] == "somchai@example.go.th"
        assert data["data"]["name"] == "สมชาย ใจดี"
        assert data["data"]["role"] == "officer"
        assert data["data"]["organization"] == "กระทรวงการพัฒนาสังคม"
        assert "id" in data["data"]
        assert "created_at" in data["data"]
        assert "updated_at" in data["data"]


# ---------------------------------------------------------------------------
# Cookie token path
# ---------------------------------------------------------------------------


class TestCookieTokenPath:
    """HttpOnly cookie is accepted when Authorization is absent."""

    def test_extract_prefers_bearer_over_cookie(self):
        from app.auth_cookies import extract_access_token

        request = MagicMock()
        request.headers.get.return_value = "Bearer header-token"
        request.cookies.get.return_value = "cookie-token"
        assert extract_access_token(request) == "header-token"

    def test_extract_falls_back_to_cookie(self):
        from app.auth_cookies import extract_access_token

        request = MagicMock()
        request.headers.get.return_value = None
        request.cookies.get.return_value = "cookie-token"
        assert extract_access_token(request) == "cookie-token"

    def test_extract_returns_none_when_missing(self):
        from app.auth_cookies import extract_access_token

        request = MagicMock()
        request.headers.get.return_value = None
        request.cookies.get.return_value = None
        assert extract_access_token(request) is None

    @pytest.mark.asyncio
    async def test_get_current_user_from_cookie_only(self, fake_user):
        from app.deps import get_current_user

        token = AuthService.create_token(str(fake_user.id), fake_user.role)
        request = MagicMock()
        request.headers.get.return_value = None
        request.cookies.get.return_value = token
        request.app.state.redis = None

        db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = fake_user
        db.execute = AsyncMock(return_value=result)

        user = await get_current_user(request, db)
        assert user.email == fake_user.email
        db.execute.assert_awaited()


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------


class TestAuthSchemas:
    """Tests for LoginRequest, LoginResponse, UserResponse schemas."""

    def test_login_request_valid(self):
        """LoginRequest accepts valid email and password."""
        from app.schemas.auth import LoginRequest

        req = LoginRequest(email="test@example.com", password="MyPass1!")
        assert req.email == "test@example.com"
        assert req.password == "MyPass1!"

    def test_login_request_rejects_invalid_email(self):
        """LoginRequest rejects invalid email format."""
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.auth import LoginRequest

        with pytest.raises(PydanticValidationError):
            LoginRequest(email="not-email", password="MyPass1!")

    def test_user_response_from_attributes(self):
        """UserResponse can be created from ORM-like object."""
        from app.schemas.auth import UserResponse

        class FakeUser:
            def __init__(self):
                self.id = uuid4()
                self.name = "Test User"
                self.email = "test@example.com"
                self.organization = "Test Org"
                self.role = "officer"
                self.created_at = datetime(2024, 8, 15, 10, 0, 0)
                self.updated_at = datetime(2024, 8, 15, 11, 0, 0)

        user = FakeUser()
        resp = UserResponse.model_validate(user, from_attributes=True)
        assert resp.name == "Test User"
        assert resp.email == "test@example.com"
        assert resp.updated_at == datetime(2024, 8, 15, 11, 0, 0)

    def test_login_response_structure(self):
        """LoginResponse has token, user, and expires_in fields."""
        from app.schemas.auth import LoginResponse, UserResponse

        user_resp = UserResponse(
            id=uuid4(),
            name="Test",
            email="test@example.com",
            organization="Org",
            role="officer",
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 1),
        )
        login_resp = LoginResponse(token="abc.def.ghi", user=user_resp, expires_in=86400)
        assert login_resp.token == "abc.def.ghi"
        assert login_resp.expires_in == 86400
        assert login_resp.user.email == "test@example.com"
