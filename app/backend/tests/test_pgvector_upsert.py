"""PgVector upsert must bind the JSONB attribute, not Table.metadata."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.providers.vector_store.pgvector_provider import PgVectorProvider


class _SessionCM:
    def __init__(self) -> None:
        self.execute = AsyncMock()
        self.commit = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


@pytest.mark.asyncio
async def test_upsert_uses_chunk_metadata_attribute():
    session = _SessionCM()

    def factory():
        return session

    provider = PgVectorProvider(session_factory=factory)
    await provider.upsert(
        id=str(uuid.uuid4()),
        vector=[0.1] * 768,
        metadata={
            "chunk_text": "วิธีเฉพาะเจาะจง",
            "document_id": str(uuid.uuid4()),
            "chunk_index": 0,
            "source": "test",
        },
    )
    session.execute.assert_awaited()
    stmt = session.execute.await_args.args[0]
    compiled = str(stmt.compile(compile_kwargs={"literal_binds": False}))
    assert "kb_chunks" in compiled.lower()
    assert "on conflict" in compiled.lower()


@pytest.mark.asyncio
async def test_search_converts_distance_to_similarity():
    session = _SessionCM()
    row = MagicMock()
    row.id = uuid.uuid4()
    row.chunk_text = "วิธีเฉพาะเจาะจง"
    row.chunk_metadata = {"source": "test"}
    row.distance = 0.25
    result = MagicMock()
    result.all.return_value = [row]
    session.execute = AsyncMock(return_value=result)

    provider = PgVectorProvider(session_factory=lambda: session)
    hits = await provider.search([0.1] * 768, top_k=3, filter={"source": "test"})
    assert len(hits) == 1
    assert hits[0].text == "วิธีเฉพาะเจาะจง"
    assert hits[0].score == pytest.approx(0.75)
    session.execute.assert_awaited()


@pytest.mark.asyncio
async def test_delete_executes_and_commits():
    session = _SessionCM()
    provider = PgVectorProvider(session_factory=lambda: session)
    chunk_id = str(uuid.uuid4())
    await provider.delete(chunk_id)
    session.execute.assert_awaited()
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_upsert_optional_fields_and_search_null_distance():
    session = _SessionCM()
    provider = PgVectorProvider(session_factory=lambda: session)
    await provider.upsert(
        id=str(uuid.uuid4()),
        vector=[0.2] * 768,
        metadata={
            "chunk_text": "หน้าหนึ่ง",
            "section_label": "s1",
            "page_number": 3,
        },
    )
    session.execute.assert_awaited()

    row = MagicMock()
    row.id = uuid.uuid4()
    row.chunk_text = "ว่าง"
    row.chunk_metadata = None
    row.distance = None
    result = MagicMock()
    result.all.return_value = [row]
    session.execute = AsyncMock(return_value=result)
    hits = await provider.search([0.0] * 768)
    assert hits[0].score == pytest.approx(0.0)
    assert hits[0].metadata == {}
