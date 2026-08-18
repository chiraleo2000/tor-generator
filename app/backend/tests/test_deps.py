"""Unit tests for FastAPI dependency injection (app/deps.py).

Tests the get_db, get_redis, and get_minio dependencies to verify:
- They raise HTTP 503 when the service is unavailable (None in app.state)
- They return the correct client when the service is available
- get_db properly yields a session, commits on success, and rolls back on error
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.deps import get_db, get_minio, get_redis


class FakeAppState:
    """Simulates FastAPI app.state for testing."""

    def __init__(self, db_session_factory=None, redis=None, minio=None):
        self.db_session_factory = db_session_factory
        self.redis = redis
        self.minio = minio


class FakeRequest:
    """Simulates a FastAPI Request object."""

    def __init__(self, app_state: FakeAppState):
        self.app = MagicMock()
        self.app.state = app_state


# ---------------------------------------------------------------------------
# get_db tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_db_raises_503_when_no_session_factory():
    """When db_session_factory is None, get_db should raise HTTP 503."""
    request = FakeRequest(FakeAppState(db_session_factory=None))
    gen = get_db(request)
    with pytest.raises(HTTPException) as exc_info:
        await gen.__anext__()
    assert exc_info.value.status_code == 503
    assert "Database not available" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_db_yields_session_and_commits():
    """get_db should yield a session and commit on success."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    # Create a session factory that returns an async context manager
    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_cm)
    request = FakeRequest(FakeAppState(db_session_factory=mock_factory))

    # Consume the generator
    gen = get_db(request)
    session = await gen.__anext__()
    assert session is mock_session

    # Simulate generator cleanup (StopAsyncIteration means success path)
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass

    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_get_db_rolls_back_on_exception():
    """get_db should rollback the session when an exception occurs."""
    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    mock_cm = AsyncMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_cm)
    request = FakeRequest(FakeAppState(db_session_factory=mock_factory))

    gen = get_db(request)
    session = await gen.__anext__()
    assert session is mock_session

    # athrow is the only call that may raise — commit is not on this path
    with pytest.raises(RuntimeError, match="handler error"):
        await gen.athrow(RuntimeError("handler error"))

    mock_session.rollback.assert_called_once()
    mock_session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# get_redis tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_redis_raises_503_when_not_available():
    """When redis is None, get_redis should raise HTTP 503."""
    request = FakeRequest(FakeAppState(redis=None))
    with pytest.raises(HTTPException) as exc_info:
        get_redis(request)
    assert exc_info.value.status_code == 503
    assert "Redis not available" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_redis_returns_client():
    """When redis is available, get_redis should return the client."""
    mock_redis = MagicMock()
    request = FakeRequest(FakeAppState(redis=mock_redis))
    result = get_redis(request)
    assert result is mock_redis


# ---------------------------------------------------------------------------
# get_minio tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_minio_raises_503_when_not_available():
    """When minio is None, get_minio should raise HTTP 503."""
    request = FakeRequest(FakeAppState(minio=None))
    with pytest.raises(HTTPException) as exc_info:
        get_minio(request)
    assert exc_info.value.status_code == 503
    assert "MinIO not available" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_minio_returns_client():
    """When minio is available, get_minio should return the client."""
    mock_minio = MagicMock()
    request = FakeRequest(FakeAppState(minio=mock_minio))
    result = get_minio(request)
    assert result is mock_minio
