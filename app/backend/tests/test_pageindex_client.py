"""Tests for PageIndex document lifecycle client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.pageindex_client import PageIndexClient


@pytest.mark.asyncio
async def test_ingest_sends_tor_document_identity_and_acl() -> None:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "ok": True,
        "doc_id": "doc-1",
        "status": "ready",
        "total_records": 7,
    }
    http = AsyncMock()
    http.post = AsyncMock(return_value=response)
    http.__aenter__ = AsyncMock(return_value=http)
    http.__aexit__ = AsyncMock(return_value=None)

    with patch("app.rag.pageindex_client.httpx.AsyncClient", return_value=http):
        client = PageIndexClient(
            base_url="http://pageindex:8000/api/search",
            api_key="secret",
        )
        payload = await client.ingest_document(
            document_id="doc-1",
            document_name="law.pdf",
            content=b"%PDF-1.4 test",
            mime_type="application/pdf",
            category="law",
            owner_id="user-1",
            scope="user",
        )

    assert payload["total_records"] == 7
    _, kwargs = http.post.await_args
    assert http.post.await_args.args[0] == "http://pageindex:8000/api/ingest"
    assert kwargs["data"] == {
        "doc_id": "doc-1",
        "display_name": "law.pdf",
        "category": "law",
        "owner_id": "user-1",
        "scope": "user",
        "replace": "true",
    }
    assert kwargs["headers"]["X-API-Key"] == "secret"
    assert kwargs["files"]["file"][0] == "law.pdf"


@pytest.mark.asyncio
async def test_delete_treats_missing_pageindex_document_as_success() -> None:
    response = MagicMock(status_code=404)
    http = AsyncMock()
    http.delete = AsyncMock(return_value=response)
    http.__aenter__ = AsyncMock(return_value=http)
    http.__aexit__ = AsyncMock(return_value=None)

    with patch("app.rag.pageindex_client.httpx.AsyncClient", return_value=http):
        await PageIndexClient(base_url="http://pageindex:8000").delete_document("missing")

    http.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingest_adds_extension_from_mime_when_display_name_has_none() -> None:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {
        "ok": True,
        "doc_id": "doc-2",
        "status": "ready",
        "total_records": 3,
    }
    http = AsyncMock()
    http.post = AsyncMock(return_value=response)
    http.__aenter__ = AsyncMock(return_value=http)
    http.__aexit__ = AsyncMock(return_value=None)

    with patch("app.rag.pageindex_client.httpx.AsyncClient", return_value=http):
        await PageIndexClient(base_url="http://pageindex:8000").ingest_document(
            document_id="doc-2",
            document_name="กฎกระทรวงวงเงิน",
            content="ข้อความ".encode(),
            mime_type="text/plain",
            category="regulation",
            owner_id=None,
            scope="baseline",
        )

    _, kwargs = http.post.await_args
    assert kwargs["data"]["display_name"] == "กฎกระทรวงวงเงิน"
    assert kwargs["files"]["file"][0] == "กฎกระทรวงวงเงิน.txt"
