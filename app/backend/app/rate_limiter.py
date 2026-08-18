"""Rate limiting implementation using Redis fixed-window counters.

Provides FastAPI dependencies for enforcing request rate limits:
- `rate_limit_api`: 100 requests/min per user (configurable via settings)
- `rate_limit_upload`: 10 uploads/min per user (configurable via settings)

Uses a simple fixed-window approach with Redis INCR + EXPIRE:
- Key pattern: rate:{user_identifier}:{endpoint_type}:{minute_bucket}
- INCR the key, set EXPIRE to 60s on first increment
- If count > limit, reject with HTTP 429 and Retry-After header

User identification:
- Authenticated users: identified by user_id from JWT (via Authorization header)
- Unauthenticated users: identified by client IP address
"""

import time

from fastapi import Request
from redis.asyncio import Redis

from app.config import get_settings
from app.exceptions import RateLimitError


class RateLimiter:
    """Rate limiter using Redis fixed-window counters.

    Each window is 60 seconds (one minute). The key is built from:
    - user identifier (user_id from JWT or client IP)
    - endpoint type (e.g., "api" or "upload")
    - minute bucket (current timestamp divided by window size)
    """

    @staticmethod
    async def check_rate_limit(
        redis: Redis,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int]:
        """Check whether a request is within the rate limit.

        Args:
            redis: Async Redis client instance.
            key: The rate limit key (includes user id, type, and time bucket).
            limit: Maximum number of requests allowed in the window.
            window_seconds: Window duration in seconds (default 60).

        Returns:
            A tuple of (allowed, retry_after_seconds):
            - allowed: True if the request is within the limit, False otherwise.
            - retry_after_seconds: Seconds until the current window resets
              (relevant when allowed is False).
        """
        current_count = await redis.incr(key)

        # Set expiry on first request in this window
        if current_count == 1:
            await redis.expire(key, window_seconds)

        if current_count > limit:
            # Calculate how long until the key expires (window resets)
            ttl = await redis.ttl(key)
            retry_after = max(ttl, 1)  # At least 1 second
            return False, retry_after

        return True, 0


def _get_user_identifier(request: Request) -> str:
    """Extract user identifier from request.

    Priority:
    1. user_id from JWT token in Authorization header (if present and decodable)
    2. Client IP address as fallback for unauthenticated requests
    """
    # Try to extract user_id from Authorization header (JWT)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            from jose import jwt

            settings = get_settings()
            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=["HS256"],
                options={"verify_exp": False},  # Don't fail rate limiting on expired tokens
            )
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            # If token decode fails, fall through to IP-based identification
            pass

    # Fallback to client IP
    client_ip = request.client.host if request.client else "unknown"
    return f"ip:{client_ip}"


def _build_rate_key(user_identifier: str, endpoint_type: str, window_seconds: int = 60) -> str:
    """Build the Redis key for rate limiting.

    Key pattern: rate:{user_identifier}:{endpoint_type}:{minute_bucket}

    Args:
        user_identifier: User ID or IP-based identifier.
        endpoint_type: The endpoint category (e.g., "api" or "upload").
        window_seconds: Window duration for computing the time bucket.

    Returns:
        The Redis key string.
    """
    minute_bucket = int(time.time()) // window_seconds
    return f"rate:{user_identifier}:{endpoint_type}:{minute_bucket}"


async def rate_limit_api(request: Request) -> None:
    """FastAPI dependency that enforces API rate limiting (100 req/min per user).

    Raises:
        RateLimitError: When the user exceeds the configured API rate limit.

    Usage:
        @router.get("/endpoint", dependencies=[Depends(rate_limit_api)])
        async def my_endpoint(): ...
    """
    redis: Redis | None = request.app.state.redis
    if redis is None:
        # If Redis is unavailable, allow the request (fail open)
        return

    settings = get_settings()
    limit = settings.rate_limit_requests_per_minute

    user_identifier = _get_user_identifier(request)
    key = _build_rate_key(user_identifier, "api")

    allowed, retry_after = await RateLimiter.check_rate_limit(redis, key, limit)

    if not allowed:
        raise RateLimitError(
            message="เกินจำนวนคำขอที่อนุญาต กรุณารอสักครู่",
            retry_after=retry_after,
        )


async def rate_limit_upload(request: Request) -> None:
    """FastAPI dependency that enforces upload rate limiting (10 uploads/min per user).

    Raises:
        RateLimitError: When the user exceeds the configured upload rate limit.

    Usage:
        @router.post("/upload", dependencies=[Depends(rate_limit_upload)])
        async def upload_file(): ...
    """
    redis: Redis | None = request.app.state.redis
    if redis is None:
        # If Redis is unavailable, allow the request (fail open)
        return

    settings = get_settings()
    limit = settings.rate_limit_uploads_per_minute

    user_identifier = _get_user_identifier(request)
    key = _build_rate_key(user_identifier, "upload")

    allowed, retry_after = await RateLimiter.check_rate_limit(redis, key, limit)

    if not allowed:
        raise RateLimitError(
            message="เกินจำนวนการอัปโหลดที่อนุญาต กรุณารอสักครู่",
            retry_after=retry_after,
        )
