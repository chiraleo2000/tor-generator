"""Unit tests for MCP RAG YAML parse and JSON-RPC mapping."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.mcp_rag import (
    _chunks_from_tool_result,
    load_mcp_servers,
    parse_rag_sources_yaml,
    retrieve_mcp_chunks,
)
from app.rag.retrieval import coerce_page_number


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


def _rag_sources_yaml_path() -> Path:
    """Host layout is app/backend/tests; the test image mounts tests at /app/tests."""
    here = Path(__file__).resolve()
    candidates = [here.parents[1] / "infra" / "mcp" / "rag-sources.yaml"]
    if len(here.parents) > 3:
        candidates.append(
            here.parents[3] / "app" / "infra" / "mcp" / "rag-sources.yaml"
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("app/infra/mcp/rag-sources.yaml")


def test_repo_rag_sources_yaml_enables_local_pgvector_only() -> None:
    from app.rag.mcp_rag import parse_rag_sources_yaml

    path = _rag_sources_yaml_path()
    rows = parse_rag_sources_yaml(path.read_text(encoding="utf-8"))
    by_id = {str(row.get("id")): row for row in rows}
    assert by_id["local-pgvector-mcp"].get("enabled") is True
    assert by_id["local-pgvector-mcp"].get("url") == "http://mcp-rag:8765"
    assert by_id["agency-legal-mcp"].get("enabled") is False
    assert by_id["partner-kb-mcp"].get("enabled") is False
    assert by_id["retrieve-stub"].get("enabled") is False


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
    settings.mcp_rag_auth_value = ""
    settings.mcp_rag_auth_header = "Authorization"
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


def test_coerce_page_number_rejects_bool_and_junk() -> None:
    assert coerce_page_number(True) is None
    assert coerce_page_number("x") is None
    assert coerce_page_number("3") == 3
    assert coerce_page_number(None) is None


@pytest.mark.asyncio
async def test_retrieve_mcp_sends_auth_header_when_configured() -> None:
    from app.rag.mcp_rag import _call_server

    settings = MagicMock()
    settings.mcp_rag_auth_value = "secret-token"
    settings.mcp_rag_auth_header = "Authorization"
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"chunks": []}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    server = {
        "id": "agency",
        "url": "http://mcp.test/rag",
        "tool": "retrieve",
        "top_k": 2,
        "timeout_seconds": 5,
    }
    with (
        patch("app.rag.mcp_rag.get_settings", return_value=settings),
        patch("app.rag.mcp_rag.httpx.AsyncClient", return_value=mock_client),
    ):
        await _call_server(
            server, "ถาม", user_id=None, search_scope="both", default_timeout=5.0
        )
    headers = mock_client.post.await_args.kwargs["headers"]
    assert headers["Authorization"] == "secret-token"


@pytest.mark.asyncio
async def test_retrieve_mcp_omits_auth_header_when_blank() -> None:
    from app.rag.mcp_rag import _call_server

    settings = MagicMock()
    settings.mcp_rag_auth_value = "   "
    settings.mcp_rag_auth_header = "Authorization"
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"chunks": []}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    server = {"id": "agency", "url": "http://mcp.test/rag", "tool": "retrieve"}
    with (
        patch("app.rag.mcp_rag.get_settings", return_value=settings),
        patch("app.rag.mcp_rag.httpx.AsyncClient", return_value=mock_client),
    ):
        await _call_server(
            server, "ถาม", user_id=None, search_scope="both", default_timeout=5.0
        )
    assert mock_client.post.await_args.kwargs["headers"] is None


@pytest.mark.asyncio
async def test_retrieve_mcp_omits_auth_header_when_empty() -> None:
    from app.rag.mcp_rag import _call_server

    settings = MagicMock()
    settings.mcp_rag_auth_value = ""
    settings.mcp_rag_auth_header = "Authorization"
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"chunks": []}
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    server = {"id": "agency", "url": "http://mcp.test/rag", "tool": "retrieve"}
    with (
        patch("app.rag.mcp_rag.get_settings", return_value=settings),
        patch("app.rag.mcp_rag.httpx.AsyncClient", return_value=mock_client),
    ):
        await _call_server(
            server, "ถาม", user_id=None, search_scope="both", default_timeout=5.0
        )
    assert mock_client.post.await_args.kwargs["headers"] is None


@pytest.mark.asyncio
async def test_retrieve_mcp_auth_value_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    from app.rag.mcp_rag import _call_server, retrieve_mcp_chunks_with_status

    secret = "mcp-auth-secret-NEVER-LOG-9f3a"
    caplog.set_level("DEBUG")

    settings = MagicMock()
    settings.mcp_rag_enabled = True
    settings.mcp_rag_timeout_seconds = 1.0
    settings.mcp_rag_auth_value = secret
    settings.mcp_rag_auth_header = "Authorization"
    settings.mcp_rag_servers_json = ""
    settings.mcp_rag_config_path = ""

    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = {"chunks": []}
    mock_ok = AsyncMock()
    mock_ok.post = AsyncMock(return_value=response)
    mock_ok.__aenter__ = AsyncMock(return_value=mock_ok)
    mock_ok.__aexit__ = AsyncMock(return_value=None)
    server = {
        "id": "agency",
        "url": "http://mcp.test/rag",
        "tool": "retrieve",
        "timeout_seconds": 1,
        "top_k": 2,
    }
    with (
        patch("app.rag.mcp_rag.get_settings", return_value=settings),
        patch("app.rag.mcp_rag.httpx.AsyncClient", return_value=mock_ok),
    ):
        await _call_server(
            server, "ถาม", user_id=None, search_scope="both", default_timeout=1.0
        )

    mock_err = AsyncMock()
    mock_err.post = AsyncMock(side_effect=OSError("down"))
    mock_err.__aenter__ = AsyncMock(return_value=mock_err)
    mock_err.__aexit__ = AsyncMock(return_value=None)
    yaml_text = """
servers:
  - id: down
    enabled: true
    transport: http
    url: http://127.0.0.1:9/rag
    tool: retrieve
"""
    with (
        patch("app.rag.mcp_rag.get_settings", return_value=settings),
        patch(
            "app.rag.mcp_rag.load_mcp_servers",
            return_value=parse_rag_sources_yaml(yaml_text),
        ),
        patch("app.rag.mcp_rag.httpx.AsyncClient", return_value=mock_err),
    ):
        await retrieve_mcp_chunks_with_status("ถาม")

    blob = caplog.text
    for record in caplog.records:
        blob += record.getMessage()
        if record.exc_text:
            blob += record.exc_text
    assert secret not in blob


def test_load_mcp_servers_rejects_duplicate_ids() -> None:
    settings = MagicMock(
        mcp_rag_servers_json='{"servers":[{"id":"a"},{"id":"a"}]}',
        mcp_rag_config_path="",
    )
    with patch("app.rag.mcp_rag.get_settings", return_value=settings):
        assert load_mcp_servers() == []


@pytest.mark.asyncio
async def test_retrieve_mcp_with_status_marks_degraded_on_error() -> None:
    from app.rag.mcp_rag import retrieve_mcp_chunks_with_status

    settings = MagicMock()
    settings.mcp_rag_enabled = True
    settings.mcp_rag_timeout_seconds = 1.0
    yaml_text = """
servers:
  - id: down
    enabled: true
    transport: http
    url: http://127.0.0.1:9/rag
    tool: retrieve
"""
    with (
        patch("app.rag.mcp_rag.get_settings", return_value=settings),
        patch(
            "app.rag.mcp_rag.load_mcp_servers",
            return_value=parse_rag_sources_yaml(yaml_text),
        ),
        patch("app.rag.mcp_rag.httpx.AsyncClient") as client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=OSError("down"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        client_cls.return_value = mock_client
        chunks, degraded = await retrieve_mcp_chunks_with_status("ถาม")
    assert chunks == []
    assert degraded is True

