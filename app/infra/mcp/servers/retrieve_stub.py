#!/usr/bin/env python3
"""HTTP JSON-RPC stub for MCP-style tools/call retrieve (local DEV only)."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8765


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send(400, {"jsonrpc": "2.0", "error": {"code": -32700, "message": "parse error"}, "id": None})
            return
        req_id = payload.get("id")
        method = payload.get("method")
        if method != "tools/call":
            self._send(
                200,
                {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "method not found"}},
            )
            return
        params = payload.get("params") or {}
        tool = str(params.get("name") or "")
        args = params.get("arguments") or {}
        query = str(args.get("query") or "")
        if tool != "retrieve":
            self._send(
                200,
                {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "unknown tool"}},
            )
            return
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
        self._send(
            200,
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": json.dumps(body, ensure_ascii=False)}]},
            },
        )

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"MCP retrieve stub http://{HOST}:{PORT}", flush=True)  # NOSONAR python:S5332
    server.serve_forever()
