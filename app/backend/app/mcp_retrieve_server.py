"""JSON-RPC MCP retrieve (Compose service mcp-rag).

Backends (PN_RETRIEVE_BACKEND):
  - s3_vectors — Cohere Embed 4 query + S3 Vectors (PN cloud default)
  - pgvector — local Postgres (dev / bridge)

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
_minio_client: Any = None


def _retrieve_backend() -> str:
    raw = (os.environ.get("PN_RETRIEVE_BACKEND") or "").strip().lower()
    if raw in {"s3_vectors", "s3vectors", "s3"}:
        return "s3_vectors"
    if raw in {"pgvector", "pg", "local"}:
        return "pgvector"
    # Auto: S3 Vectors only when the dedicated vector bucket is configured
    if (os.environ.get("PN_S3_VECTOR_BUCKET") or "").strip():
        return "s3_vectors"
    return "pgvector"

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
        "Retrieve Thai public-procurement knowledge snippets. "
        "Prefer list_rag_groups then pass rag_group. "
        "PN cloud uses S3 Vectors + Cohere Embed 4; local may use pgvector."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural-language question or search text.",
            },
            "top_k": {
                "type": "integer",
                "description": "Maximum snippets (PN default 3, max 5).",
            },
            "rag_group": {
                "type": "string",
                "description": (
                    "RAG group id on the shared bucket "
                    "(e.g. procurement-th, agency-extra). "
                    "Required for S3 Vectors; empty uses default group."
                ),
            },
            "search_scope": {"type": "string"},
            "user_id": {"type": "string"},
        },
        "required": ["query"],
    },
}

LIST_RAG_GROUPS_TOOL: dict[str, Any] = {
    "name": "list_rag_groups",
    "description": (
        "List available RAG groups on the shared S3 bucket that MCP may search. "
        "Use an id from this list as retrieve.rag_group."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

MCP_TOOLS = [RETRIEVE_TOOL, LIST_RAG_GROUPS_TOOL]


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


def _rag_group_filter(rag_group: str | None) -> dict[str, Any] | None:
    gid = (rag_group or "").strip()
    if not gid:
        return None
    return {"rag_group": gid}


def list_rag_groups_payload() -> dict[str, Any]:
    try:
        from app.pn_rag.config import get_rag_groups_config

        cfg = get_rag_groups_config()
        groups = [
            {
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "vector_index": g.vector_index,
                "prefix": g.prefix,
            }
            for g in cfg.mcp_groups()
        ]
        return {
            "default_group": cfg.default_group,
            "bucket": cfg.bucket,
            "groups": groups,
        }
    except Exception:
        logger.exception("list_rag_groups failed")
        return {"default_group": "", "bucket": "", "groups": []}


async def retrieve_pgvector_items(
    query: str,
    *,
    top_k: int,
    user_id: UUID | None,
    search_scope: str,
    rag_group: str | None = None,
) -> list[dict[str, Any]]:
    chunks = await _retrieve_local_chunks(
        query,
        user_id=user_id,
        search_scope=search_scope or "both",
        top_k=max(1, top_k),
        section_relevance=None,
        extra_filter=_rag_group_filter(rag_group),
    )
    items = [chunk_to_mcp_item(chunk) for chunk in chunks]
    if rag_group and rag_group.strip():
        for item in items:
            meta = item.setdefault("metadata", {})
            if isinstance(meta, dict):
                meta.setdefault("rag_group", rag_group.strip())
    return items


async def retrieve_s3_vector_items(
    query: str,
    *,
    top_k: int,
    rag_group: str | None = None,
) -> list[dict[str, Any]]:
    from app.pn_rag.retrieve import retrieve_pn_chunks

    return await retrieve_pn_chunks(
        query,
        rag_group=rag_group,
        top_k=top_k,
        minio_client=_minio_client,
    )


async def retrieve_items(
    query: str,
    *,
    top_k: int,
    user_id: UUID | None,
    search_scope: str,
    rag_group: str | None = None,
) -> list[dict[str, Any]]:
    if _retrieve_backend() == "s3_vectors":
        return await retrieve_s3_vector_items(
            query, top_k=top_k, rag_group=rag_group
        )
    return await retrieve_pgvector_items(
        query,
        top_k=top_k,
        user_id=user_id,
        search_scope=search_scope,
        rag_group=rag_group,
    )


def _initialize_result(req_id: Any) -> dict[str, Any]:
    return _rpc_result(
        req_id,
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "tor-mcp-retrieve", "version": "1.1.0"},
        },
    )


def _tools_list_result(req_id: Any) -> dict[str, Any]:
    return _rpc_result(req_id, {"tools": MCP_TOOLS})


def _text_tool_result(req_id: Any, payload: dict[str, Any]) -> dict[str, Any]:
    return _rpc_result(
        req_id,
        {
            "content": [
                {"type": "text", "text": json.dumps(payload, ensure_ascii=False)}
            ]
        },
    )


def _retrieve_rpc_result(req_id: Any, items: list[dict[str, Any]]) -> dict[str, Any]:
    return _text_tool_result(req_id, {"chunks": items})


def _retrieve_top_k(args: dict[str, Any]) -> int:
    default_k = 3 if _retrieve_backend() == "s3_vectors" else 8
    try:
        top_k = int(args.get("top_k") or default_k)
    except (TypeError, ValueError):
        top_k = default_k
    if _retrieve_backend() != "s3_vectors":
        return top_k
    return max(1, min(top_k, int(os.environ.get("PN_RETRIEVE_TOP_K_MAX") or 5)))


async def _handle_tools_call(req_id: Any, params: Any) -> tuple[int, dict[str, Any] | None]:
    params = params or {}
    args = params.get("arguments") or {}
    if not isinstance(args, dict):
        args = {}
    tool_name = str(params.get("name") or "")
    if tool_name == "list_rag_groups":
        return 200, _text_tool_result(req_id, list_rag_groups_payload())
    if tool_name != "retrieve":
        return 200, _rpc_error(req_id, -32601, "unknown tool")
    try:
        items = await retrieve_items(
            str(args.get("query") or ""),
            top_k=_retrieve_top_k(args),
            user_id=_user_id_from_args(args),
            search_scope=str(args.get("search_scope") or "both"),
            rag_group=str(args.get("rag_group") or "").strip() or None,
        )
    except Exception:
        logger.exception("MCP retrieve failed backend=%s", _retrieve_backend())
        items = []
    return 200, _retrieve_rpc_result(req_id, items)


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
    return await _handle_tools_call(req_id, payload.get("params") or {})


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _minio_client
    settings = get_settings()
    backend = _retrieve_backend()
    engine = None
    if backend == "pgvector":
        engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=5)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        from app.infra import set_session_factory

        set_session_factory(factory)
        logger.info(
            "MCP retrieve backend=pgvector postgres=%s", settings.postgres_host
        )
    else:
        try:
            from app.export.minio_storage import build_minio_client

            _minio_client = build_minio_client(settings)
        except Exception:
            logger.exception("MinIO/S3 client init failed; chunk text may be preview-only")
            _minio_client = None
        logger.info(
            "MCP retrieve backend=s3_vectors bucket=%s vector_bucket=%s",
            settings.minio_bucket,
            os.environ.get("PN_S3_VECTOR_BUCKET") or settings.minio_bucket,
        )
    try:
        yield
    finally:
        _minio_client = None
        if engine is not None:
            from app.infra import set_session_factory

            set_session_factory(None)
            await engine.dispose()


app = FastAPI(title="TOR MCP retrieve", lifespan=lifespan)


@app.get("/health")
@app.get("/")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "tor-mcp-retrieve",
        "backend": _retrieve_backend(),
    }


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
