"""Health check endpoints.

Provides liveness and readiness probes for the application.
- GET /health: Checks all dependencies (PostgreSQL, Redis, MinIO) and returns aggregate status.
- GET /health/ready: Readiness probe — checks DB + Redis (critical for request handling).

Requirements: 1.5, 1.7
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Request

router = APIRouter(prefix="/health", tags=["health"])


async def _check_postgres(request: Request) -> str:
    """Check PostgreSQL connectivity by executing SELECT 1."""
    engine = getattr(request.app.state, "db_engine", None)
    if engine is None:
        return "down"
    try:
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "up"
    except Exception:
        return "down"


async def _check_redis(request: Request) -> str:
    """Check Redis connectivity by sending PING."""
    redis_client = getattr(request.app.state, "redis", None)
    if redis_client is None:
        return "down"
    try:
        result = await redis_client.ping()
        return "up" if result else "down"
    except Exception:
        return "down"


def _check_minio(request: Request) -> str:
    """Check MinIO connectivity by calling bucket_exists on the default bucket."""
    minio_client = getattr(request.app.state, "minio", None)
    if minio_client is None:
        return "down"
    try:
        # bucket_exists is a synchronous call in the minio Python SDK
        from app.config import get_settings

        settings = get_settings()
        minio_client.bucket_exists(settings.minio_bucket)
        return "up"
    except Exception:
        return "down"


def _compute_aggregate_status(services: dict[str, str]) -> str:
    """Compute aggregate status from individual service statuses.

    - healthy: all services are up
    - degraded: some services are up, some are down
    - unhealthy: all services are down
    """
    statuses = list(services.values())
    up_count = statuses.count("up")
    if up_count == len(statuses):
        return "healthy"
    elif up_count == 0:
        return "unhealthy"
    else:
        return "degraded"


@router.get("")
async def health_check(request: Request):
    """Full health check — liveness + dependency check.

    Checks PostgreSQL, Redis, and MinIO connectivity and returns
    aggregate status with individual service statuses and a timestamp.
    """
    postgres_status = await _check_postgres(request)
    redis_status = await _check_redis(request)
    minio_status = _check_minio(request)

    services = {
        "postgres": postgres_status,
        "redis": redis_status,
        "minio": minio_status,
    }

    return {
        "status": _compute_aggregate_status(services),
        "services": services,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness_check(request: Request):
    """Readiness probe — checks DB + Redis (critical for request handling).

    Returns ready if both PostgreSQL and Redis are connected,
    not_ready otherwise.
    """
    postgres_status = await _check_postgres(request)
    redis_status = await _check_redis(request)

    services = {
        "postgres": postgres_status,
        "redis": redis_status,
    }

    is_ready = postgres_status == "up" and redis_status == "up"

    return {
        "status": "ready" if is_ready else "not_ready",
        "services": services,
    }
