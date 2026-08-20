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
    max_slots = (
        int(settings.llm_max_concurrent)
        if kind == "llm"
        else int(settings.embedding_max_concurrent)
    )
    timeout = float(settings.llm_queue_wait_timeout_seconds)
    started = time.monotonic()
    acquired = False

    await redis.rpush(waiters_key, rid)
    await _set_request(redis, rid, kind=kind, status=_STATUS_WAITING, position=1)

    try:
        while True:
            elapsed = time.monotonic() - started
            if elapsed > timeout:
                await _set_request(
                    redis,
                    rid,
                    kind=kind,
                    status=_STATUS_TIMEOUT,
                    waiting_ms=int(elapsed * 1000),
                    error="หมดเวลารอคิว AI",
                )
                raise AdmissionTimeoutError(
                    "หมดเวลารอคิว AI กรุณาลองใหม่เมื่อระบบว่างขึ้น"
                )

            waiters = await redis.lrange(waiters_key, 0, -1)
            waiters_str = [
                w.decode() if isinstance(w, bytes) else str(w) for w in waiters
            ]
            try:
                position = waiters_str.index(rid) + 1
            except ValueError:
                position = 1

            waiting_ms = int(elapsed * 1000)
            await _set_request(
                redis,
                rid,
                kind=kind,
                status=_STATUS_WAITING,
                position=position,
                waiting_ms=waiting_ms,
            )
            if on_wait is not None:
                maybe = on_wait(position, waiting_ms)
                if maybe is not None:
                    await maybe

            if waiters_str and waiters_str[0] == rid:
                slots = int(await redis.get(slots_key) or 0)
                if slots < max_slots:
                    await redis.incr(slots_key)
                    await redis.lrem(waiters_key, 1, rid)
                    acquired = True
                    await _set_request(
                        redis,
                        rid,
                        kind=kind,
                        status=_STATUS_RUNNING,
                        position=0,
                        waiting_ms=waiting_ms,
                    )
                    break

            await asyncio.sleep(0.25)

        yield rid
    finally:
        if acquired:
            try:
                await redis.decr(slots_key)
                current = int(await redis.get(slots_key) or 0)
                if current < 0:
                    await redis.set(slots_key, 0)
            except Exception:
                logger.exception("Failed to release admission slot")
            await _set_request(
                redis,
                rid,
                kind=kind,
                status=_STATUS_DONE,
                position=0,
                waiting_ms=int((time.monotonic() - started) * 1000),
            )
        else:
            try:
                await redis.lrem(waiters_key, 1, rid)
            except Exception:
                logger.exception("Failed to remove waiter from admission queue")
