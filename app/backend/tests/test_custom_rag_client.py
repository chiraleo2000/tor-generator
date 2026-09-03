"""Tests for Custom RAG HTTP client mapping."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.custom_rag_client import CustomRagClient


@pytest.mark.asyncio
async def test_custom_rag_maps_chunks() -> None:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "chunks": [
            {
                "text": "ข้อความจากภายนอก",
                "score": 0.91,
                "source_document": "เอกสารภายนอก",
                "metadata": {"section": "1"},
            }
        ]
    }
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.rag.custom_rag_client.httpx.AsyncClient", return_value=mock_client):
        client = CustomRagClient(base_url="http://rag.test", api_key="secret", top_k=3)
        chunks = await client.retrieve("สอบถาม", user_id="u1", search_scope="both")

    assert len(chunks) == 1
    assert chunks[0].text == "ข้อความจากภายนอก"
    assert chunks[0].source_document == "เอกสารภายนอก"
    assert chunks[0].metadata.get("rag_source") == "custom_rag"
    mock_client.post.assert_awaited()


@pytest.mark.asyncio
async def test_custom_rag_empty_chunks() -> None:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"chunks": []}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.rag.custom_rag_client.httpx.AsyncClient", return_value=mock_client):
        client = CustomRagClient(base_url="http://rag.test/")
        assert await client.retrieve("x") == []


def test_resolve_custom_rag_url_keeps_pageindex_search() -> None:
    from app.rag.custom_rag_client import resolve_custom_rag_url

    assert (
        resolve_custom_rag_url("http://pageindex:8000/api/search")
        == "http://pageindex:8000/api/search"
    )
    assert (
        resolve_custom_rag_url("http://rag.test") == "http://rag.test/v1/retrieve"
    )
    assert (
        resolve_custom_rag_url("http://rag.test", "/api/search")
        == "http://rag.test/api/search"
    )


@pytest.mark.asyncio
async def test_custom_rag_maps_results_list() -> None:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "results": [{"content": "จาก PageIndex", "score": 0.4, "title": "ก"}]
    }
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.rag.custom_rag_client.httpx.AsyncClient", return_value=mock_client):
        client = CustomRagClient(base_url="http://pageindex:8000/api/search")
        chunks = await client.retrieve("สอบถาม")

    assert chunks[0].text == "จาก PageIndex"
    assert chunks[0].source_document == "ก"
    assert mock_client.post.await_args.args[0] == "http://pageindex:8000/api/search"
