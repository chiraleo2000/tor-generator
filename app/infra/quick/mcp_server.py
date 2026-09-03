#!/usr/bin/env python3
"""Amazon Quick remote MCP + REST twin (JSON Schema Draft 7, no stdio).

Amazon Quick registers tools from tools/list. inputSchema.required must be an
array of property names (Draft 7), never a boolean on each property.
Tool calls time out at 60s on Quick — keep handlers local and fast.

Endpoints:
  GET  /health
  POST /retrieve     REST twin for OpenAPI (flat object, no arrays)
  POST /  and /mcp   JSON-RPC MCP (initialize, tools/list, tools/call)
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler as _RequestHandler
from http.server import ThreadingHTTPServer as _ThreadingServer
from typing import Any

HOST = os.environ.get("QUICK_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("QUICK_MCP_PORT", "8767"))
PROTOCOL_VERSION = "2024-11-05"

RETRIEVE_TOOL: dict[str, Any] = {
    "name": "retrieve",
    "description": (
        "Search Thai public-procurement knowledge for TOR drafting. "
        "Pass a natural-language query. Returns one grounded snippet."
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

TOOLS = [RETRIEVE_TOOL, PING_TOOL, HEALTH_TOOL]


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


def retrieve_payload(query: str) -> dict[str, Any]:
    text = f"ชิ้นจำลองจาก Amazon Quick MCP สำหรับคำถาม: {query[:120]}"
    return {
        "text": text,
        "score": 0.62,
        "source_document": "amazon-quick-mcp",
        "rag_source": "mcp",
    }


def _text_result(req_id: Any, text: str) -> dict[str, Any]:
    return _rpc_result(req_id, {"content": [{"type": "text", "text": text}]})


def _initialize_result(req_id: Any) -> dict[str, Any]:
    return _rpc_result(
        req_id,
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "tor-amazon-quick", "version": "0.3.0"},
        },
    )


def _tools_list_result(req_id: Any) -> dict[str, Any]:
    return _rpc_result(req_id, {"tools": TOOLS})


def _call_tool(req_id: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "ping":
        return _text_result(req_id, "pong")
    if name == "get_health":
        return _text_result(req_id, json.dumps({"status": "ok"}, ensure_ascii=False))
    if name != "retrieve":
        return _rpc_error(req_id, -32601, "unknown tool")
    snippet = retrieve_payload(str(args.get("query") or ""))
    body = {
        "chunks": [
            {
                "text": snippet["text"],
                "score": snippet["score"],
                "source_document": snippet["source_document"],
                "metadata": {"rag_source": "mcp"},
            }
        ]
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
    if method != "tools/call":
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


class Handler(_RequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path not in {"/", "/health"}:
            self._send(404, {"error": "not found"})
            return
        self._send(200, {"status": "ok", "service": "tor-amazon-quick"})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path in {"/", "/mcp", "/retrieve"} and not request_authorized(self.headers):
            self._send(401, {"error": "unauthorized"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            payload = {}
        if path == "/retrieve":
            query = str(payload.get("query") or "") if isinstance(payload, dict) else ""
            self._send(200, retrieve_payload(query))
            return
        if path not in {"/", "/mcp"}:
            self._send(404, {"error": "not found"})
            return
        if not isinstance(payload, dict):
            self._send(400, _rpc_error(None, -32600, "invalid request"))
            return
        status, body = dispatch_rpc(payload)
        if body is None:
            self.send_response(status)
            self.end_headers()
            return
        self._send(status, body)

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _serve() -> None:
    server = _ThreadingServer((HOST, PORT), Handler)
    print(f"Amazon Quick MCP listening on {HOST}:{PORT}", flush=True)
    run = getattr(server, "serve_forever")
    run()


if __name__ == "__main__":
    _serve()
