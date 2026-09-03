"""Amazon Quick MCP Draft 7 + OpenAPI connector (not QuickSight)."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

def _app_tree() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "infra" / "quick" / "mcp_server.py").is_file():
            return parent
    return here.parents[2]


REPO_APP = _app_tree()
STUB_PATH = REPO_APP / "infra" / "mcp" / "servers" / "retrieve_stub.py"
QUICK_PATH = REPO_APP / "infra" / "quick" / "mcp_server.py"
OPENAPI_PATH = REPO_APP / "infra" / "quick" / "openapi-tor.json"


def _load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _required_is_array(tool: dict[str, Any]) -> bool:
    required = (tool.get("inputSchema") or {}).get("required")
    return isinstance(required, list)


def test_retrieve_stub_tools_list_uses_draft7_required_array() -> None:
    stub = _load(STUB_PATH, "retrieve_stub_quick")
    status, body = stub.dispatch_rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert status == 200
    tools = body["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "retrieve"
    assert _required_is_array(tools[0])
    assert "query" in tools[0]["inputSchema"]["required"]
    props = tools[0]["inputSchema"]["properties"]
    assert "required" not in props["query"]


def test_retrieve_stub_initialize_and_retrieve() -> None:
    stub = _load(STUB_PATH, "retrieve_stub_init")
    _, init_body = stub.dispatch_rpc({"jsonrpc": "2.0", "id": 7, "method": "initialize"})
    assert init_body["result"]["protocolVersion"] == "2024-11-05"
    status, note = stub.dispatch_rpc({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert status == 204
    assert note is None
    _, call_body = stub.dispatch_rpc(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "retrieve", "arguments": {"query": "หลักประกันสัญญา"}},
        }
    )
    text = call_body["result"]["content"][0]["text"]
    assert "หลักประกันสัญญา" in text


def test_amazon_quick_tools_are_draft7_and_under_limit() -> None:
    quick = _load(QUICK_PATH, "amazon_quick_mcp")
    _, body = quick.dispatch_rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    tools = body["result"]["tools"]
    assert 1 <= len(tools) <= 100
    names = {tool["name"] for tool in tools}
    assert names == {"retrieve", "ping", "get_health"}
    for tool in tools:
        assert _required_is_array(tool)
        assert quick.required_is_draft7(tool)
        for prop in (tool["inputSchema"].get("properties") or {}).values():
            assert "required" not in prop


def test_amazon_quick_ping_and_rest_payload() -> None:
    quick = _load(QUICK_PATH, "amazon_quick_ping")
    _, ping_body = quick.dispatch_rpc(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "ping", "arguments": {}},
        }
    )
    assert ping_body["result"]["content"][0]["text"] == "pong"
    snippet = quick.retrieve_payload("วงเงินงบประมาณ")
    assert snippet["rag_source"] == "mcp"
    assert "วงเงินงบประมาณ" in snippet["text"]
    assert "chunks" not in snippet


def _schema_has_array(node: Any) -> bool:
    if isinstance(node, dict):
        if node.get("type") == "array":
            return True
        return any(_schema_has_array(value) for value in node.values())
    if isinstance(node, list):
        return any(_schema_has_array(item) for item in node)
    return False


def test_amazon_quick_openapi_has_no_array_schemas() -> None:
    spec = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    assert spec["openapi"].startswith("3.")
    assert "paths" in spec
    operations = 0
    for path_item in spec["paths"].values():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            operations += 1
            assert operation.get("operationId")
            assert operation.get("description")
            content = ((operation.get("requestBody") or {}).get("content")) or {}
            assert "application/xml" not in content
    assert 1 <= operations <= 100
    # OpenAPI "servers" is a document array; Amazon Quick forbids array *schemas*.
    for path_item in spec["paths"].values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            bodies = []
            request = operation.get("requestBody") or {}
            bodies.append(((request.get("content") or {}).get("application/json") or {}).get("schema"))
            for response in (operation.get("responses") or {}).values():
                bodies.append(
                    (((response.get("content") or {}).get("application/json") or {}).get("schema"))
                )
            for schema in bodies:
                assert not _schema_has_array(schema)


def test_amazon_quick_unknown_tool_and_draft7_required() -> None:
    quick = _load(QUICK_PATH, "amazon_quick_unknown")
    _, body = quick.dispatch_rpc(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {"name": "nope", "arguments": {}},
        }
    )
    assert body["error"]["code"] == -32601
    assert quick.required_is_draft7({"inputSchema": {"required": True}}) is False
    assert quick.required_is_draft7({"inputSchema": {"required": []}}) is True


def test_amazon_quick_auth_fail_safe(monkeypatch) -> None:
    quick = _load(QUICK_PATH, "amazon_quick_auth")

    class Headers(dict):
        def get(self, key, default=None):  # noqa: A003
            for stored, value in self.items():
                if str(stored).lower() == str(key).lower():
                    return value
            return default

    monkeypatch.setenv("QUICK_MCP_AUTH_VALUE", "")
    assert quick.request_authorized(Headers()) is True
    monkeypatch.setenv("QUICK_MCP_AUTH_VALUE", "secret-token")
    assert quick.request_authorized(Headers()) is False
    assert quick.request_authorized(Headers({"Authorization": "secret-token"})) is True


def test_amazon_quick_http_health_and_retrieve(monkeypatch) -> None:
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer

    monkeypatch.setenv("QUICK_MCP_AUTH_VALUE", "")
    quick = _load(QUICK_PATH, "amazon_quick_http")
    server = ThreadingHTTPServer(("127.0.0.1", 0), quick.Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        host, port = server.server_address
        health = urllib.request.urlopen(f"http://{host}:{port}/health", timeout=2)
        payload = json.loads(health.read().decode("utf-8"))
        assert payload["status"] == "ok"
        mcp_req = urllib.request.Request(
            f"http://{host}:{port}/mcp",
            data=json.dumps(
                {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        mcp_body = json.loads(
            urllib.request.urlopen(mcp_req, timeout=2).read().decode("utf-8")
        )
        assert mcp_body["result"]["protocolVersion"] == "2024-11-05"
        req = urllib.request.Request(
            f"http://{host}:{port}/retrieve",
            data=json.dumps({"query": "หลักประกัน"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        body = json.loads(urllib.request.urlopen(req, timeout=2).read().decode("utf-8"))
        assert "หลักประกัน" in body["text"]
        assert "chunks" not in body
        try:
            urllib.request.urlopen(f"http://{host}:{port}/missing", timeout=2)
            raise AssertionError("expected 404")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
    finally:
        server.shutdown()
        server.server_close()


def test_amazon_quick_http_rejects_missing_auth(monkeypatch) -> None:
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer

    monkeypatch.setenv("QUICK_MCP_AUTH_VALUE", "need-token")
    quick = _load(QUICK_PATH, "amazon_quick_http_auth")
    server = ThreadingHTTPServer(("127.0.0.1", 0), quick.Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        host, port = server.server_address
        req = urllib.request.Request(
            f"http://{host}:{port}/retrieve",
            data=json.dumps({"query": "x"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=2)
            raise AssertionError("expected 401")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
        health = urllib.request.urlopen(f"http://{host}:{port}/health", timeout=2)
        assert json.loads(health.read().decode("utf-8"))["status"] == "ok"
    finally:
        server.shutdown()
        server.server_close()

