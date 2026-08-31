"""Redis-backed draft job status store (fail-open when Redis is down).

Mirrors ``llm_admission``: ``hset(mapping=...)`` + ``expire(key, 600)``.
In-memory fallback lets a single backend instance keep drafting when Redis
is unavailable.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

TTL_SECONDS = 600
STALE_RUNNING_SECONDS = 600
KEY_PREFIX = "draft:job:"
STATUSES = ("queued", "running", "done", "failed")

_memory: dict[str, dict[str, Any]] = {}


def _key(project_id: UUID | str) -> str:
    return f"{KEY_PREFIX}{project_id}"


def _now() -> float:
    return time.time()


def _normalize(record: dict[str, Any]) -> dict[str, Any]:
    status = str(record.get("status") or "failed")
    drafted_count = int(record.get("drafted_count") or 0)
    total = int(record.get("total") or 0)
    updated_at = float(record.get("updated_at") or 0)
    if status == "running" and updated_at and (_now() - updated_at) > STALE_RUNNING_SECONDS:
        status = "failed"
    return {
        "status": status,
        "drafted_count": drafted_count,
        "total": total,
        "updated_at": updated_at,
    }


def _remember(project_id: UUID | str, record: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize(record)
    _memory[str(project_id)] = dict(normalized)
    return normalized


def clear_memory() -> None:
    """Test helper: drop in-process fallback records."""
    _memory.clear()


def memory_snapshot(project_id: UUID | str) -> dict[str, Any] | None:
    raw = _memory.get(str(project_id))
    return _normalize(raw) if raw else None


async def set_job(
    redis: Redis | None,
    project_id: UUID | str,
    status: str,
    drafted_count: int,
    total: int,
) -> dict[str, Any]:
    """Write a full job record. Fail-open to in-memory when Redis is down."""
    if status not in STATUSES:
        status = "failed"
    record = {
        "status": status,
        "drafted_count": max(0, int(drafted_count)),
        "total": max(0, int(total)),
        "updated_at": _now(),
    }
    stored = _remember(project_id, record)
    if redis is None:
        return stored
    key = _key(project_id)
    mapping = {
        "status": stored["status"],
        "drafted_count": str(stored["drafted_count"]),
        "total": str(stored["total"]),
        "updated_at": str(stored["updated_at"]),
    }
    try:
        await redis.hset(key, mapping=mapping)
        await redis.expire(key, TTL_SECONDS)
    except (RedisError, OSError):
        logger.warning("Draft job store write failed; using in-memory fallback", exc_info=True)
    return stored


async def bump_progress(
    redis: Redis | None,
    project_id: UUID | str,
    drafted_count: int,
) -> dict[str, Any] | None:
    current = await get_job(redis, project_id, apply_stale=False)
    if current is None:
        return await set_job(redis, project_id, "running", drafted_count, drafted_count)
    return await set_job(
        redis,
        project_id,
        current["status"] if current["status"] in STATUSES else "running",
        drafted_count,
        current["total"],
    )


async def mark_status(
    redis: Redis | None,
    project_id: UUID | str,
    status: str,
) -> dict[str, Any] | None:
    current = await get_job(redis, project_id, apply_stale=False)
    if current is None:
        return await set_job(redis, project_id, status, 0, 0)
    return await set_job(
        redis, project_id, status, current["drafted_count"], current["total"]
    )


def _decode_redis_hash(data: dict) -> dict[str, Any]:
    return {
        (k.decode() if isinstance(k, bytes) else k): (
            v.decode() if isinstance(v, bytes) else v
        )
        for k, v in data.items()
    }


async def _read_job_from_redis(
    redis: Redis, project_id: UUID | str
) -> dict[str, Any] | None:
    try:
        data = await redis.hgetall(_key(project_id))
    except (RedisError, OSError):
        logger.warning("Draft job store read failed; using in-memory fallback", exc_info=True)
        return None
    return _decode_redis_hash(data) if data else None


def _job_record_without_stale(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": str(raw.get("status") or "failed"),
        "drafted_count": int(raw.get("drafted_count") or 0),
        "total": int(raw.get("total") or 0),
        "updated_at": float(raw.get("updated_at") or 0),
    }


async def get_job(
    redis: Redis | None,
    project_id: UUID | str,
    *,
    apply_stale: bool = True,
) -> dict[str, Any] | None:
    """Read the latest job record. Stale running (>600s) is reported as failed."""
    raw = await _read_job_from_redis(redis, project_id) if redis is not None else None
    if raw is None:
        raw = _memory.get(str(project_id))
    if not raw:
        return None
    if not apply_stale:
        return _job_record_without_stale(raw)
    return _normalize(raw)
