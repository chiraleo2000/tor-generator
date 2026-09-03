#!/usr/bin/env python3
"""JSON-RPC MCP retrieve stub (local DEV). Supports Amazon Quick tools/list Draft 7."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler as _RequestHandler
from http.server import ThreadingHTTPServer as _ThreadingServer
from typing import Any

HOST = os.environ.get("MCP_STUB_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCP_STUB_PORT", "8765"))

PROTOCOL_VERSION = "2024-11-05"

RETRIEVE_TOOL: dict[str, Any] = {
    "name": "retrieve",
    "description": (
        "Retrieve Thai public-procurement knowledge snippets for a question. "
        "Use for TOR drafting, contract-guarantee, and พ.ร.บ. การจัดซื้อจัดจ้าง queries."
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
                "description": "Maximum snippets to return. Optional; the stub returns one.",
            },
        },
        "required": ["query"],
    },
}


def _rpc_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def _rpc_result(req_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _retrieve_result(req_id: Any, query: str) -> dict[str, Any]:
    body = {
        "chunks": [
            {
                "text": f"ชิ้นจำลองจาก MCP stub สำหรับคำถาม: {query[:120]}",
                "score": 0.5,
                "source_document": "mcp-retrieve-stub",
                "metadata": {"rag_source": "mcp"},
            }
        ]
    }
    return _rpc_result(
        req_id,
        {"content": [{"type": "text", "text": json.dumps(body, ensure_ascii=False)}]},
    )


def _initialize_result(req_id: Any) -> dict[str, Any]:
    return _rpc_result(
        req_id,
        {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "tor-mcp-retrieve-stub", "version": "0.3.0"},
        },
    )


def _tools_list_result(req_id: Any) -> dict[str, Any]:
    return _rpc_result(req_id, {"tools": [RETRIEVE_TOOL]})


def dispatch_rpc(payload: dict[str, Any]) -> tuple[int, dict[str, Any] | None]:
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
    if str(params.get("name") or "") != "retrieve":
        return 200, _rpc_error(req_id, -32601, "unknown tool")
    return 200, _retrieve_result(req_id, str(args.get("query") or ""))


class Handler(_RequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0].rstrip("/") not in {"", "/health"}:
            self._send(404, {"error": "not found"})
            return
        self._send(200, {"status": "ok", "service": "tor-mcp-retrieve-stub"})

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send(400, _rpc_error(None, -32700, "parse error"))
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


def _serve_stub() -> None:
    server = _ThreadingServer((HOST, PORT), Handler)
    print(f"MCP retrieve stub listening on {HOST}:{PORT}", flush=True)
    run = getattr(server, "serve_forever")
    run()


if __name__ == "__main__":
    _serve_stub()
