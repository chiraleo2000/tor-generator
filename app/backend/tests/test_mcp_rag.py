"""Unit tests for MCP RAG YAML parse and JSON-RPC mapping."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.mcp_rag import load_mcp_servers, parse_rag_sources_yaml, retrieve_mcp_chunks
from app.rag.mcp_rag import _chunks_from_tool_result


def test_parse_rag_sources_yaml_reads_disabled_servers() -> None:
    text = """
servers:
  - id: agency-legal-mcp
    enabled: false
    transport: http
    url: https://mcp.example.go.th/rag
    tool: retrieve
    timeout_seconds: 20
    top_k: 8
"""
    rows = parse_rag_sources_yaml(text)
    assert len(rows) == 1
    assert rows[0]["id"] == "agency-legal-mcp"
    assert rows[0]["enabled"] is False
    assert rows[0]["top_k"] == 8


def test_chunks_from_tool_result_reads_mcp_content_text() -> None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": '{"chunks":[{"text":"จาก MCP","score":0.7,"source_document":"ก"}]}',
                }
            ]
        },
    }
    chunks = _chunks_from_tool_result(payload, "agency")
    assert len(chunks) == 1
    assert chunks[0].text == "จาก MCP"
    assert chunks[0].metadata.get("rag_source") == "mcp"
    assert chunks[0].metadata.get("mcp_server") == "agency"


@pytest.mark.asyncio
async def test_retrieve_mcp_chunks_disabled_returns_empty() -> None:
    with patch("app.rag.mcp_rag.get_settings") as settings:
        settings.return_value = MagicMock(mcp_rag_enabled=False)
        assert await retrieve_mcp_chunks("ถาม") == []


@pytest.mark.asyncio
async def test_retrieve_mcp_chunks_fail_open_on_http_error() -> None:
    settings = MagicMock()
    settings.mcp_rag_enabled = True
    settings.mcp_rag_servers_json = ""
    settings.mcp_rag_config_path = ""
    settings.mcp_rag_timeout_seconds = 5.0
    yaml_text = """
servers:
  - id: down
    enabled: true
    transport: http
    url: http://127.0.0.1:9/rag
    tool: retrieve
    timeout_seconds: 1
    top_k: 2
"""
    with (
        patch("app.rag.mcp_rag.get_settings", return_value=settings),
        patch("app.rag.mcp_rag.load_mcp_servers", return_value=parse_rag_sources_yaml(yaml_text)),
        patch("app.rag.mcp_rag.httpx.AsyncClient") as client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=OSError("down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        client_cls.return_value = mock_client
        assert await retrieve_mcp_chunks("ถาม") == []


def test_load_mcp_servers_bad_json_returns_empty() -> None:
    settings = MagicMock(mcp_rag_servers_json="{not json", mcp_rag_config_path="")
    with patch("app.rag.mcp_rag.get_settings", return_value=settings):
        assert load_mcp_servers() == []


def test_chunks_from_tool_result_coerces_page_number() -> None:
    payload = {
        "chunks": [
            {
                "text": "หน้า",
                "score": 0.1,
                "page_number": "12",
                "source_document": "ก",
            }
        ]
    }
    chunks = _chunks_from_tool_result(payload, "agency")
    assert chunks[0].page_number == 12
