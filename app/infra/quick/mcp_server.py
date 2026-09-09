#!/usr/bin/env python3
"""Amazon Quick remote MCP + REST twin (JSON Schema Draft 7, no stdio).

Amazon Quick registers tools from tools/list. inputSchema.required must be an
array of property names (Draft 7), never a boolean on each property.
Tool calls time out at 60s on Quick — keep handlers local and fast.

When QUICK_RAG_MCP_URL is set (Compose default: http://mcp-rag:8765/mcp),
retrieve proxies to the project's pgvector MCP so Quick uses real RAG chunks.
When unset, retrieve returns a local stub (unit tests / offline).

Endpoints:
  GET  /health
  POST /retrieve     REST twin for OpenAPI (flat object, no arrays)
  POST /  and /mcp   JSON-RPC MCP (initialize, tools/list, tools/call)
"""

from __future__ import annotations

import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler as _RequestHandler
from http.server import ThreadingHTTPServer as _ThreadingServer
from typing import Any

HOST = os.environ.get("QUICK_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("QUICK_MCP_PORT", "8767"))
PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "0.5.0"
MCP_TOOLS_CALL = "tools/call"
_JSON = "application/json"
_HEALTH_PATH = "/health"
_MCP_PATHS = {"/", "/mcp"}
_POST_AUTH_PATHS = {"/", "/mcp", "/retrieve"}
_HEALTH_PATHS = {"/", _HEALTH_PATH}

RETRIEVE_TOOL: dict[str, Any] = {
    "name": "retrieve",
    "description": (
        "Search Thai public-procurement knowledge for TOR drafting. "
        "Optional rag_group selects which RAG corpus on the shared S3 bucket "
        "(call list_rag_groups first). Returns grounded snippets."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Question or search text in Thai or English.",
            },
            "top_k": {
                "type": "integer",
                "description": "Hint for how many snippets to prefer. Optional.",
            },
            "rag_group": {
                "type": "string",
                "description": "RAG group id (e.g. procurement-th). Optional.",
            },
        },
        "required": ["query"],
    },
}

PING_TOOL: dict[str, Any] = {
    "name": "ping",
    "description": "Liveness check for the TOR Amazon Quick connector. No arguments.",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

HEALTH_TOOL: dict[str, Any] = {
    "name": "get_health",
    "description": (
        "Return connector health as a short status string. Use before retrieve "
        "when diagnosing a failed Amazon Quick action."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

LIST_RAG_GROUPS_TOOL: dict[str, Any] = {
    "name": "list_rag_groups",
    "description": (
        "List RAG groups available on the shared S3 bucket. "
        "Pass an id to retrieve as rag_group."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

TOOLS = [RETRIEVE_TOOL, LIST_RAG_GROUPS_TOOL, PING_TOOL, HEALTH_TOOL]


def rag_mcp_url() -> str:
    return str(os.environ.get("QUICK_RAG_MCP_URL") or "").strip()


def _auth_configured() -> tuple[str, str]:
    header = str(os.environ.get("QUICK_MCP_AUTH_HEADER") or "Authorization").strip()
    if not header:
        header = "Authorization"
    value = str(os.environ.get("QUICK_MCP_AUTH_VALUE") or "").strip()
    return header, value


def request_authorized(headers: Any) -> bool:
    """Fail-safe: empty QUICK_MCP_AUTH_VALUE means no header is required."""
    header, expected = _auth_configured()
    if not expected:
        return True
    got = ""
    if headers is not None:
        got = str(headers.get(header) or "")
    return got == expected


def _rpc_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _rpc_result(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _stub_chunk(query: str) -> dict[str, Any]:
    return {
        "text": f"ชิ้นจำลองจาก Amazon Quick MCP สำหรับคำถาม: {query[:120]}",
        "score": 0.62,
        "source_document": "amazon-quick-mcp",
        "metadata": {"rag_source": "mcp", "mode": "stub"},
    }


def _http_json(url: str, payload: dict[str, Any], *, timeout: float = 45.0) -> dict[str, Any]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": _JSON, "Accept": _JSON},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw) if raw else {}
    return parsed if isinstance(parsed, dict) else {}


def _chunks_from_mcp_result(body: dict[str, Any]) -> list[dict[str, Any]]:
    result = body.get("result") or {}
    content = result.get("content") or []
    if not content:
        return []
    first = content[0] if isinstance(content, list) else {}
    text = str((first or {}).get("text") or "")
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [{"text": text, "score": 0.0, "source_document": "mcp-rag", "metadata": {}}]
    chunks = parsed.get("chunks") if isinstance(parsed, dict) else None
    if not isinstance(chunks, list):
        return []
    out: list[dict[str, Any]] = []
    for item in chunks:
        if isinstance(item, dict) and str(item.get("text") or "").strip():
            out.append(item)
    return out


def fetch_rag_chunks(
    query: str, top_k: int = 5, rag_group: str | None = None
) -> list[dict[str, Any]]:
    """Proxy retrieve to project mcp-rag (pgvector). Empty URL → stub chunk."""
    url = rag_mcp_url()
    if not url:
        return [_stub_chunk(query)]
    try:
        k = int(top_k)
    except (TypeError, ValueError):
        k = 5
    k = max(1, min(k, 20))
    arguments: dict[str, Any] = {
        "query": query,
        "top_k": k,
        "search_scope": "both",
    }
    if rag_group and str(rag_group).strip():
        arguments["rag_group"] = str(rag_group).strip()
    try:
        body = _http_json(
            url,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": MCP_TOOLS_CALL,
                "params": {
                    "name": "retrieve",
                    "arguments": arguments,
                },
            },
            timeout=50.0,
        )
    except (json.JSONDecodeError, OSError) as exc:
        return [
            {
                "text": f"RAG backend unreachable ({url}): {exc}",
                "score": 0.0,
                "source_document": "amazon-quick-mcp-error",
                "metadata": {"rag_source": "mcp", "mode": "error"},
            }
        ]
    if body.get("error"):
        err = body["error"]
        return [
            {
                "text": f"RAG MCP error: {err}",
                "score": 0.0,
                "source_document": "amazon-quick-mcp-error",
                "metadata": {"rag_source": "mcp", "mode": "error"},
            }
        ]
    chunks = _chunks_from_mcp_result(body)
    if chunks:
        return chunks
    return [
        {
            "text": f"ไม่พบชิ้นความรู้ในคลังสำหรับคำถาม: {query[:120]}",
            "score": 0.0,
            "source_document": "amazon-quick-mcp-empty",
            "metadata": {"rag_source": "mcp", "mode": "empty"},
        }
    ]


def fetch_list_rag_groups() -> dict[str, Any]:
    """Proxy list_rag_groups to mcp-rag when configured."""
    url = rag_mcp_url()
    if not url:
        return {
            "default_group": "procurement-th",
            "bucket": "",
            "groups": [
                {
                    "id": "procurement-th",
                    "name": "จัดซื้อจัดจ้าง (คลังหลัก)",
                    "description": "stub offline",
                    "vector_index": "procurement-th-embed4-v1",
                    "prefix": "rags/procurement-th/",
                }
            ],
            "mode": "stub",
        }
    try:
        body = _http_json(
            url,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": MCP_TOOLS_CALL,
                "params": {"name": "list_rag_groups", "arguments": {}},
            },
            timeout=20.0,
        )
    except (json.JSONDecodeError, OSError) as exc:
        return {"error": str(exc), "groups": [], "mode": "error"}
    if body.get("error"):
        return {"error": body["error"], "groups": [], "mode": "error"}
    chunks_text = ""
    result = body.get("result") or {}
    content = result.get("content") if isinstance(result, dict) else None
    if isinstance(content, list) and content:
        chunks_text = str((content[0] or {}).get("text") or "")
    try:
        parsed = json.loads(chunks_text) if chunks_text else {}
    except json.JSONDecodeError:
        parsed = {"raw": chunks_text}
    if isinstance(parsed, dict):
        parsed.setdefault("mode", "live")
        return parsed
    return {"groups": [], "mode": "live", "raw": chunks_text}


def retrieve_payload(
    query: str, top_k: int = 5, rag_group: str | None = None
) -> dict[str, Any]:
    """Flat OpenAPI object (no arrays): best snippet from real RAG or stub."""
    chunks = fetch_rag_chunks(query, top_k=top_k, rag_group=rag_group)
    first = chunks[0]
    meta = first.get("metadata") if isinstance(first.get("metadata"), dict) else {}
    rag_source = str(meta.get("rag_source") or "mcp")
    return {
        "text": str(first.get("text") or ""),
        "score": float(first.get("score") or 0.0),
        "source_document": str(first.get("source_document") or ""),
        "rag_source": rag_source,
        "rag_group": str(rag_group or meta.get("rag_group") or ""),
    }


def rag_backend_status() -> dict[str, Any]:
    url = rag_mcp_url()
    if not url:
        return {"mode": "stub", "rag_url": "", "reachable": False}
    health_url = url.rstrip("/")
    if health_url.endswith("/mcp"):
        health_url = health_url[: -len("/mcp")] + _HEALTH_PATH
    elif "/" in health_url:
        health_url = health_url.rsplit("/", 1)[0] + _HEALTH_PATH
    try:
        with urllib.request.urlopen(health_url, timeout=3) as resp:
            raw = resp.read().decode("utf-8")
        payload = json.loads(raw) if raw else {}
        ok = isinstance(payload, dict) and payload.get("status") == "ok"
        return {
            "mode": "live",
            "rag_url": url,
            "reachable": ok,
            "service": payload.get("service") if isinstance(payload, dict) else None,
        }
    except (json.JSONDecodeError, OSError) as exc:
        return {
            "mode": "live",
            "rag_url": url,
            "reachable": False,
            "error": str(exc),
        }


def _text_result(req_id: Any, text: str) -> dict[str, Any]:
    return _rpc_result(req_id, {"content": [{"type": "text", "text": text}]})


def _initialize_result(req_id: Any) -> dict[str, Any]:
    return _rpc_result(
        req_id,
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "tor-amazon-quick", "version": SERVER_VERSION},
        },
    )


def _tools_list_result(req_id: Any) -> dict[str, Any]:
    return _rpc_result(req_id, {"tools": TOOLS})


def _call_tool(req_id: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "ping":
        return _text_result(req_id, "pong")
    if name == "get_health":
        status = {
            "status": "ok",
            "service": "tor-amazon-quick",
            "version": SERVER_VERSION,
            "rag": rag_backend_status(),
        }
        return _text_result(req_id, json.dumps(status, ensure_ascii=False))
    if name == "list_rag_groups":
        return _text_result(
            req_id, json.dumps(fetch_list_rag_groups(), ensure_ascii=False)
        )
    if name != "retrieve":
        return _rpc_error(req_id, -32601, "unknown tool")
    try:
        top_k = int(args.get("top_k") or 5)
    except (TypeError, ValueError):
        top_k = 5
    rag_group = str(args.get("rag_group") or "").strip() or None
    chunks = fetch_rag_chunks(
        str(args.get("query") or ""), top_k=top_k, rag_group=rag_group
    )
    body = {
        "chunks": chunks,
        "mode": "live" if rag_mcp_url() else "stub",
        "rag_group": rag_group or "",
    }
    return _text_result(req_id, json.dumps(body, ensure_ascii=False))


def dispatch_rpc(payload: dict[str, Any]) -> tuple[int, dict[str, Any] | None]:
    req_id = payload.get("id")
    method = str(payload.get("method") or "")
    if method == "notifications/initialized":
        return 204, None
    if method == "initialize":
        return 200, _initialize_result(req_id)
    if method == "tools/list":
        return 200, _tools_list_result(req_id)
    if method != MCP_TOOLS_CALL:
        return 200, _rpc_error(req_id, -32601, "method not found")
    params = payload.get("params") or {}
    args = params.get("arguments") or {}
    if not isinstance(args, dict):
        args = {}
    return 200, _call_tool(req_id, str(params.get("name") or ""), args)


def required_is_draft7(tool: dict[str, Any]) -> bool:
    schema = tool.get("inputSchema") or {}
    required = schema.get("required")
    return isinstance(required, list)


def _parse_top_k(payload: Any, default: int = 5) -> int:
    if not isinstance(payload, dict):
        return default
    try:
        return int(payload.get("top_k") or default)
    except (TypeError, ValueError):
        return default


def _read_json_body(handler: _RequestHandler) -> Any:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        return json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


class Handler(_RequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path not in _HEALTH_PATHS:
            self._send(404, {"error": "not found"})
            return
        payload = {
            "status": "ok",
            "service": "tor-amazon-quick",
            "version": SERVER_VERSION,
            "rag": rag_backend_status(),
        }
        self._send(200, payload)

    def _handle_retrieve(self, payload: Any) -> None:
        query = str(payload.get("query") or "") if isinstance(payload, dict) else ""
        rag_group = None
        if isinstance(payload, dict):
            rag_group = str(payload.get("rag_group") or "").strip() or None
        self._send(
            200,
            retrieve_payload(query, top_k=_parse_top_k(payload), rag_group=rag_group),
        )

    def _handle_rpc(self, payload: Any) -> None:
        if not isinstance(payload, dict):
            self._send(400, _rpc_error(None, -32600, "invalid request"))
            return
        status, body = dispatch_rpc(payload)
        if body is None:
            self.send_response(status)
            self.end_headers()
            return
        self._send(status, body)

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path in _POST_AUTH_PATHS and not request_authorized(self.headers):
            self._send(401, {"error": "unauthorized"})
            return
        payload = _read_json_body(self)
        if path == "/retrieve":
            self._handle_retrieve(payload)
            return
        if path not in _MCP_PATHS:
            self._send(404, {"error": "not found"})
            return
        self._handle_rpc(payload)

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", _JSON)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _serve() -> None:
    server = _ThreadingServer((HOST, PORT), Handler)
    print(
        f"Amazon Quick MCP listening on {HOST}:{PORT} "
        f"rag={rag_mcp_url() or 'stub'}",
        flush=True,
    )
    run = getattr(server, "serve_forever")
    run()


if __name__ == "__main__":
    _serve()
