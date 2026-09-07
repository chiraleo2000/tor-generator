"""Redis-backed LLM / embedding admission queue (fair FIFO + slot limit)."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Literal

from redis.asyncio import Redis

from app.config import get_settings
from app.providers.constants import LOCAL_LLM_PROVIDERS

logger = logging.getLogger(__name__)

Kind = Literal["llm", "embedding"]
WaitCallback = Callable[[int, int], Awaitable[None] | None]

_STATUS_WAITING = "waiting"
_STATUS_RUNNING = "running"
_STATUS_DONE = "done"
_STATUS_TIMEOUT = "timeout"
_STATUS_ERROR = "error"


def _keys(kind: Kind, request_id: str) -> tuple[str, str, str]:
    return (
        f"llm:admit:{kind}:waiters",
        f"llm:admit:{kind}:slots",
        f"llm:admit:req:{request_id}",
    )


async def _set_request(
    redis: Redis,
    request_id: str,
    *,
    kind: Kind,
    status: str,
    position: int = 0,
    waiting_ms: int = 0,
    error: str = "",
) -> None:
    key = f"llm:admit:req:{request_id}"
    mapping: dict[str, Any] = {
        "kind": kind,
        "status": status,
        "position": str(position),
        "waiting_ms": str(waiting_ms),
        "error": error,
        "updated_at": str(time.time()),
    }
    await redis.hset(key, mapping=mapping)
    await redis.expire(key, 600)


async def get_queue_status(redis: Redis | None, request_id: str) -> dict[str, Any]:
    if redis is None or not request_id:
        return {"status": "unknown", "position": 0, "waiting_ms": 0}
    data = await redis.hgetall(f"llm:admit:req:{request_id}")
    if not data:
        return {"status": "unknown", "position": 0, "waiting_ms": 0}
    decoded = {
        (k.decode() if isinstance(k, bytes) else k): (
            v.decode() if isinstance(v, bytes) else v
        )
        for k, v in data.items()
    }
    return {
        "request_id": request_id,
        "kind": decoded.get("kind", "llm"),
        "status": decoded.get("status", "unknown"),
        "position": int(decoded.get("position") or 0),
        "waiting_ms": int(decoded.get("waiting_ms") or 0),
        "error": decoded.get("error") or "",
    }


class AdmissionTimeoutError(TimeoutError):
    """Raised when waiting for an LLM/embedding slot exceeds the timeout."""


def _decode_waiters(waiters: list[Any]) -> list[str]:
    return [w.decode() if isinstance(w, bytes) else str(w) for w in waiters]


def _position_of(waiters_str: list[str], rid: str) -> int:
    try:
        return waiters_str.index(rid) + 1
    except ValueError:
        return 1


async def _notify_wait(
    on_wait: WaitCallback | None, position: int, waiting_ms: int
) -> None:
    if on_wait is None:
        return
    maybe = on_wait(position, waiting_ms)
    if maybe is not None:
        await maybe


def concurrency_cap(kind: Kind, settings: Any) -> int:
    """Local Gemma crashes if several chat jobs share the GPU; keep one LLM slot."""
    if kind != "llm":
        return max(1, int(settings.embedding_max_concurrent))
    cap = max(1, int(settings.llm_max_concurrent))
    provider = getattr(settings, "llm_provider", "") or ""
    if provider in LOCAL_LLM_PROVIDERS:
        return 1
    return cap


def slot_ttl_seconds(kind: Kind, settings: Any) -> int:
    try:
        wait = int(float(settings.llm_queue_wait_timeout_seconds or 120))
    except (TypeError, ValueError):
        wait = 120
    if kind == "embedding":
        return max(300, wait + 120)
    try:
        local_to = int(getattr(settings, "lm_studio_timeout", 1800) or 1800)
    except (TypeError, ValueError):
        local_to = 1800
    return max(600, wait + local_to)


async def reset_admission_queues(redis: Redis | None) -> None:
    """Drop leaked slot counters after a model crash or backend restart."""
    if redis is None:
        return
    for kind in ("llm", "embedding"):
        waiters_key, slots_key, _ = _keys(kind, "startup")
        try:
            await redis.delete(waiters_key, slots_key)
        except Exception:
            logger.exception("Failed to reset %s admission queue", kind)


async def _try_acquire_slot(
    redis: Redis,
    *,
    kind: Kind,
    rid: str,
    waiters_key: str,
    slots_key: str,
    waiters_str: list[str],
    max_slots: int,
    waiting_ms: int,
    slot_ttl: int,
) -> bool:
    if not waiters_str or waiters_str[0] != rid:
        return False
    slots = int(await redis.get(slots_key) or 0)
    if slots < 0:
        await redis.set(slots_key, 0)
        slots = 0
    if slots >= max_slots:
        return False
    await redis.incr(slots_key)
    if slot_ttl > 0:
        await redis.expire(slots_key, slot_ttl)
    await redis.lrem(waiters_key, 1, rid)
    await _set_request(
        redis,
        rid,
        kind=kind,
        status=_STATUS_RUNNING,
        position=0,
        waiting_ms=waiting_ms,
    )
    return True


async def _release_slot(redis: Redis, slots_key: str) -> None:
    try:
        await redis.decr(slots_key)
        current = int(await redis.get(slots_key) or 0)
        if current < 0:
            await redis.set(slots_key, 0)
    except Exception:
        logger.exception("Failed to release admission slot")


async def _remove_waiter(redis: Redis, waiters_key: str, rid: str) -> None:
    try:
        await redis.lrem(waiters_key, 1, rid)
    except Exception:
        logger.exception("Failed to remove waiter from admission queue")


async def _wait_for_slot(
    redis: Redis,
    *,
    kind: Kind,
    rid: str,
    waiters_key: str,
    slots_key: str,
    max_slots: int,
    wait_seconds: float,
    started: float,
    on_wait: WaitCallback | None,
    slot_ttl: int,
) -> None:
    try:
        async with asyncio.timeout(wait_seconds):
            while True:
                elapsed = time.monotonic() - started
                waiters_str = _decode_waiters(await redis.lrange(waiters_key, 0, -1))
                position = _position_of(waiters_str, rid)
                waiting_ms = int(elapsed * 1000)
                await _set_request(
                    redis,
                    rid,
                    kind=kind,
                    status=_STATUS_WAITING,
                    position=position,
                    waiting_ms=waiting_ms,
                )
                await _notify_wait(on_wait, position, waiting_ms)
                if await _try_acquire_slot(
                    redis,
                    kind=kind,
                    rid=rid,
                    waiters_key=waiters_key,
                    slots_key=slots_key,
                    waiters_str=waiters_str,
                    max_slots=max_slots,
                    waiting_ms=waiting_ms,
                    slot_ttl=slot_ttl,
                ):
                    return
                await asyncio.sleep(0.25)
    except TimeoutError as exc:
        if isinstance(exc, AdmissionTimeoutError):
            raise
        waiting_ms = int((time.monotonic() - started) * 1000)
        await _set_request(
            redis,
            rid,
            kind=kind,
            status=_STATUS_TIMEOUT,
            waiting_ms=waiting_ms,
            error="หมดเวลารอคิว AI",
        )
        raise AdmissionTimeoutError(
            "หมดเวลารอคิว AI กรุณาลองใหม่เมื่อระบบว่างขึ้น"
        ) from exc


@asynccontextmanager
async def admit(
    redis: Redis | None,
    kind: Kind,
    request_id: str | None = None,
    on_wait: WaitCallback | None = None,
) -> AsyncIterator[str]:
    """Acquire a concurrency slot; update Redis wait status while queued.

    Fail-closed when Redis is unavailable (cannot protect the backend).
    Optional on_wait(position, waiting_ms) is awaited each poll while queued.
    """
    settings = get_settings()
    rid = (request_id or str(uuid.uuid4())).strip()
    if redis is None:
        # Degraded: no shared queue (unit tests / Redis down). Prefer fail-open so
        # chat/draft still work; production compose always wires Redis.
        logger.warning("LLM admission skipped: Redis unavailable")
        yield rid
        return

    waiters_key, slots_key, _ = _keys(kind, rid)
    max_slots = concurrency_cap(kind, settings)
    wait_seconds = float(settings.llm_queue_wait_timeout_seconds)
    started = time.monotonic()
    acquired = False

    await redis.rpush(waiters_key, rid)
    await _set_request(redis, rid, kind=kind, status=_STATUS_WAITING, position=1)

    try:
        await _wait_for_slot(
            redis,
            kind=kind,
            rid=rid,
            waiters_key=waiters_key,
            slots_key=slots_key,
            max_slots=max_slots,
            wait_seconds=wait_seconds,
            started=started,
            on_wait=on_wait,
            slot_ttl=slot_ttl_seconds(kind, settings),
        )
        acquired = True
        yield rid
    finally:
        if acquired:
            await _release_slot(redis, slots_key)
            await _set_request(
                redis,
                rid,
                kind=kind,
                status=_STATUS_DONE,
                position=0,
                waiting_ms=int((time.monotonic() - started) * 1000),
            )
        else:
            await _remove_waiter(redis, waiters_key, rid)
