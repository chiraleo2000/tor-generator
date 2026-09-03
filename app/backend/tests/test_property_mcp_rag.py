"""Property tests for MCP RAG client (mcp-rag-config-and-deploy)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.rag.mcp_rag import (
    _auth_headers,
    _chunks_from_tool_result,
    _tools_call_payload,
    _visible_chunks,
    retrieve_mcp_chunks_with_status,
)
from app.rag.retrieval import RetrievedChunk

MAX_EX = 100


def _ok_response(chunks: list[dict] | None = None) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    inner = json.dumps({"chunks": chunks or [{"text": "ก", "score": 0.5, "source_document": "ด"}]})
    response.json.return_value = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {"content": [{"type": "text", "text": inner}]},
    }
    return response


def _client(post_side_effect=None, response=None) -> AsyncMock:
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=post_side_effect, return_value=response or _ok_response()
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def _enabled_settings(**kwargs):
    settings = MagicMock()
    settings.mcp_rag_enabled = True
    settings.mcp_rag_timeout_seconds = 20.0
    settings.mcp_rag_auth_header = "Authorization"
    settings.mcp_rag_auth_value = ""
    for key, value in kwargs.items():
        setattr(settings, key, value)
    return settings


server_entry = st.fixed_dictionaries(
    {"id": st.text(min_size=1, max_size=12, alphabet=st.characters(whitelist_categories=("L", "N")))},
    optional={
        "enabled": st.booleans(),
        "transport": st.sampled_from(["http", "stdio", "sse", ""]),
        "url": st.sampled_from(["http://mcp.test/rag", "", "   "]),
        "tool": st.sampled_from(["retrieve", "search", None]),
        "top_k": st.integers(min_value=1, max_value=20),
        "timeout_seconds": st.integers(min_value=1, max_value=30),
    },
)


@pytest.mark.property
@pytest.mark.asyncio
@given(rows=st.lists(server_entry, min_size=1, max_size=6))
@settings(max_examples=MAX_EX)
async def test_property_1_enabled_http_entry_filtering(rows: list[dict]) -> None:
    # Feature: mcp-rag-config-and-deploy, Property 1: Enabled HTTP Entry Filtering
    mock_client = _client()
    with (
        patch("app.rag.mcp_rag.get_settings", return_value=_enabled_settings()),
        patch("app.rag.mcp_rag.load_mcp_servers", return_value=rows),
        patch("app.rag.mcp_rag.httpx.AsyncClient", return_value=mock_client),
    ):
        await retrieve_mcp_chunks_with_status("ถาม")
    posted = [call.kwargs.get("url") or (call.args[0] if call.args else None) for call in mock_client.post.await_args_list]
    if not posted and mock_client.post.await_args_list:
        posted = [call.args[0] for call in mock_client.post.await_args_list if call.args]
    expected = [
        str(row.get("url") or "").strip()
        for row in rows
        if row.get("enabled") is True
        and str(row.get("transport") or "http") == "http"
        and str(row.get("url") or "").strip()
    ]
    assert mock_client.post.await_count == len(expected)


@pytest.mark.property
@given(
    tool=st.one_of(st.none(), st.just("retrieve"), st.just("search")),
    top_k=st.one_of(st.none(), st.integers(min_value=1, max_value=20)),
)
@settings(max_examples=MAX_EX)
def test_property_2_payload_defaults(tool: str | None, top_k: int | None) -> None:
    # Feature: mcp-rag-config-and-deploy, Property 2: Payload Defaults
    server: dict = {"id": "s1", "url": "http://x"}
    if tool is not None:
        server["tool"] = tool
    if top_k is not None:
        server["top_k"] = top_k
    payload = _tools_call_payload(server, "q", user_id=None, search_scope="both")
    assert payload["params"]["name"] == (tool or "retrieve")
    assert payload["params"]["arguments"]["top_k"] == (top_k if top_k is not None else 8)


@pytest.mark.property
@given(value=st.one_of(st.just(""), st.just("   "), st.just("token-abc"), st.text(max_size=20)))
@settings(max_examples=MAX_EX)
def test_property_3_conditional_auth_header(value: str) -> None:
    # Feature: mcp-rag-config-and-deploy, Property 3: Conditional Auth Header
    settings = MagicMock(mcp_rag_auth_value=value, mcp_rag_auth_header="Authorization")
    with patch("app.rag.mcp_rag.get_settings", return_value=settings):
        headers = _auth_headers()
    if value.strip():
        assert headers.get("Authorization") == value.strip()
    else:
        assert headers == {}


@pytest.mark.property
@pytest.mark.asyncio
@given(kind=st.sampled_from(["os", "http", "json"]))
@settings(max_examples=MAX_EX)
async def test_property_4_single_server_failure_isolation(kind: str) -> None:
    # Feature: mcp-rag-config-and-deploy, Property 4: Single-Server Failure Isolation
    if kind == "os":
        effect = OSError("down")
    elif kind == "http":
        effect = httpx.ConnectError("down")
    else:
        effect = json.JSONDecodeError("bad", "", 0)
    mock_client = _client(post_side_effect=effect)
    servers = [
        {
            "id": "broken",
            "enabled": True,
            "transport": "http",
            "url": "http://mcp.test/rag",
            "tool": "retrieve",
        }
    ]
    with (
        patch("app.rag.mcp_rag.get_settings", return_value=_enabled_settings()),
        patch("app.rag.mcp_rag.load_mcp_servers", return_value=servers),
        patch("app.rag.mcp_rag.httpx.AsyncClient", return_value=mock_client),
    ):
        chunks, degraded = await retrieve_mcp_chunks_with_status("ถาม")
    assert chunks == []
    assert degraded is True


@pytest.mark.property
@pytest.mark.asyncio
@given(query=st.text(min_size=1, max_size=30))
@settings(max_examples=MAX_EX)
async def test_property_5_no_retry_on_timeout(query: str) -> None:
    # Feature: mcp-rag-config-and-deploy, Property 5: No Retry On Failure
    mock_client = _client(post_side_effect=httpx.TimeoutException("timeout"))
    servers = [
        {
            "id": "slow",
            "enabled": True,
            "transport": "http",
            "url": "http://mcp.test/rag",
        }
    ]
    with (
        patch("app.rag.mcp_rag.get_settings", return_value=_enabled_settings()),
        patch("app.rag.mcp_rag.load_mcp_servers", return_value=servers),
        patch("app.rag.mcp_rag.httpx.AsyncClient", return_value=mock_client),
    ):
        await retrieve_mcp_chunks_with_status(query)
    assert mock_client.post.await_count == 1


@pytest.mark.property
@given(
    text=st.text(min_size=1, max_size=40).filter(lambda item: item.strip()),
    score=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    server_id=st.text(min_size=1, max_size=8, alphabet="abcdef123"),
)
@settings(max_examples=MAX_EX)
def test_property_9_mcp_chunk_source_tagging(text: str, score: float, server_id: str) -> None:
    # Feature: mcp-rag-config-and-deploy, Property 9: MCP Chunk Source Tagging
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"chunks": [{"text": text, "score": score, "source_document": "ด"}]}
                    ),
                }
            ]
        },
    }
    chunks = _chunks_from_tool_result(payload, server_id)
    assert chunks
    for chunk in chunks:
        assert chunk.metadata.get("rag_source") == "mcp"
        assert chunk.metadata.get("mcp_server") == server_id


@pytest.mark.property
@given(
    owner=st.one_of(st.none(), st.uuids().map(str)),
    viewer=st.one_of(st.none(), st.uuids().map(str)),
    scope=st.sampled_from(["both", "mine", "global", ""]),
)
@settings(max_examples=MAX_EX)
def test_property_11_acl_on_owned_chunks(
    owner: str | None, viewer: str | None, scope: str
) -> None:
    # Feature: mcp-rag-config-and-deploy, Property 11: ACL Enforcement On Owned Chunks
    chunk = RetrievedChunk(
        id="c1",
        text="t",
        score=0.5,
        metadata={"owner_id": owner} if owner else {},
    )
    visible = _visible_chunks([chunk], user_id=viewer, search_scope=scope)
    if owner is None:
        assert visible == [chunk]
        return
    if not scope or viewer is None:
        assert visible == []
        return
    if scope == "global":
        assert visible == []
        return
    if str(owner) == str(viewer) and scope in {"both", "mine"}:
        assert visible == [chunk]
    else:
        assert visible == []


@pytest.mark.property
@given(
    text=st.text(min_size=1, max_size=40).filter(lambda item: item.strip()),
    score=st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
    source=st.text(min_size=1, max_size=20).filter(lambda item: item.strip()),
)
@settings(max_examples=MAX_EX)
def test_property_12_retrieve_contract_shape(text: str, score: float, source: str) -> None:
    # Feature: mcp-rag-config-and-deploy, Property 12: Retrieve Contract Shape Equivalence
    payload = {
        "result": {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {"chunks": [{"text": text, "score": score, "source_document": source}]}
                    ),
                }
            ]
        }
    }
    chunks = _chunks_from_tool_result(payload, "origin")
    assert chunks
    for chunk in chunks:
        assert chunk.text.strip()
        assert isinstance(chunk.score, float)
        assert chunk.source_document
    _ = uuid4()
