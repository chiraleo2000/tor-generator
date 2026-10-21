"""Infrastructure snapshot from health checks, rate limits, and the LLM queue."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request

from app.api.v1.endpoints.health import (
    _check_minio,
    _check_mongo,
    _check_neo4j,
    _check_postgres,
    _check_redis,
    _compute_aggregate_status,
)
from app.config import get_settings
from app.usage.anomaly import percentile

logger = logging.getLogger(__name__)

_ADMISSION_QUEUES = ("llm", "shared", "embedding")


def _decode(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


async def _scan_keys(redis: Any, pattern: str) -> list[Any]:
    keys: list[Any] = []
    scanner = getattr(redis, "scan_iter", None)
    if scanner is None:
        return keys
    async for key in scanner(match=pattern):
        keys.append(key)
    return keys


async def ai_rate_snapshot(redis: Any) -> dict[str, Any]:
    limit = int(getattr(get_settings(), "rate_limit_ai_per_minute", 30) or 30)
    if redis is None:
        return {
            "limit_per_minute": limit,
            "redis": "down",
            "active_keys": 0,
            "highest_count": 0,
        }
    active = 0
    highest = 0
    try:
        for key in await _scan_keys(redis, "rate:*:ai:*"):
            active += 1
            raw = await redis.get(key)
            try:
                highest = max(highest, int(raw or 0))
            except (TypeError, ValueError):
                continue
    except Exception:
        logger.exception("ai rate snapshot failed")
        return {
            "limit_per_minute": limit,
            "redis": "down",
            "active_keys": active,
            "highest_count": highest,
        }
    return {
        "limit_per_minute": limit,
        "redis": "up",
        "active_keys": active,
        "highest_count": highest,
    }


async def collect_waiting_ms(redis: Any) -> list[int]:
    if redis is None:
        return []
    waits: list[int] = []
    try:
        for key in await _scan_keys(redis, "llm:admit:req:*"):
            data = await redis.hgetall(key)
            if not data:
                continue
            decoded = {_decode(name): _decode(value) for name, value in data.items()}
            if decoded.get("status") != "waiting":
                continue
            try:
                waits.append(int(decoded.get("waiting_ms") or 0))
            except ValueError:
                continue
    except Exception:
        logger.exception("admission wait snapshot failed")
    return waits


async def admission_snapshot(redis: Any) -> dict[str, Any]:
    if redis is None:
        return {"waiting": None, "wait_p95_ms": None, "queues": []}
    queues: list[dict[str, Any]] = []
    llm_waiting = 0
    try:
        for name in _ADMISSION_QUEUES:
            waiting = int(await redis.llen(f"llm:admit:{name}:waiters") or 0)
            queues.append({"name": name, "waiting": waiting})
            if name != "embedding":
                llm_waiting += waiting
        waits = await collect_waiting_ms(redis)
    except Exception:
        logger.exception("admission snapshot failed")
        return {"waiting": None, "wait_p95_ms": None, "queues": queues}
    return {
        "waiting": llm_waiting,
        "wait_p95_ms": percentile(waits, 95),
        "queues": queues,
    }


async def dependency_status(request: Request) -> dict[str, str]:
    return {
        "postgres": await _check_postgres(request),
        "redis": await _check_redis(request),
        "minio": _check_minio(request),
        "mongo": _check_mongo(request),
        "neo4j": await _check_neo4j(request),
    }


async def infra_snapshot(request: Request) -> dict[str, Any]:
    services = await dependency_status(request)
    redis = getattr(request.app.state, "redis", None)
    return {
        "status": _compute_aggregate_status(services),
        "services": services,
        "rate_limit": await ai_rate_snapshot(redis),
        "admission": await admission_snapshot(redis),
    }


async def probe_process_services() -> dict[str, str]:
    """Best-effort status for the sweep, which has no HTTP request."""
    from app import infra

    services = {
        "postgres": "down",
        "redis": "down",
        "minio": "down",
        "mongo": "down",
        "neo4j": "down",
    }
    if infra.session_factory is not None:
        services["postgres"] = "up"
    if infra.redis_client is not None:
        try:
            pong = await infra.redis_client.ping()
            services["redis"] = "up" if pong else "down"
        except Exception:
            services["redis"] = "down"
    if infra.minio_client is not None:
        services["minio"] = "up"
    if infra.mongo_client is not None:
        try:
            infra.mongo_client.admin.command("ping")
            services["mongo"] = "up"
        except Exception:
            services["mongo"] = "down"
    if infra.neo4j_driver is not None:
        try:
            await infra.neo4j_driver.verify_connectivity()
            services["neo4j"] = "up"
        except Exception:
            services["neo4j"] = "down"
    return services
