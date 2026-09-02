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
    _, kwargs = mock_client.post.await_args
    assert kwargs["headers"]["Authorization"] == "Bearer secret"
    assert kwargs["headers"]["X-API-Key"] == "secret"


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


@pytest.mark.asyncio
async def test_pageindex_rag_maps_hits_from_full_search_url() -> None:
    response = MagicMock(status_code=200)
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "query": "หลักประกันสัญญา",
        "hits": [
            {
                "doc_id": "law-001",
                "doc_title": "ระเบียบจัดซื้อจัดจ้าง",
                "source_kind": "pdf",
                "source_origin": "manual_upload",
                "section_id": "5.2",
                "title": "หลักประกันสัญญา",
                "summary": "สรุปย่อ",
                "full_text": "ข้อความเต็มจาก PageIndex",
                "keywords": ["หลักประกัน"],
                "score": 4.0,
            }
        ],
    }
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.rag.custom_rag_client.httpx.AsyncClient", return_value=mock_client):
        client = CustomRagClient(
            base_url="http://knowledge-rag:8000/api/search",
            api_key="pageindex-secret",
        )
        chunks = await client.retrieve("หลักประกันสัญญา", top_k=7)

    assert len(chunks) == 1
    assert chunks[0].id == "law-001:5.2"
    assert chunks[0].text == "ข้อความเต็มจาก PageIndex"
    assert chunks[0].score == pytest.approx(0.8)
    assert chunks[0].source_document == "ระเบียบจัดซื้อจัดจ้าง"
    assert chunks[0].section_label == "หลักประกันสัญญา"
    assert chunks[0].metadata["rag_source"] == "pageindex_rag"
    mock_client.post.assert_awaited_once_with(
        "http://knowledge-rag:8000/api/search",
        json={
            "query": "หลักประกันสัญญา",
            "k": 7,
            "user_id": None,
            "search_scope": "both",
        },
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer pageindex-secret",
            "X-API-Key": "pageindex-secret",
        },
    )


@pytest.mark.asyncio
async def test_pageindex_rag_fallback_from_custom_contract() -> None:
    missing = MagicMock(status_code=404)
    pageindex = MagicMock(status_code=200)
    pageindex.raise_for_status = MagicMock()
    pageindex.json.return_value = {
        "hits": [{"doc_id": "d1", "section_id": "1", "details": "เนื้อหา", "score": 1}]
    }
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[missing, pageindex])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.rag.custom_rag_client.httpx.AsyncClient", return_value=mock_client):
        client = CustomRagClient(base_url="http://knowledge-rag:8000")
        chunks = await client.retrieve("ค้นหา")

    assert len(chunks) == 1
    assert chunks[0].metadata["rag_source"] == "pageindex_rag"
    assert mock_client.post.await_count == 2
    assert mock_client.post.await_args_list[1].args[0] == "http://knowledge-rag:8000/api/search"
