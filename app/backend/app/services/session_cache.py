"""Redis-backed cache for agent extraction, slot maps, drafts, and session state."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any
from uuid import UUID

from app.config import get_settings
from app.infra import redis_client as infra_redis

logger = logging.getLogger("tor_app.session_cache")

MIN_TTL_HOURS = 1
MAX_TTL_HOURS = 168


def content_hash(data: bytes) -> str:
    """SHA-256 of file bytes. Filename is not part of the digest."""
    return hashlib.sha256(data).hexdigest()


def clamp_ttl_seconds(hours: int) -> int:
    return max(MIN_TTL_HOURS, min(MAX_TTL_HOURS, int(hours))) * 3600


def extraction_key(project_id: UUID | str, digest: str) -> str:
    return f"agent:extract:{project_id}:{digest}"


def slotmap_key(project_id: UUID | str) -> str:
    return f"agent:slotmap:{project_id}"


def draft_key(project_id: UUID | str, section_key: str) -> str:
    return f"agent:draft:{project_id}:{section_key}"


def session_key(session_id: UUID | str) -> str:
    return f"agent:session:{session_id}"


def kb_session_key(session_id: UUID | str) -> str:
    return f"kb:session:{session_id}"


class SessionCacheService:
    """Cache agent intermediates in Redis. Writes never block the workflow."""

    def __init__(self, redis: Any | None = None) -> None:
        self._redis = redis if redis is not None else infra_redis

    def _client(self) -> Any | None:
        return self._redis if self._redis is not None else infra_redis

    def _ttl(self, hours: int) -> int:
        settings = get_settings()
        return settings.cache_ttl_seconds(hours)

    async def _get_json(self, key: str) -> Any | None:
        client = self._client()
        if client is None:
            return None
        try:
            raw = await client.get(key)
        except Exception as exc:
            logger.warning("Cache read failed for %s: %s", key, exc)
            return None
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return raw

    async def _set_json(self, key: str, value: Any, ttl: int) -> None:
        client = self._client()
        if client is None:
            return
        try:
            payload = json.dumps(value, ensure_ascii=False, default=str)
            await client.set(key, payload, ex=ttl)
        except Exception as exc:
            logger.warning("Cache write failed for %s: %s", key, exc)

    async def _delete_keys(self, *keys: str) -> None:
        client = self._client()
        if client is None or not keys:
            return
        try:
            await client.delete(*keys)
        except Exception as exc:
            logger.warning("Cache delete failed: %s", exc)

    async def get_extraction(self, project_id: UUID | str, digest: str) -> Any | None:
        return await self._get_json(extraction_key(project_id, digest))

    async def set_extraction(self, project_id: UUID | str, digest: str, value: Any) -> None:
        hours = get_settings().agent_cache_extraction_ttl_hours
        await self._set_json(extraction_key(project_id, digest), value, self._ttl(hours))

    async def get_slot_map(self, project_id: UUID | str) -> Any | None:
        return await self._get_json(slotmap_key(project_id))

    async def set_slot_map(self, project_id: UUID | str, value: Any) -> None:
        hours = get_settings().agent_cache_mapping_ttl_hours
        await self._set_json(slotmap_key(project_id), value, self._ttl(hours))

    async def get_draft(self, project_id: UUID | str, section_key: str) -> Any | None:
        return await self._get_json(draft_key(project_id, section_key))

    async def set_draft(self, project_id: UUID | str, section_key: str, value: Any) -> None:
        hours = get_settings().agent_cache_draft_ttl_hours
        await self._set_json(draft_key(project_id, section_key), value, self._ttl(hours))

    async def get_session_state(self, session_id: UUID | str) -> Any | None:
        return await self._get_json(session_key(session_id))

    async def set_session_state(self, session_id: UUID | str, value: Any) -> None:
        hours = get_settings().agent_cache_mapping_ttl_hours
        await self._set_json(session_key(session_id), value, self._ttl(hours))

    async def get_kb_history(self, session_id: UUID | str) -> Any | None:
        return await self._get_json(kb_session_key(session_id))

    async def set_kb_history(self, session_id: UUID | str, value: Any) -> None:
        await self._set_json(kb_session_key(session_id), value, 30 * 60)

    async def invalidate_project(self, project_id: UUID | str) -> None:
        await self._delete_keys(slotmap_key(project_id))
