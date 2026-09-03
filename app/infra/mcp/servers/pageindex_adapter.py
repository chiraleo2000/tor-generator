#!/usr/bin/env python3
"""Map POST /v1/retrieve to a PageIndex-style POST /api/search (local/dev)."""

from __future__ import annotations

import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler as _RequestHandler
from http.server import ThreadingHTTPServer as _ThreadingServer
from typing import Any

HOST = os.environ.get("PAGEINDEX_ADAPTER_HOST", "0.0.0.0")
PORT = int(os.environ.get("PAGEINDEX_ADAPTER_PORT", "8080"))
UPSTREAM = os.environ.get(
    "PAGEINDEX_SEARCH_URL", "http://pageindex:8000/api/search"
).rstrip("/")
_JSON = "application/json"


def _chunks_from_upstream(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    for key in ("chunks", "results", "items", "documents", "hits"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    nested = payload.get("data")
    if isinstance(nested, dict):
        return _chunks_from_upstream(nested)
    if isinstance(nested, list):
        return [item for item in nested if isinstance(item, dict)]
    return []


class Handler(_RequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") not in {"/v1/retrieve", "/api/search"}:
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send(400, {"chunks": []})
            return
        request = urllib.request.Request(
            UPSTREAM,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": _JSON, "Accept": _JSON},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                upstream = json.loads(response.read().decode("utf-8"))
        except (json.JSONDecodeError, OSError):
            self._send(200, {"chunks": []})
            return
        self._send(200, {"chunks": _chunks_from_upstream(upstream)})

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", _JSON)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _serve_stub() -> None:
    server = _ThreadingServer((HOST, PORT), Handler)
    print(f"PageIndex adapter listening on {HOST}:{PORT} -> {UPSTREAM}", flush=True)
    run = getattr(server, "serve_forever")
    run()


if __name__ == "__main__":
    _serve_stub()
