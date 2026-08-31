"""Unit tests for Redis Draft_Job_Store (Req 11)."""

from __future__ import annotations

import time
import uuid
from unittest.mock import AsyncMock

import pytest

from app.draft_job_store import (
    TTL_SECONDS,
    bump_progress,
    clear_memory,
    get_job,
    mark_status,
    set_job,
)


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, dict[str, str]] = {}
        self.ttls: dict[str, int] = {}

    async def hset(self, key, mapping=None, **_kwargs):
        self.data[key] = {str(k): str(v) for k, v in (mapping or {}).items()}

    async def expire(self, key, ttl):
        self.ttls[key] = int(ttl)

    async def hgetall(self, key):
        return dict(self.data.get(key) or {})


@pytest.fixture(autouse=True)
def _reset_store():
    clear_memory()
    yield
    clear_memory()


@pytest.mark.asyncio
async def test_set_and_get_round_trip():
    redis = FakeRedis()
    pid = uuid.uuid4()
    written = await set_job(redis, pid, "running", 3, 13)
    assert written["status"] == "running"
    assert redis.ttls[f"draft:job:{pid}"] == TTL_SECONDS
    read = await get_job(redis, pid)
    assert read["status"] == "running"
    assert read["drafted_count"] == 3
    assert read["total"] == 13


@pytest.mark.asyncio
async def test_stale_running_reports_failed():
    redis = FakeRedis()
    pid = uuid.uuid4()
    await set_job(redis, pid, "running", 4, 13)
    key = f"draft:job:{pid}"
    redis.data[key]["updated_at"] = str(time.time() - 601)
    read = await get_job(redis, pid)
    assert read["status"] == "failed"
    assert read["drafted_count"] == 4


@pytest.mark.asyncio
async def test_fail_open_when_redis_none():
    pid = uuid.uuid4()
    await set_job(None, pid, "queued", 0, 13)
    await bump_progress(None, pid, 2)
    await mark_status(None, pid, "done")
    read = await get_job(None, pid)
    assert read["status"] == "done"
    assert read["drafted_count"] == 2


@pytest.mark.asyncio
async def test_fail_open_when_redis_raises():
    redis = AsyncMock()
    redis.hset = AsyncMock(side_effect=ConnectionError("down"))
    redis.expire = AsyncMock(side_effect=ConnectionError("down"))
    redis.hgetall = AsyncMock(side_effect=ConnectionError("down"))
    pid = uuid.uuid4()
    await set_job(redis, pid, "running", 1, 13)
    read = await get_job(redis, pid)
    assert read["status"] == "running"
    assert read["drafted_count"] == 1
