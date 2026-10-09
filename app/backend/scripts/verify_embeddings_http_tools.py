"""HTTP smoke: admin embedding probe + KB chat RAG (live EmbeddingGemma 2)."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


BASE = "http://localhost:4000/api/v1"


def _req(method: str, path: str, token: str | None = None, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} -> {exc.code}: {detail}") from exc


def _out(message: str) -> None:
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(
            message.encode(encoding, errors="replace").decode(encoding, errors="replace"),
            flush=True,
        )


def main() -> None:
    results: list[bool] = []

    admin = _req(
        "POST",
        "/auth/login",
        body={"email": "admin@example.go.th", "password": "Passw0rd!"},
    )
    admin_token = (admin.get("data") or {}).get("token") or admin.get("token")
    ok = bool(admin_token)
    _out(("PASS" if ok else "FAIL") + "  auth.admin_login")
    results.append(ok)

    probe = _req(
        "POST",
        "/admin/ai-settings/test",
        token=admin_token,
        body={
            "deployment_mode": "on_prem",
            "llm_provider": "lm_studio",
            "embedding_provider": "local",
            "local_embedding_server": "lm_studio",
            "lm_studio_base_url": "http://host.docker.internal:1234/v1",
        },
    )
    msg = str((probe.get("data") or {}).get("message") or "")
    ok = "embeddings" in msg
    _out(("PASS" if ok else "FAIL") + f"  admin.ai_settings.test — {msg}")
    results.append(ok)

    officer = _req(
        "POST",
        "/auth/login",
        body={"email": "officer@example.go.th", "password": "Passw0rd!"},
    )
    officer_token = (officer.get("data") or {}).get("token") or officer.get("token")
    ok = bool(officer_token)
    _out(("PASS" if ok else "FAIL") + "  auth.officer_login")
    results.append(ok)

    session = _req("POST", "/kb-chat/sessions", token=officer_token)
    session_id = (session.get("data") or {}).get("session_id")
    answer = _req(
        "POST",
        f"/kb-chat/sessions/{session_id}/message",
        token=officer_token,
        body={
            "message": "วงเงินจัดซื้อโดยวิธีเฉพาะเจาะจงตามระเบียบพัสดุ 2560 เป็นเท่าไร",
        },
    )
    payload = answer.get("data") or {}
    text = str(payload.get("answer") or "")
    no_results = bool(payload.get("no_results"))
    cites = payload.get("citations") or []
    ok = (not no_results) and len(text) > 20
    preview = text[:120].replace("\n", " ")
    _out(
        ("PASS" if ok else "FAIL")
        + f"  kb_chat.message — no_results={no_results} cites={len(cites)} answer={preview}"
    )
    results.append(ok)

    kb = _req("GET", "/knowledge-base", token=officer_token)
    data = kb.get("data") or {}
    docs = data.get("documents") or data.get("items") or data
    count = len(docs) if isinstance(docs, list) else 0
    ok = count > 0
    _out(("PASS" if ok else "FAIL") + f"  knowledge_base.list — docs={count}")
    results.append(ok)

    passed = sum(1 for item in results if item)
    total = len(results)
    _out(f"\nHTTP_SUMMARY {passed}/{total}")
    if passed != total:
        raise SystemExit(1)
    _out("HTTP_EMBEDDING_TOOLS_OK")


if __name__ == "__main__":
    main()
