"""Unit tests for the rate limiter module.

Tests cover:
- Requests within the limit are allowed
- Requests over the limit return 429
- Retry-after calculation
- User identification from JWT and IP
- Key building logic
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rate_limiter import (
    RateLimiter,
    _build_rate_key,
    _get_user_identifier,
    rate_limit_api,
    rate_limit_upload,
)


# ---------------------------------------------------------------------------
# RateLimiter.check_rate_limit tests
# ---------------------------------------------------------------------------


class TestRateLimiterCheckRateLimit:
    """Tests for the core RateLimiter.check_rate_limit method."""

    @pytest.mark.asyncio
    async def test_first_request_is_allowed(self):
        """First request in a window should be allowed and set expiry."""
        redis = AsyncMock()
        redis.incr.return_value = 1
        redis.expire.return_value = True

        allowed, retry_after = await RateLimiter.check_rate_limit(
            redis, "rate:user:123:api:100", limit=100
        )

        assert allowed is True
        assert retry_after == 0
        redis.incr.assert_called_once_with("rate:user:123:api:100")
        redis.expire.assert_called_once_with("rate:user:123:api:100", 60)

    @pytest.mark.asyncio
    async def test_request_at_limit_is_allowed(self):
        """Request exactly at the limit (count == limit) should be allowed."""
        redis = AsyncMock()
        redis.incr.return_value = 100

        allowed, retry_after = await RateLimiter.check_rate_limit(
            redis, "rate:user:123:api:100", limit=100
        )

        assert allowed is True
        assert retry_after == 0

    @pytest.mark.asyncio
    async def test_request_over_limit_is_rejected(self):
        """Request over the limit (count > limit) should be rejected."""
        redis = AsyncMock()
        redis.incr.return_value = 101
        redis.ttl.return_value = 45

        allowed, retry_after = await RateLimiter.check_rate_limit(
            redis, "rate:user:123:api:100", limit=100
        )

        assert allowed is False
        assert retry_after == 45

    @pytest.mark.asyncio
    async def test_retry_after_minimum_is_one_second(self):
        """When TTL is 0 or negative, retry_after should be at least 1."""
        redis = AsyncMock()
        redis.incr.return_value = 200
        redis.ttl.return_value = 0

        allowed, retry_after = await RateLimiter.check_rate_limit(
            redis, "rate:user:123:api:100", limit=100
        )

        assert allowed is False
        assert retry_after == 1

    @pytest.mark.asyncio
    async def test_expire_not_called_after_first_request(self):
        """EXPIRE should only be set when count == 1 (first request in window)."""
        redis = AsyncMock()
        redis.incr.return_value = 50

        await RateLimiter.check_rate_limit(redis, "rate:user:123:api:100", limit=100)

        redis.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_custom_window_seconds(self):
        """Custom window_seconds should be passed to EXPIRE."""
        redis = AsyncMock()
        redis.incr.return_value = 1
        redis.expire.return_value = True

        await RateLimiter.check_rate_limit(
            redis, "rate:user:123:api:100", limit=50, window_seconds=120
        )

        redis.expire.assert_called_once_with("rate:user:123:api:100", 120)


# ---------------------------------------------------------------------------
# _get_user_identifier tests
# ---------------------------------------------------------------------------


class TestGetUserIdentifier:
    """Tests for user identification from request."""

    def test_unauthenticated_uses_ip(self):
        """Without Authorization header, should use client IP."""
        request = MagicMock()
        request.headers = {}
        request.client.host = "192.168.1.100"

        identifier = _get_user_identifier(request)

        assert identifier == "ip:192.168.1.100"

    @patch("app.rate_limiter.get_settings")
    def test_authenticated_uses_user_id(self, mock_settings):
        """With valid JWT, should extract user_id from token."""
        from jose import jwt

        mock_settings.return_value = MagicMock(jwt_secret="test_secret")
        token = jwt.encode({"sub": "user-uuid-123"}, "test_secret", algorithm="HS256")

        request = MagicMock()
        request.headers = {"Authorization": f"Bearer {token}"}
        request.client.host = "192.168.1.100"

        identifier = _get_user_identifier(request)

        assert identifier == "user:user-uuid-123"

    def test_invalid_token_falls_back_to_ip(self):
        """With invalid JWT, should fall back to client IP."""
        request = MagicMock()
        request.headers = {"Authorization": "Bearer invalid-token-garbage"}
        request.client.host = "10.0.0.1"

        identifier = _get_user_identifier(request)

        assert identifier == "ip:10.0.0.1"

    def test_no_client_info_uses_unknown(self):
        """When request.client is None, should use 'unknown'."""
        request = MagicMock()
        request.headers = {}
        request.client = None

        identifier = _get_user_identifier(request)

        assert identifier == "ip:unknown"


# ---------------------------------------------------------------------------
# _build_rate_key tests
# ---------------------------------------------------------------------------


class TestBuildRateKey:
    """Tests for Redis key construction."""

    def test_key_format(self):
        """Key should follow pattern rate:{user}:{type}:{bucket}."""
        key = _build_rate_key("user:abc", "api")
        parts = key.split(":")

        assert parts[0] == "rate"
        assert parts[1] == "user"
        assert parts[2] == "abc"
        assert parts[3] == "api"
        # Last part should be the minute bucket (an integer)
        assert parts[4].isdigit()

    def test_different_endpoint_types_produce_different_keys(self):
        """API and upload endpoints should have different keys."""
        key_api = _build_rate_key("user:abc", "api")
        key_upload = _build_rate_key("user:abc", "upload")

        assert key_api != key_upload
        assert ":api:" in key_api
        assert ":upload:" in key_upload

    def test_minute_bucket_changes_over_time(self):
        """The time bucket should be based on current time // window."""
        expected_bucket = int(time.time()) // 60
        key = _build_rate_key("user:abc", "api", window_seconds=60)

        bucket_str = key.split(":")[-1]
        actual_bucket = int(bucket_str)

        # Allow 1 second tolerance for test execution time
        assert abs(actual_bucket - expected_bucket) <= 1


# ---------------------------------------------------------------------------
# rate_limit_api dependency tests
# ---------------------------------------------------------------------------


class TestRateLimitApiDependency:
    """Tests for the rate_limit_api FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_allows_request_within_limit(self):
        """Should not raise when under the limit."""
        redis = AsyncMock()
        redis.incr.return_value = 1
        redis.expire.return_value = True

        request = MagicMock()
        request.app.state.redis = redis
        request.headers = {}
        request.client.host = "10.0.0.1"

        with patch("app.rate_limiter.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(rate_limit_requests_per_minute=100)
            # Should not raise
            await rate_limit_api(request)

    @pytest.mark.asyncio
    async def test_rejects_request_over_limit(self):
        """Should raise RateLimitError when over the limit."""
        from app.exceptions import RateLimitError

        redis = AsyncMock()
        redis.incr.return_value = 101
        redis.ttl.return_value = 30

        request = MagicMock()
        request.app.state.redis = redis
        request.headers = {}
        request.client.host = "10.0.0.1"

        with patch("app.rate_limiter.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(rate_limit_requests_per_minute=100)
            with pytest.raises(RateLimitError) as exc_info:
                await rate_limit_api(request)

            assert exc_info.value.retry_after == 30
            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_allows_when_redis_unavailable(self):
        """Should allow request when Redis is None (fail open)."""
        request = MagicMock()
        request.app.state.redis = None

        # Should not raise
        await rate_limit_api(request)


# ---------------------------------------------------------------------------
# rate_limit_upload dependency tests
# ---------------------------------------------------------------------------


class TestRateLimitUploadDependency:
    """Tests for the rate_limit_upload FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_allows_upload_within_limit(self):
        """Should not raise when under the upload limit."""
        redis = AsyncMock()
        redis.incr.return_value = 5
        redis.expire.return_value = True

        request = MagicMock()
        request.app.state.redis = redis
        request.headers = {}
        request.client.host = "10.0.0.1"

        with patch("app.rate_limiter.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(rate_limit_uploads_per_minute=10)
            # Should not raise
            await rate_limit_upload(request)

    @pytest.mark.asyncio
    async def test_rejects_upload_over_limit(self):
        """Should raise RateLimitError when over the upload limit."""
        from app.exceptions import RateLimitError

        redis = AsyncMock()
        redis.incr.return_value = 11
        redis.ttl.return_value = 55

        request = MagicMock()
        request.app.state.redis = redis
        request.headers = {}
        request.client.host = "10.0.0.1"

        with patch("app.rate_limiter.get_settings") as mock_settings:
            mock_settings.return_value = MagicMock(rate_limit_uploads_per_minute=10)
            with pytest.raises(RateLimitError) as exc_info:
                await rate_limit_upload(request)

            assert exc_info.value.retry_after == 55
            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_allows_when_redis_unavailable(self):
        """Should allow upload when Redis is None (fail open)."""
        request = MagicMock()
        request.app.state.redis = None

        # Should not raise
        await rate_limit_upload(request)
