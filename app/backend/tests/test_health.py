"""Unit tests for health check endpoints.

Tests the GET /health and GET /health/ready endpoints with various
combinations of service availability (up/down) to verify aggregate
status logic.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def mock_db_engine():
    """Mock async SQLAlchemy engine that succeeds on SELECT 1."""
    engine = MagicMock()
    conn_mock = AsyncMock()
    conn_mock.execute = AsyncMock(return_value=None)

    # Make async context manager work
    connect_cm = AsyncMock()
    connect_cm.__aenter__ = AsyncMock(return_value=conn_mock)
    connect_cm.__aexit__ = AsyncMock(return_value=False)
    engine.connect = MagicMock(return_value=connect_cm)
    return engine


@pytest.fixture
def mock_db_engine_down():
    """Mock async SQLAlchemy engine that raises on connect."""
    engine = MagicMock()
    connect_cm = AsyncMock()
    connect_cm.__aenter__ = AsyncMock(side_effect=Exception("Connection refused"))
    connect_cm.__aexit__ = AsyncMock(return_value=False)
    engine.connect = MagicMock(return_value=connect_cm)
    return engine


@pytest.fixture
def mock_redis():
    """Mock Redis client that responds to PING."""
    redis = AsyncMock()
    redis.ping = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def mock_redis_down():
    """Mock Redis client that raises on PING."""
    redis = AsyncMock()
    redis.ping = AsyncMock(side_effect=Exception("Connection refused"))
    return redis


@pytest.fixture
def mock_minio():
    """Mock MinIO client that succeeds on bucket_exists."""
    minio = MagicMock()
    minio.bucket_exists = MagicMock(return_value=True)
    return minio


@pytest.fixture
def mock_minio_down():
    """Mock MinIO client that raises on bucket_exists."""
    minio = MagicMock()
    minio.bucket_exists = MagicMock(side_effect=Exception("Connection refused"))
    return minio


@pytest.fixture
def mock_mongo():
    mongo = MagicMock()
    mongo.admin.command = MagicMock(return_value={"ok": 1})
    return mongo


@pytest.fixture
def mock_neo4j():
    driver = MagicMock()
    driver.verify_connectivity = AsyncMock(return_value=None)
    return driver


def _core_up(monkeypatch, app, mock_db_engine, mock_redis, mock_minio, mock_mongo, mock_neo4j):
    monkeypatch.setattr(app.state, "db_engine", mock_db_engine, raising=False)
    monkeypatch.setattr(app.state, "redis", mock_redis, raising=False)
    monkeypatch.setattr(app.state, "minio", mock_minio, raising=False)
    monkeypatch.setattr(app.state, "mongo", mock_mongo, raising=False)
    monkeypatch.setattr(app.state, "neo4j", mock_neo4j, raising=False)


@pytest.mark.asyncio
async def test_health_all_services_up(
    mock_db_engine, mock_redis, mock_minio, mock_mongo, mock_neo4j, monkeypatch
):
    """When all services are up, status should be 'healthy'."""
    _core_up(monkeypatch, app, mock_db_engine, mock_redis, mock_minio, mock_mongo, mock_neo4j)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["services"]["postgres"] == "up"
    assert data["services"]["redis"] == "up"
    assert data["services"]["minio"] == "up"
    assert data["services"]["mongo"] == "up"
    assert data["services"]["neo4j"] == "up"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_all_services_down(monkeypatch):
    """When all services are down (None), status should be 'unhealthy'."""
    monkeypatch.setattr(app.state, "db_engine", None, raising=False)
    monkeypatch.setattr(app.state, "redis", None, raising=False)
    monkeypatch.setattr(app.state, "minio", None, raising=False)
    monkeypatch.setattr(app.state, "mongo", None, raising=False)
    monkeypatch.setattr(app.state, "neo4j", None, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["services"]["postgres"] == "down"
    assert data["services"]["redis"] == "down"
    assert data["services"]["minio"] == "down"
    assert data["services"]["mongo"] == "down"
    assert data["services"]["neo4j"] == "down"


@pytest.mark.asyncio
async def test_health_degraded_postgres_down(mock_redis, mock_minio, monkeypatch):
    """When postgres is down but redis and minio are up, status should be 'degraded'."""
    monkeypatch.setattr(app.state, "db_engine", None, raising=False)
    monkeypatch.setattr(app.state, "redis", mock_redis, raising=False)
    monkeypatch.setattr(app.state, "minio", mock_minio, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["postgres"] == "down"
    assert data["services"]["redis"] == "up"
    assert data["services"]["minio"] == "up"


@pytest.mark.asyncio
async def test_health_degraded_redis_exception(
    mock_db_engine, mock_redis_down, mock_minio, monkeypatch
):
    """When redis raises an exception on ping, it should report 'down' and status is 'degraded'."""
    monkeypatch.setattr(app.state, "db_engine", mock_db_engine, raising=False)
    monkeypatch.setattr(app.state, "redis", mock_redis_down, raising=False)
    monkeypatch.setattr(app.state, "minio", mock_minio, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["postgres"] == "up"
    assert data["services"]["redis"] == "down"
    assert data["services"]["minio"] == "up"


@pytest.mark.asyncio
async def test_health_degraded_minio_exception(
    mock_db_engine, mock_redis, mock_minio_down, monkeypatch
):
    """When minio raises an exception, it should report 'down' and status is 'degraded'."""
    monkeypatch.setattr(app.state, "db_engine", mock_db_engine, raising=False)
    monkeypatch.setattr(app.state, "redis", mock_redis, raising=False)
    monkeypatch.setattr(app.state, "minio", mock_minio_down, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["postgres"] == "up"
    assert data["services"]["redis"] == "up"
    assert data["services"]["minio"] == "down"


@pytest.mark.asyncio
async def test_health_degraded_db_connect_exception(
    mock_db_engine_down, mock_redis, mock_minio, monkeypatch
):
    """When db engine raises on connect, postgres should be 'down'."""
    monkeypatch.setattr(app.state, "db_engine", mock_db_engine_down, raising=False)
    monkeypatch.setattr(app.state, "redis", mock_redis, raising=False)
    monkeypatch.setattr(app.state, "minio", mock_minio, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["services"]["postgres"] == "down"
    assert data["services"]["redis"] == "up"
    assert data["services"]["minio"] == "up"


@pytest.mark.asyncio
async def test_readiness_ready(mock_db_engine, mock_redis, monkeypatch):
    """When DB and Redis are up, readiness status should be 'ready'."""
    monkeypatch.setattr(app.state, "db_engine", mock_db_engine, raising=False)
    monkeypatch.setattr(app.state, "redis", mock_redis, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["services"]["postgres"] == "up"
    assert data["services"]["redis"] == "up"


@pytest.mark.asyncio
async def test_readiness_not_ready_db_down(mock_redis, monkeypatch):
    """When DB is down, readiness status should be 'not_ready'."""
    monkeypatch.setattr(app.state, "db_engine", None, raising=False)
    monkeypatch.setattr(app.state, "redis", mock_redis, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["services"]["postgres"] == "down"
    assert data["services"]["redis"] == "up"


@pytest.mark.asyncio
async def test_readiness_not_ready_redis_down(mock_db_engine, monkeypatch):
    """When Redis is down, readiness status should be 'not_ready'."""
    monkeypatch.setattr(app.state, "db_engine", mock_db_engine, raising=False)
    monkeypatch.setattr(app.state, "redis", None, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["services"]["postgres"] == "up"
    assert data["services"]["redis"] == "down"


@pytest.mark.asyncio
async def test_readiness_not_ready_all_down(monkeypatch):
    """When both DB and Redis are down, readiness status should be 'not_ready'."""
    monkeypatch.setattr(app.state, "db_engine", None, raising=False)
    monkeypatch.setattr(app.state, "redis", None, raising=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["services"]["postgres"] == "down"
    assert data["services"]["redis"] == "down"
