"""Optional MCP RAG retrieve client (JSON-RPC 2.0 over HTTP).

Fail-open: a down server never blocks pgvector / Custom RAG results.
This is an extra data source — not DEPLOYMENT_MODE=hybrid.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx

from app.config import get_settings
from app.rag.acl import document_is_visible
from app.rag.retrieval import RetrievedChunk, coerce_page_number

logger = logging.getLogger(__name__)


def _scalar(raw: str) -> Any:
    text = raw.strip().strip('"').strip("'")
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none", "~"}:
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _parse_yaml_kv(line: str) -> tuple[str, Any] | None:
    if ":" not in line:
        return None
    key, value = line.split(":", 1)
    return key.strip(), _scalar(value)


def _start_server_entry(rest: str) -> dict[str, Any]:
    current: dict[str, Any] = {}
    parsed = _parse_yaml_kv(rest)
    if parsed:
        current[parsed[0]] = parsed[1]
    return current


def _parse_yaml_server_line(
    servers: list[dict[str, Any]],
    current: dict[str, Any] | None,
    line: str,
) -> dict[str, Any] | None:
    if line.startswith("  - "):
        if current:
            servers.append(current)
        return _start_server_entry(line[4:])
    if current is not None and line.startswith("    "):
        parsed = _parse_yaml_kv(line.strip())
        if parsed:
            current[parsed[0]] = parsed[1]
    return current


def parse_rag_sources_yaml(text: str) -> list[dict[str, Any]]:
    """Parse the constrained rag-sources.yaml shape (no PyYAML dependency)."""
    servers: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip() or line.strip() == "servers:":
            continue
        current = _parse_yaml_server_line(servers, current, line)
    if current:
        servers.append(current)
    return servers


def _servers_from_json(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        rows = data.get("servers")
        return rows if isinstance(rows, list) else []
    return data if isinstance(data, list) else []


def load_mcp_servers() -> list[dict[str, Any]]:
    settings = get_settings()
    inline = str(getattr(settings, "mcp_rag_servers_json", "") or "").strip()
    if inline:
        try:
            data = json.loads(inline)
        except json.JSONDecodeError:
            logger.warning("MCP_RAG_SERVERS_JSON is not valid JSON")
            return []
        return _servers_from_json(data)
    path_value = str(getattr(settings, "mcp_rag_config_path", "") or "").strip()
    if not path_value:
        return []
    path = Path(path_value)
    if not path.is_file():
        logger.warning("MCP_RAG_CONFIG not found: %s", path)
        return []
    return parse_rag_sources_yaml(path.read_text(encoding="utf-8"))


def _tool_result_body(payload: Any) -> Any:
    if not isinstance(payload, dict) or "result" not in payload:
        return payload
    result = payload.get("result") or {}
    content = result.get("content") if isinstance(result, dict) else None
    if not isinstance(content, list) or not content:
        return payload
    first = content[0]
    text = first.get("text") if isinstance(first, dict) else None
    if not isinstance(text, str) or not text.strip().startswith("{"):
        return payload
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"chunks": []}


def _coerce_page_number(item: dict[str, Any], metadata: dict[str, Any]) -> int | None:
    raw = item.get("page_number")
    if raw is None:
        raw = metadata.get("page_number")
    return coerce_page_number(raw)


def _chunk_from_item(item: dict[str, Any], server_id: str, index: int) -> RetrievedChunk | None:
    text = str(item.get("text") or "").strip()
    if not text:
        return None
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    metadata = {**metadata, "rag_source": "mcp", "mcp_server": server_id}
    source = (
        item.get("source_document")
        or metadata.get("source_document")
        or metadata.get("document_name")
    )
    try:
        score = float(item.get("score") or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    return RetrievedChunk(
        id=str(item.get("id") or f"mcp-{server_id}-{uuid4().hex[:8]}-{index}"),
        text=text,
        score=score,
        document_type=metadata.get("document_type"),
        legal_reference=metadata.get("legal_reference"),
        section_relevance=metadata.get("section_relevance"),
        source_document=str(source) if source else server_id,
        section_label=metadata.get("section_label"),
        page_number=_coerce_page_number(item, metadata),
        metadata=metadata,
    )


def _chunks_from_tool_result(payload: Any, server_id: str) -> list[RetrievedChunk]:
    body = _tool_result_body(payload)
    raw_chunks = body.get("chunks") if isinstance(body, dict) else None
    if not isinstance(raw_chunks, list):
        return []
    mapped: list[RetrievedChunk] = []
    for index, item in enumerate(raw_chunks):
        if not isinstance(item, dict):
            continue
        chunk = _chunk_from_item(item, server_id, index)
        if chunk is not None:
            mapped.append(chunk)
    return mapped


def _visible_chunks(
    chunks: list[RetrievedChunk],
    *,
    user_id: UUID | str | None,
    search_scope: str,
) -> list[RetrievedChunk]:
    visible: list[RetrievedChunk] = []
    for chunk in chunks:
        owner = (chunk.metadata or {}).get("owner_id")
        if owner is None or document_is_visible(
            document_owner_id=owner,
            viewer_id=user_id,
            search_scope=search_scope,
        ):
            visible.append(chunk)
    return visible


def _tools_call_payload(
    server: dict[str, Any],
    query: str,
    *,
    user_id: UUID | str | None,
    search_scope: str,
) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": str(server.get("tool") or "retrieve"),
            "arguments": {
                "query": query,
                "top_k": int(server.get("top_k") or 8),
                "search_scope": search_scope,
                "user_id": str(user_id) if user_id else None,
            },
        },
    }


async def _call_server(
    server: dict[str, Any],
    query: str,
    *,
    user_id: UUID | str | None,
    search_scope: str,
    default_timeout: float,
) -> list[RetrievedChunk]:
    url = str(server.get("url") or "").strip()
    if not url:
        return []
    timeout = float(server.get("timeout_seconds") or default_timeout)
    server_id = str(server.get("id") or "mcp")
    payload = _tools_call_payload(
        server, query, user_id=user_id, search_scope=search_scope
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    return _visible_chunks(
        _chunks_from_tool_result(data, server_id),
        user_id=user_id,
        search_scope=search_scope,
    )


async def retrieve_mcp_chunks(
    query: str,
    *,
    user_id: UUID | str | None = None,
    search_scope: str = "both",
) -> list[RetrievedChunk]:
    """Fetch chunks from enabled MCP servers. Empty list when disabled or on error."""
    settings = get_settings()
    if not getattr(settings, "mcp_rag_enabled", False):
        return []
    default_timeout = float(getattr(settings, "mcp_rag_timeout_seconds", 20.0) or 20.0)
    collected: list[RetrievedChunk] = []
    for server in load_mcp_servers():
        if not server.get("enabled"):
            continue
        if str(server.get("transport") or "http") != "http":
            logger.warning("Skipping MCP server %s: transport not http", server.get("id"))
            continue
        try:
            collected.extend(
                await _call_server(
                    server,
                    query,
                    user_id=user_id,
                    search_scope=search_scope,
                    default_timeout=default_timeout,
                )
            )
        except (httpx.HTTPError, OSError, json.JSONDecodeError):
            logger.warning(
                "MCP RAG server %s failed; continuing",
                server.get("id"),
                exc_info=True,
            )
    return collected
