"""JSON-RPC surface of the local pgvector MCP retrieve server."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

from app.mcp_retrieve_server import (
    chunk_to_mcp_item,
    dispatch_rpc,
)
from app.rag.retrieval import RetrievedChunk


@pytest.mark.asyncio
async def test_dispatch_initialize_and_tools_list() -> None:
    status, init_body = await dispatch_rpc(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    )
    assert status == 200
    assert init_body is not None
    assert init_body["result"]["serverInfo"]["name"] == "tor-mcp-pgvector"

    status, listed = await dispatch_rpc(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    )
    assert status == 200
    assert listed is not None
    assert listed["result"]["tools"][0]["name"] == "retrieve"

    status, note = await dispatch_rpc({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert status == 204
    assert note is None


@pytest.mark.asyncio
async def test_dispatch_retrieve_wraps_pgvector_chunks() -> None:
    chunk = RetrievedChunk(
        id="c1",
        text="วิธีเฉพาะเจาะจง",
        score=0.81,
        source_document="ระเบียบ.pdf",
        page_number=3,
        metadata={"document_type": "regulation"},
    )
    with patch(
        "app.mcp_retrieve_server.retrieve_pgvector_items",
        new_callable=AsyncMock,
        return_value=[chunk_to_mcp_item(chunk)],
    ):
        status, body = await dispatch_rpc(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "retrieve",
                    "arguments": {"query": "วงเงิน", "top_k": 4},
                },
            }
        )
    assert status == 200
    assert body is not None
    text = body["result"]["content"][0]["text"]
    assert "วิธีเฉพาะเจาะจง" in text
    assert "ระเบียบ.pdf" in text


@pytest.mark.asyncio
async def test_dispatch_unknown_tool() -> None:
    status, body = await dispatch_rpc(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "other", "arguments": {"query": "x"}},
        }
    )
    assert status == 200
    assert body is not None
    assert body["error"]["code"] == -32601


def test_chunk_to_mcp_item_sets_rag_source() -> None:
    item = chunk_to_mcp_item(
        RetrievedChunk(id="a", text="ท", score=0.2, source_document="ก.pdf")
    )
    assert item["metadata"]["rag_source"] == "mcp"
    assert item["source_document"] == "ก.pdf"


def test_rewrite_loopback_for_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import mcp_retrieve_server as server

    monkeypatch.setenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")
    monkeypatch.setattr(server.Path, "exists", lambda _self: True)
    server._rewrite_loopback_for_docker()
    assert os.environ["LM_STUDIO_BASE_URL"] == "http://host.docker.internal:1234/v1"
