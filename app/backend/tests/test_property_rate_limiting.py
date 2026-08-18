"""Property-based tests for Rate Limiting Enforcement (Property 13).

Validates: Requirements 15.1, 15.5

These tests verify that:
1. For any limit N (1-1000) and request count <= N, all requests are allowed
2. For any limit N and request count > N, excess requests are rejected (not allowed)
3. Retry-after is always >= 1 second when rate limited
4. The allowed count always equals exactly the configured limit

Uses a mock Redis that simulates INCR behavior (returns incrementing count on each call).
"""

from unittest.mock import AsyncMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.rate_limiter import RateLimiter


# ---------------------------------------------------------------------------
# Mock Redis factory that simulates INCR behavior
# ---------------------------------------------------------------------------


def make_mock_redis(ttl_value: int = 30):
    """Create a mock Redis client that simulates INCR + TTL behavior.

    Each call to redis.incr(key) returns an incrementing counter starting at 1.
    redis.ttl(key) returns the specified ttl_value.
    redis.expire(key, seconds) is a no-op.
    """
    call_count = {"value": 0}

    redis = AsyncMock()

    async def incr_side_effect(key):
        call_count["value"] += 1
        return call_count["value"]

    redis.incr.side_effect = incr_side_effect
    redis.ttl.return_value = ttl_value
    redis.expire.return_value = True

    return redis, call_count


# ---------------------------------------------------------------------------
# Property 13: Rate Limiting Enforcement
# ---------------------------------------------------------------------------


@pytest.mark.property
class TestPropertyRateLimitingEnforcement:
    """Property 13: Rate Limiting Enforcement.

    **Validates: Requirements 15.1, 15.5**

    For any authenticated user, sending more than the configured rate limit
    SHALL result in HTTP 429 responses for excess requests — rate limiting
    is enforced consistently regardless of request content.
    """

    @given(
        limit=st.integers(min_value=1, max_value=1000),
        request_count=st.integers(min_value=1, max_value=2000),
    )
    @settings(max_examples=200)
    # Feature: tor-drafting-review-app, Property 13: Rate Limiting Enforcement
    @pytest.mark.asyncio
    async def test_requests_within_limit_always_allowed(self, limit, request_count):
        """Requests at or below the limit are always allowed."""
        actual_count = min(request_count, limit)
        redis, _ = make_mock_redis(ttl_value=45)

        allowed_count = 0
        for _ in range(actual_count):
            allowed, retry_after = await RateLimiter.check_rate_limit(
                redis, f"rate:test:api:{limit}", limit=limit
            )
            if allowed:
                allowed_count += 1

        # All requests within the limit must be allowed
        assert allowed_count == actual_count

    @given(
        limit=st.integers(min_value=1, max_value=1000),
        excess=st.integers(min_value=1, max_value=500),
    )
    @settings(max_examples=200)
    # Feature: tor-drafting-review-app, Property 13: Rate Limiting Enforcement
    @pytest.mark.asyncio
    async def test_excess_requests_always_rejected(self, limit, excess):
        """Requests exceeding the limit are always rejected (not allowed)."""
        total_requests = limit + excess
        redis, _ = make_mock_redis(ttl_value=45)

        rejected_count = 0
        for _ in range(total_requests):
            allowed, retry_after = await RateLimiter.check_rate_limit(
                redis, f"rate:test:api:{limit}", limit=limit
            )
            if not allowed:
                rejected_count += 1

        # Exactly the excess requests should be rejected
        assert rejected_count == excess

    @given(
        limit=st.integers(min_value=1, max_value=1000),
        ttl_value=st.integers(min_value=-10, max_value=300),
    )
    @settings(max_examples=200)
    # Feature: tor-drafting-review-app, Property 13: Rate Limiting Enforcement
    @pytest.mark.asyncio
    async def test_retry_after_always_at_least_one_second(self, limit, ttl_value):
        """When rate limited, retry_after is always >= 1 second."""
        redis, _ = make_mock_redis(ttl_value=ttl_value)

        # Exhaust the limit first
        for _ in range(limit):
            await RateLimiter.check_rate_limit(
                redis, f"rate:test:api:{limit}", limit=limit
            )

        # The next request should be rejected with retry_after >= 1
        allowed, retry_after = await RateLimiter.check_rate_limit(
            redis, f"rate:test:api:{limit}", limit=limit
        )

        assert allowed is False
        assert retry_after >= 1

    @given(
        limit=st.integers(min_value=1, max_value=1000),
        extra_requests=st.integers(min_value=0, max_value=500),
    )
    @settings(max_examples=200)
    # Feature: tor-drafting-review-app, Property 13: Rate Limiting Enforcement
    @pytest.mark.asyncio
    async def test_allowed_count_equals_exactly_configured_limit(self, limit, extra_requests):
        """The total number of allowed requests always equals exactly the configured limit."""
        total_requests = limit + extra_requests
        redis, _ = make_mock_redis(ttl_value=30)

        allowed_count = 0
        for _ in range(total_requests):
            allowed, retry_after = await RateLimiter.check_rate_limit(
                redis, f"rate:test:api:{limit}", limit=limit
            )
            if allowed:
                allowed_count += 1

        # Allowed count must be exactly the configured limit
        assert allowed_count == limit
