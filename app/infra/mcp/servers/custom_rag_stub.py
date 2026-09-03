#!/usr/bin/env python3
"""HTTP stub for Custom RAG POST /api/search and /v1/retrieve (local DEV only)."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler as _RequestHandler
from http.server import ThreadingHTTPServer as _ThreadingServer
from typing import Any

HOST = os.environ.get("CUSTOM_RAG_STUB_HOST", "127.0.0.1")
PORT = int(os.environ.get("CUSTOM_RAG_STUB_PORT", "8089"))
_JSON = "application/json"


def _search_result(query: str) -> dict[str, Any]:
    return {
        "chunks": [
            {
                "id": "custom-rag-stub-1",
                "text": f"ชิ้นจำลองจาก Custom RAG stub สำหรับคำถาม: {query[:120]}",
                "score": 0.62,
                "source_document": "custom-rag-stub",
                "title": "custom-rag-stub",
                "metadata": {"rag_source": "custom_rag"},
            }
        ]
    }


class Handler(_RequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") not in {"/api/search", "/v1/retrieve", "/search"}:
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            body = {}
        query = str(body.get("query") or "") if isinstance(body, dict) else ""
        self._send(200, _search_result(query))

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", _JSON)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _serve_stub() -> None:
    server = _ThreadingServer((HOST, PORT), Handler)
    print(f"Custom RAG stub listening on {HOST}:{PORT}", flush=True)
    run = getattr(server, "serve_forever")
    run()


if __name__ == "__main__":
    _serve_stub()
