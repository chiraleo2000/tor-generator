"""Qdrant provider search/delete with a mocked client."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if "qdrant_client" not in sys.modules:
    qdrant_mock = MagicMock()
    sys.modules["qdrant_client"] = qdrant_mock
    sys.modules["qdrant_client.models"] = qdrant_mock.models

import app.providers.vector_store.qdrant_provider as qdrant_mod


@pytest.mark.asyncio
async def test_qdrant_search_and_delete():
    client = AsyncMock()
    collection = MagicMock()
    collection.name = "tor_kb"
    collections = MagicMock()
    collections.collections = [collection]
    client.get_collections = AsyncMock(return_value=collections)

    point = MagicMock()
    point.id = "chunk-1"
    point.score = 0.91
    point.payload = {"chunk_text": "หลักเกณฑ์การจัดซื้อจัดจ้าง", "source": "kb"}
    client.search = AsyncMock(return_value=[point])
    client.upsert = AsyncMock()
    client.delete = AsyncMock()

    with patch.object(qdrant_mod, "AsyncQdrantClient", return_value=client):
        provider = qdrant_mod.QdrantProvider()
        hits = await provider.search([0.1] * 768, top_k=2, filter={"source": "kb"})
        assert hits[0].text == "หลักเกณฑ์การจัดซื้อจัดจ้าง"
        assert hits[0].score == pytest.approx(0.91)

        await provider.upsert("chunk-1", [0.2] * 768, {"chunk_text": "อัปเดต"})
        client.upsert.assert_awaited()

        await provider.delete("chunk-1")
        client.delete.assert_awaited()


@pytest.mark.asyncio
async def test_qdrant_creates_collection_once_and_searches_without_filter():
    client = AsyncMock()
    collections = MagicMock()
    collections.collections = []
    client.get_collections = AsyncMock(return_value=collections)
    client.create_collection = AsyncMock()
    client.search = AsyncMock(return_value=[])

    with patch.object(qdrant_mod, "AsyncQdrantClient", return_value=client):
        provider = qdrant_mod.QdrantProvider()
        await provider.search([0.1] * 768)
        await provider.search([0.2] * 768)
        client.create_collection.assert_awaited_once()
        assert client.search.await_count == 2
