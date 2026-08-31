#!/usr/bin/env python3
"""HTTP JSON-RPC stub for MCP-style tools/call retrieve (local DEV only)."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # NOSONAR python:S5332
from typing import Any

HOST = "127.0.0.1"
PORT = 8765


def _rpc_error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


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
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"content": [{"type": "text", "text": json.dumps(body, ensure_ascii=False)}]},
    }


class Handler(BaseHTTPRequestHandler):  # NOSONAR python:S5332 — local dev stub
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send(400, _rpc_error(None, -32700, "parse error"))
            return
        req_id = payload.get("id")
        if payload.get("method") != "tools/call":
            self._send(200, _rpc_error(req_id, -32601, "method not found"))
            return
        params = payload.get("params") or {}
        args = params.get("arguments") or {}
        if str(params.get("name") or "") != "retrieve":
            self._send(200, _rpc_error(req_id, -32601, "unknown tool"))
            return
        self._send(200, _retrieve_result(req_id, str(args.get("query") or "")))

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _serve_stub() -> None:  # NOSONAR python:S5332 — local dev stub binds 127.0.0.1 only
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"MCP retrieve stub listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()  # NOSONAR python:S5332


if __name__ == "__main__":
    _serve_stub()
