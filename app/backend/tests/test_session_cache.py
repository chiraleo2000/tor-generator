"""Session cache graceful failure and key helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.session_cache import (
    SessionCacheService,
    content_hash,
    extraction_key,
    kb_session_key,
    session_key,
)


@pytest.mark.asyncio
async def test_write_failure_does_not_raise():
    redis = MagicMock()
    redis.set = AsyncMock(side_effect=RuntimeError("down"))
    cache = SessionCacheService(redis=redis)
    await cache.set_slot_map("p1", {"s1": {}})


@pytest.mark.asyncio
async def test_get_returns_none_when_redis_missing():
    cache = SessionCacheService(redis=None)
    assert await cache.get_slot_map("p1") is None


@pytest.mark.asyncio
async def test_round_trip_json():
    stored = {}

    async def setter(key, value, ex=None):
        stored[key] = value

    async def getter(key):
        return stored.get(key)

    redis = MagicMock()
    redis.set = AsyncMock(side_effect=setter)
    redis.get = AsyncMock(side_effect=getter)
    cache = SessionCacheService(redis=redis)
    await cache.set_extraction("proj", "abc", {"text": "hello"})
    value = await cache.get_extraction("proj", "abc")
    assert value["text"] == "hello"


def test_content_hash_same_bytes():
    payload = b"abc"
    digest = content_hash(payload)
    assert digest == content_hash(bytes(payload))
    assert "agent:extract:" in extraction_key("p", "hash")


def test_cache_keys_are_namespaced():
    assert session_key("abc") != kb_session_key("abc")
    assert session_key("abc").startswith("agent:session:")
    assert kb_session_key("abc").startswith("kb:session:")
