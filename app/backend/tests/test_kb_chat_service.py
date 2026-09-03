"""Knowledge-base chat service helpers with mocked retrieval."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.rag.retrieval import RetrievalResult, RetrievedChunk
from app.services.kb_chat_service import (
    NO_RESULTS,
    KnowledgeChatService,
    _chunks_for_answer,
    bound_history,
)


def test_bound_history_trims_oldest_pairs() -> None:
    items = [{"role": "user" if index % 2 == 0 else "assistant", "content": str(index)} for index in range(50)]
    trimmed = bound_history(items)
    assert len(trimmed) <= 40
    assert trimmed[0]["role"] == "user"


def test_chunks_for_answer_keeps_strong_or_fallback() -> None:
    strong = RetrievedChunk(id="1", text="ก", score=0.9)
    weak = RetrievedChunk(id="2", text="ข", score=0.01)
    assert _chunks_for_answer([strong, weak]) == [strong]
    assert _chunks_for_answer([weak]) == [weak]
    assert _chunks_for_answer([]) == []


@pytest.mark.asyncio
async def test_answer_no_results() -> None:
    cache = MagicMock()
    cache.set_kb_history = AsyncMock()
    service = KnowledgeChatService(cache=cache, llm=MagicMock())
    empty = RetrievalResult(chunks=[], query="q", top_k=1, actual_count=0)
    with patch(
        "app.services.kb_chat_service.hybrid_retrieve",
        new_callable=AsyncMock,
        return_value=(empty, [], False, True),
    ):
        response = await service.answer(uuid4(), uuid4(), "หลักประกัน")
    assert response.no_results is True
    assert response.answer == NO_RESULTS
    cache.set_kb_history.assert_awaited()


@pytest.mark.asyncio
async def test_answer_synthesizes_with_citations() -> None:
    llm = MagicMock()
    llm.invoke = AsyncMock(return_value=MagicMock(content="คำตอบ"))
    cache = MagicMock()
    cache.set_kb_history = AsyncMock()
    service = KnowledgeChatService(cache=cache, llm=llm)
    chunk = RetrievedChunk(id="1", text="ก", score=0.8, source_document="ด", page_number=2)
    result = RetrievalResult(chunks=[chunk], query="q", top_k=1, actual_count=1)
    with patch(
        "app.services.kb_chat_service.hybrid_retrieve",
        new_callable=AsyncMock,
        return_value=(result, [], False, False),
    ):
        response = await service.answer(uuid4(), uuid4(), "ถาม", history=[])
    assert response.answer == "คำตอบ"
    assert response.citations[0]["document"] == "ด"
    assert response.citations[0]["page"] == 2


@pytest.mark.asyncio
async def test_load_session_acl_and_timeout() -> None:
    service = KnowledgeChatService(cache=MagicMock())
    db = AsyncMock()
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=missing)
    assert await service.load_session(db, uuid4(), uuid4()) is None

    user_id = uuid4()
    row = MagicMock()
    row.user_id = user_id
    row.last_active_at = datetime.now(timezone.utc) - timedelta(hours=2)
    found = MagicMock()
    found.scalar_one_or_none.return_value = row
    db.execute = AsyncMock(return_value=found)
    assert await service.load_session(db, uuid4(), user_id) is None

    row.last_active_at = datetime.now(timezone.utc)
    assert await service.load_session(db, uuid4(), user_id) is row


@pytest.mark.asyncio
async def test_create_session_adds_row() -> None:
    service = KnowledgeChatService(cache=MagicMock())
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    row = await service.create_session(db, uuid4())
    db.add.assert_called_once()
    assert row.history == []


@pytest.mark.asyncio
async def test_append_updates_db_row() -> None:
    cache = MagicMock()
    cache.set_kb_history = AsyncMock()
    service = KnowledgeChatService(cache=cache, llm=MagicMock())
    db = AsyncMock()
    row = MagicMock()
    found = MagicMock()
    found.scalar_one_or_none.return_value = row
    db.execute = AsyncMock(return_value=found)
    empty = RetrievalResult(chunks=[], query="q", top_k=1, actual_count=0)
    with patch(
        "app.services.kb_chat_service.hybrid_retrieve",
        new_callable=AsyncMock,
        return_value=(empty, [], False, False),
    ):
        await service.answer(uuid4(), uuid4(), "ถาม", db=db)
    assert row.history
