"""Knowledge-base Q&A with access-controlled hybrid retrieval."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kb_chat_session import KBChatSession
from app.providers.factory import ProviderFactory
from app.rag.hybrid import hybrid_retrieve
from app.services.session_cache import SessionCacheService

logger = logging.getLogger("tor_app.kb_chat")

MAX_HISTORY = 20
MAX_MESSAGE_LENGTH = 1000
SESSION_TIMEOUT_MINUTES = 30
RELEVANCE_THRESHOLD = 0.5
NO_RESULTS = "ไม่พบข้อมูลที่เกี่ยวข้อง"


@dataclass
class ChatResponse:
    answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    no_results: bool = False
    history: list[dict[str, Any]] = field(default_factory=list)


def bound_history(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep at most 20 user/assistant pairs (40 messages), evicting oldest pairs."""
    items = list(history or [])
    max_messages = MAX_HISTORY * 2
    if len(items) <= max_messages:
        return items
    trimmed = items[-max_messages:]
    if trimmed and trimmed[0].get("role") == "assistant":
        trimmed = trimmed[1:]
    return trimmed


class KnowledgeChatService:
    def __init__(self, cache: SessionCacheService | None = None, llm: Any | None = None) -> None:
        self._cache = cache or SessionCacheService()
        self._llm = llm

    async def create_session(self, db: AsyncSession, user_id: UUID) -> KBChatSession:
        row = KBChatSession(id=uuid4(), user_id=user_id, history=[])
        db.add(row)
        await db.flush()
        return row

    async def load_session(
        self, db: AsyncSession, session_id: UUID, user_id: UUID
    ) -> KBChatSession | None:
        row = (
            await db.execute(select(KBChatSession).where(KBChatSession.id == session_id))
        ).scalar_one_or_none()
        if row is None or row.user_id != user_id:
            return None
        idle = datetime.now(timezone.utc) - _as_utc(row.last_active_at)
        if idle > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
            return None
        return row

    async def answer(
        self,
        session_id: UUID,
        user_id: UUID,
        message: str,
        history: list[dict] | None = None,
        db: AsyncSession | None = None,
    ) -> ChatResponse:
        text = (message or "").strip()
        if len(text) > MAX_MESSAGE_LENGTH:
            text = text[:MAX_MESSAGE_LENGTH]
        result, _, _degraded = await hybrid_retrieve(
            text,
            user_id=user_id,
            search_scope="both",
            top_k=5,
        )
        relevant = [
            chunk
            for chunk in (result.chunks or [])
            if float(getattr(chunk, "score", 0) or 0) >= RELEVANCE_THRESHOLD
        ]
        if not relevant:
            response = ChatResponse(answer=NO_RESULTS, citations=[], no_results=True)
            await self._append(session_id, user_id, text, response, history, db)
            return response
        answer = await self._synthesize(text, relevant, history or [])
        cited = []
        for chunk in relevant:
            cited.append(
                {
                    "document": getattr(chunk, "source_document", None)
                    or (chunk.metadata or {}).get("source_document"),
                    "page": getattr(chunk, "page_number", None),
                    "section": getattr(chunk, "section_label", None),
                }
            )
        response = ChatResponse(answer=answer, citations=cited, no_results=False)
        await self._append(session_id, user_id, text, response, history, db)
        return response

    async def _synthesize(self, message: str, chunks: list, history: list[dict]) -> str:
        llm = self._llm or ProviderFactory().get_llm()
        context = "\n\n".join(getattr(chunk, "text", "") for chunk in chunks[:5])
        prior = "\n".join(
            f"{item.get('role')}: {item.get('content')}"
            for item in history[-6:]
            if isinstance(item, dict)
        )
        response = await llm.invoke(
            [
                {
                    "role": "system",
                    "content": (
                        "ตอบจากเอกสารที่ให้เท่านั้น เป็นภาษาราชการ "
                        "อ้างชื่อเอกสารถ้ามี ห้ามแต่งข้อมูลที่ไม่มีในบริบท"
                    ),
                },
                {"role": "user", "content": f"{prior}\n\nคำถาม: {message}\n\nบริบท:\n{context}"},
            ],
            temperature=0.2,
            max_tokens=2048,
        )
        return getattr(response, "content", "") or ""

    async def _append(
        self,
        session_id: UUID,
        user_id: UUID,
        message: str,
        response: ChatResponse,
        history: list[dict] | None,
        db: AsyncSession | None,
    ) -> None:
        del user_id
        items = list(history or [])
        items.append({"role": "user", "content": message})
        items.append(
            {
                "role": "assistant",
                "content": response.answer,
                "citations": response.citations,
            }
        )
        items = bound_history(items)
        response.history = items
        await self._cache.set_kb_history(session_id, items)
        if db is None:
            return
        row = (
            await db.execute(select(KBChatSession).where(KBChatSession.id == session_id))
        ).scalar_one_or_none()
        if row is None:
            return
        row.history = items
        row.last_active_at = datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
