"""JSON-RPC MCP retrieve backed by local pgvector (Compose service mcp-rag).

This process is the server. Do not set MCP_RAG_ENABLED=true here or it would
call itself. The API backend is the client (MCP_RAG_ENABLED=true).
"""

from __future__ import annotations

import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.rag.hybrid import _retrieve_local_chunks
from app.rag.retrieval import RetrievedChunk

logger = logging.getLogger("tor_mcp_rag")

HOST = os.environ.get("MCP_RAG_SERVER_HOST", "0.0.0.0")
PORT = int(os.environ.get("MCP_RAG_SERVER_PORT", "8765"))
PROTOCOL_VERSION = "2024-11-05"

_LOOPBACK_HOSTS = ("127.0.0.1", "localhost")


def _rewrite_loopback_for_docker() -> None:
    """Compose interpolation can leak a host-only LM Studio URL into this container."""
    if not Path("/.dockerenv").exists():
        return
    for key in ("LM_STUDIO_BASE_URL", "LOCAL_EMBEDDING_BASE_URL"):
        url = os.environ.get(key, "")
        if not url:
            continue
        rewritten = url
        for host in _LOOPBACK_HOSTS:
            rewritten = rewritten.replace(host, "host.docker.internal")
        if rewritten != url:
            os.environ[key] = rewritten


_rewrite_loopback_for_docker()

RETRIEVE_TOOL: dict[str, Any] = {
    "name": "retrieve",
    "description": (
        "Retrieve Thai public-procurement knowledge snippets from the local "
        "pgvector corpus (documents/sources)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language question or search text.",
            },
            "top_k": {"type": "integer", "description": "Maximum snippets to return."},
            "search_scope": {"type": "string"},
            "user_id": {"type": "string"},
        },
        "required": ["query"],
    },
}


def _rpc_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _rpc_result(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _user_id_from_args(args: dict[str, Any]) -> UUID | None:
    raw = args.get("user_id")
    if raw is None or str(raw).strip() in {"", "None"}:
        return None
    try:
        return UUID(str(raw))
    except ValueError:
        return None


def chunk_to_mcp_item(chunk: RetrievedChunk) -> dict[str, Any]:
    metadata = dict(chunk.metadata or {})
    metadata["rag_source"] = "mcp"
    if chunk.document_type:
        metadata.setdefault("document_type", chunk.document_type)
    if chunk.legal_reference:
        metadata.setdefault("legal_reference", chunk.legal_reference)
    if chunk.section_relevance:
        metadata.setdefault("section_relevance", chunk.section_relevance)
    if chunk.section_label:
        metadata.setdefault("section_label", chunk.section_label)
    item: dict[str, Any] = {
        "id": chunk.id,
        "text": chunk.text,
        "score": chunk.score,
        "source_document": chunk.source_document,
        "metadata": metadata,
    }
    if chunk.page_number is not None:
        item["page_number"] = chunk.page_number
    return item


async def retrieve_pgvector_items(
    query: str,
    *,
    top_k: int,
    user_id: UUID | None,
    search_scope: str,
) -> list[dict[str, Any]]:
    chunks = await _retrieve_local_chunks(
        query,
        user_id=user_id,
        search_scope=search_scope or "both",
        top_k=max(1, top_k),
        section_relevance=None,
        extra_filter=None,
    )
    return [chunk_to_mcp_item(chunk) for chunk in chunks]


def _initialize_result(req_id: Any) -> dict[str, Any]:
    return _rpc_result(
        req_id,
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "tor-mcp-pgvector", "version": "1.0.0"},
        },
    )


def _tools_list_result(req_id: Any) -> dict[str, Any]:
    return _rpc_result(req_id, {"tools": [RETRIEVE_TOOL]})


def _retrieve_rpc_result(req_id: Any, items: list[dict[str, Any]]) -> dict[str, Any]:
    body = {"chunks": items}
    return _rpc_result(
        req_id,
        {"content": [{"type": "text", "text": json.dumps(body, ensure_ascii=False)}]},
    )


async def dispatch_rpc(payload: dict[str, Any]) -> tuple[int, dict[str, Any] | None]:
    """Return (HTTP status, JSON-RPC body). Body is None for notifications (HTTP 204)."""
    req_id = payload.get("id")
    method = str(payload.get("method") or "")
    if method == "notifications/initialized":
        return 204, None
    if method == "initialize":
        return 200, _initialize_result(req_id)
    if method == "tools/list":
        return 200, _tools_list_result(req_id)
    if method != "tools/call":
        return 200, _rpc_error(req_id, -32601, "method not found")
    params = payload.get("params") or {}
    args = params.get("arguments") or {}
    if not isinstance(args, dict):
        args = {}
    if str(params.get("name") or "") != "retrieve":
        return 200, _rpc_error(req_id, -32601, "unknown tool")
    try:
        top_k = int(args.get("top_k") or 8)
    except (TypeError, ValueError):
        top_k = 8
    try:
        items = await retrieve_pgvector_items(
            str(args.get("query") or ""),
            top_k=top_k,
            user_id=_user_id_from_args(args),
            search_scope=str(args.get("search_scope") or "both"),
        )
    except Exception:
        logger.exception("pgvector MCP retrieve failed")
        items = []
    return 200, _retrieve_rpc_result(req_id, items)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=5)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    from app.infra import set_session_factory

    set_session_factory(factory)
    logger.info("MCP pgvector retrieve listening with Postgres %s", settings.postgres_host)
    try:
        yield
    finally:
        set_session_factory(None)
        await engine.dispose()


app = FastAPI(title="TOR MCP pgvector retrieve", lifespan=lifespan)


@app.get("/health")
@app.get("/")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "tor-mcp-pgvector"}


@app.post("/")
@app.post("/mcp")
async def mcp_rpc(request: Request) -> Response:
    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(_rpc_error(None, -32700, "parse error"), status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse(_rpc_error(None, -32600, "invalid request"), status_code=400)
    status, body = await dispatch_rpc(payload)
    if body is None:
        return Response(status_code=status)
    return JSONResponse(body, status_code=status)


def main() -> None:
    import uvicorn

    uvicorn.run(app, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
