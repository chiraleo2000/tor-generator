"""LLM admission queue fail-open and timeout paths."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm_admission import (
    AdmissionTimeoutError,
    _set_request,
    admit,
    get_queue_status,
)


@pytest.mark.asyncio
async def test_get_queue_status_without_redis() -> None:
    assert await get_queue_status(None, "abc") == {
        "status": "unknown",
        "position": 0,
        "waiting_ms": 0,
    }


@pytest.mark.asyncio
async def test_get_queue_status_empty_hash() -> None:
    redis = MagicMock()
    redis.hgetall = AsyncMock(return_value={})
    payload = await get_queue_status(redis, "rid")
    assert payload["status"] == "unknown"


@pytest.mark.asyncio
async def test_get_queue_status_decodes_bytes() -> None:
    redis = MagicMock()
    redis.hgetall = AsyncMock(
        return_value={b"kind": b"llm", b"status": b"waiting", b"position": b"2", b"waiting_ms": b"10"}
    )
    payload = await get_queue_status(redis, "rid")
    assert payload["status"] == "waiting"
    assert payload["position"] == 2
    assert payload["kind"] == "llm"


@pytest.mark.asyncio
async def test_admit_fail_open_without_redis() -> None:
    async with admit(None, "llm", request_id="x") as rid:
        assert rid == "x"


@pytest.mark.asyncio
async def test_admit_acquires_slot() -> None:
    redis = MagicMock()
    redis.rpush = AsyncMock()
    redis.hset = AsyncMock()
    redis.expire = AsyncMock()
    redis.lrange = AsyncMock(return_value=[b"x"])
    redis.get = AsyncMock(side_effect=[0, 1, 0])
    redis.incr = AsyncMock()
    redis.lrem = AsyncMock()
    redis.decr = AsyncMock()
    redis.set = AsyncMock()
    with patch("app.llm_admission.get_settings") as settings:
        settings.return_value = MagicMock(
            llm_max_concurrent=2,
            embedding_max_concurrent=2,
            llm_queue_wait_timeout_seconds=5,
        )
        async with admit(redis, "llm", request_id="x"):
            pass
    redis.incr.assert_awaited()
    redis.decr.assert_awaited()


@pytest.mark.asyncio
async def test_admit_timeout() -> None:
    redis = MagicMock()
    redis.rpush = AsyncMock()
    redis.hset = AsyncMock()
    redis.expire = AsyncMock()
    redis.lrange = AsyncMock(return_value=[b"other", b"x"])
    redis.lrem = AsyncMock()
    with (
        patch("app.llm_admission.get_settings") as settings,
        patch("app.llm_admission.asyncio.sleep", new_callable=AsyncMock),
        patch("app.llm_admission.time.monotonic", side_effect=[0.0, 10.0, 10.0]),
    ):
        settings.return_value = MagicMock(
            llm_max_concurrent=1,
            embedding_max_concurrent=1,
            llm_queue_wait_timeout_seconds=1,
        )
        with pytest.raises(AdmissionTimeoutError):
            async with admit(redis, "llm", request_id="x"):
                pass


@pytest.mark.asyncio
async def test_get_queue_status_empty_request_id() -> None:
    redis = MagicMock()
    payload = await get_queue_status(redis, "")
    assert payload["status"] == "unknown"


@pytest.mark.asyncio
async def test_admit_on_wait_and_negative_slots() -> None:
    redis = MagicMock()
    redis.rpush = AsyncMock()
    redis.hset = AsyncMock()
    redis.expire = AsyncMock()
    redis.lrange = AsyncMock(return_value=[b"x"])
    redis.get = AsyncMock(side_effect=[0, -1])
    redis.incr = AsyncMock()
    redis.lrem = AsyncMock()
    redis.decr = AsyncMock()
    redis.set = AsyncMock()
    waits: list[tuple[int, int]] = []

    async def on_wait(position: int, waiting_ms: int) -> None:
        waits.append((position, waiting_ms))

    with patch("app.llm_admission.get_settings") as settings:
        settings.return_value = MagicMock(
            llm_max_concurrent=2,
            embedding_max_concurrent=2,
            llm_queue_wait_timeout_seconds=5,
        )
        async with admit(redis, "embedding", request_id="x", on_wait=on_wait):
            pass
    assert waits
    redis.set.assert_awaited()


@pytest.mark.asyncio
async def test_admit_release_failure_is_logged() -> None:
    redis = MagicMock()
    redis.rpush = AsyncMock()
    redis.hset = AsyncMock()
    redis.expire = AsyncMock()
    redis.lrange = AsyncMock(return_value=["x"])
    redis.get = AsyncMock(return_value=0)
    redis.incr = AsyncMock()
    redis.lrem = AsyncMock()
    redis.decr = AsyncMock(side_effect=RuntimeError("redis down"))
    with patch("app.llm_admission.get_settings") as settings:
        settings.return_value = MagicMock(
            llm_max_concurrent=1,
            embedding_max_concurrent=1,
            llm_queue_wait_timeout_seconds=5,
        )
        async with admit(redis, "llm", request_id="x"):
            pass


@pytest.mark.asyncio
async def test_set_request_writes_hash_and_ttl() -> None:
    redis = MagicMock()
    redis.hset = AsyncMock()
    redis.expire = AsyncMock()
    await _set_request(
        redis, "rid-1", kind="llm", status="waiting", position=3, waiting_ms=12, error=""
    )
    mapping = redis.hset.await_args.kwargs["mapping"]
    assert mapping["kind"] == "llm"
    assert mapping["status"] == "waiting"
    assert mapping["position"] == "3"
    assert mapping["waiting_ms"] == "12"
    redis.expire.assert_awaited_with("llm:admit:req:rid-1", 600)


@pytest.mark.asyncio
async def test_get_queue_status_plain_strings() -> None:
    redis = MagicMock()
    redis.hgetall = AsyncMock(
        return_value={"kind": "embedding", "status": "running", "position": "0", "waiting_ms": ""}
    )
    payload = await get_queue_status(redis, "rid")
    assert payload["kind"] == "embedding"
    assert payload["status"] == "running"
    assert payload["position"] == 0
    assert payload["waiting_ms"] == 0


@pytest.mark.asyncio
async def test_admit_missing_waiter_times_out_and_lrem() -> None:
    redis = MagicMock()
    redis.rpush = AsyncMock()
    redis.hset = AsyncMock()
    redis.expire = AsyncMock()
    redis.lrange = AsyncMock(return_value=[b"other"])
    redis.lrem = AsyncMock()
    with (
        patch("app.llm_admission.get_settings") as settings,
        patch("app.llm_admission.asyncio.sleep", new_callable=AsyncMock),
        patch("app.llm_admission.time.monotonic", side_effect=[0.0, 0.0, 10.0, 10.0]),
    ):
        settings.return_value = MagicMock(
            llm_max_concurrent=1,
            embedding_max_concurrent=1,
            llm_queue_wait_timeout_seconds=1,
        )
        with pytest.raises(AdmissionTimeoutError):
            async with admit(redis, "llm", request_id="x"):
                pass
    redis.lrem.assert_awaited()


@pytest.mark.asyncio
async def test_admit_generates_request_id_and_sync_on_wait() -> None:
    redis = MagicMock()
    redis.rpush = AsyncMock()
    redis.hset = AsyncMock()
    redis.expire = AsyncMock()
    redis.lrange = AsyncMock(return_value=[b"generated"])
    redis.get = AsyncMock(return_value=0)
    redis.incr = AsyncMock()
    redis.lrem = AsyncMock()
    redis.decr = AsyncMock()
    redis.set = AsyncMock()
    waits: list[tuple[int, int]] = []

    def on_wait(position: int, waiting_ms: int) -> None:
        waits.append((position, waiting_ms))

    with (
        patch("app.llm_admission.get_settings") as settings,
        patch("app.llm_admission.uuid.uuid4", return_value="generated"),
    ):
        settings.return_value = MagicMock(
            llm_max_concurrent=2,
            embedding_max_concurrent=2,
            llm_queue_wait_timeout_seconds=5,
        )
        async with admit(redis, "llm", on_wait=on_wait) as rid:
            assert rid == "generated"
    assert waits
    redis.incr.assert_awaited()
