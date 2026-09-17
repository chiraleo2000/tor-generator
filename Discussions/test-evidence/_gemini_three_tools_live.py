"""Live Gemini hybrid check: KB Q&A then standalone review. Draft is a separate script."""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

API = "http://127.0.0.1:4000"
EMAIL = "officer@example.go.th"
PASSWORD = "Passw0rd!"
OUT = Path(__file__).resolve().parent / "_gemini-three-tools.json"
GOLD = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "backend"
    / "tests"
    / "fixtures"
    / "hire_develop_gold_pack.txt"
)
STUBS = ("ชิ้นจำลอง", "custom-rag-stub", "mcp-retrieve-stub")


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def step(msg: str) -> None:
    print(f"[{_now()}] {msg}", flush=True)


def data(response: httpx.Response) -> dict:
    body = response.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"] or {}
    return body if isinstance(body, dict) else {}


def thai_count(text: str) -> int:
    return sum(1 for ch in text if "\u0e00" <= ch <= "\u0e7f")


def parse_sse(raw: str) -> dict:
    event = ""
    done: dict = {}
    tokens: list[str] = []
    errors: list[dict] = []
    citations: list = []
    for line in raw.splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:") and event:
            try:
                payload = json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
            if event == "token":
                tokens.append(str(payload.get("text") or ""))
            elif event == "citation":
                citations.append(payload)
            elif event == "done":
                done = payload
            elif event == "error":
                errors.append(payload)
    if not done:
        done = {"content": "".join(tokens), "citations": citations}
    if citations and not done.get("citations"):
        done["citations"] = citations
    if errors:
        done["errors"] = errors
    return done


def login(client: httpx.Client) -> None:
    response = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
    response.raise_for_status()
    token = data(response).get("token")
    if not token:
        raise SystemExit("login missing token")
    client.headers["Authorization"] = f"Bearer {token}"


def test_chat(client: httpx.Client) -> dict:
    room = client.post(
        "/api/v1/chat/rooms",
        json={"kind": "kb", "title": "ทดสอบ Gemini ถาม-ตอบ"},
    )
    room.raise_for_status()
    room_id = data(room)["id"]
    question = (
        "ถามจาก พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560 "
        "ผู้เสนอราคาต้องมีคุณสมบัติอะไรบ้าง อ้างมาตราให้ชัด"
    )
    step(f"chat room {room_id}")
    streamed = client.post(
        f"/api/v1/chat/rooms/{room_id}/messages",
        json={"content": question, "search_scope": "both"},
        timeout=httpx.Timeout(300.0, connect=20.0),
    )
    if streamed.status_code != 200:
        return {
            "ok": False,
            "status": streamed.status_code,
            "body": streamed.text[:1200],
        }
    done = parse_sse(streamed.text)
    content = str(done.get("content") or "")
    cites = done.get("citations") or []
    blob = content + json.dumps(cites, ensure_ascii=False)
    stub = [s for s in STUBS if s in blob]
    ok = (
        streamed.status_code == 200
        and len(content.strip()) >= 80
        and thai_count(content) >= 40
        and not stub
        and not done.get("errors")
        and isinstance(cites, list)
        and len(cites) >= 1
        and "สรุปคำตอบ" in content
    )
    step(f"chat chars={len(content)} thai={thai_count(content)} cites={len(cites)} ok={ok}")
    return {
        "ok": ok,
        "status": streamed.status_code,
        "chars": len(content),
        "thai": thai_count(content),
        "citations": len(cites),
        "has_summary": "สรุปคำตอบ" in content,
        "has_table": "|" in content,
        "has_caution": "ข้อควรระวัง" in content,
        "stub": stub,
        "errors": done.get("errors"),
        "preview": content[:600],
        "cite_preview": cites[:3],
    }


def test_review(client: httpx.Client) -> dict:
    pack = GOLD.read_bytes() if GOLD.is_file() else (
        "1. ความเป็นมา\nโครงการจัดซื้อครุภัณฑ์คอมพิวเตอร์ของสำนักงานปลัดกระทรวง วงเงิน 5,000,000 บาท\n"
        "2. วัตถุประสงค์ เพื่อทดแทนครุภัณฑ์ตาม พ.ร.บ. การจัดซื้อจัดจ้าง พ.ศ. 2560\n"
        "ระยะเวลา 180 วัน สถานที่กรุงเทพมหานคร\n"
    ).encode("utf-8")
    extracted = client.post(
        "/api/v1/review/extract",
        files={"file": ("gold-pack.txt", pack, "text/plain")},
        timeout=120.0,
    )
    if extracted.status_code != 200:
        return {"ok": False, "stage": "extract", "status": extracted.status_code, "body": extracted.text[:800]}
    payload = data(extracted)
    job_id = payload.get("id")
    text = str(payload.get("extracted_text") or "")
    step(f"review extract id={job_id} chars={len(text)}")
    ran = client.post(
        "/api/v1/review/run",
        json={"id": job_id},
        timeout=httpx.Timeout(900.0, connect=20.0),
    )
    if ran.status_code != 200:
        return {
            "ok": False,
            "stage": "run",
            "status": ran.status_code,
            "body": ran.text[:1200],
            "extract_chars": len(text),
        }
    result = data(ran)
    score = result.get("quality_score")
    findings = result.get("findings") or []
    dump = json.dumps(result, ensure_ascii=False)
    stub = [s for s in STUBS if s in dump]
    ok = (
        isinstance(score, (int, float))
        and float(score) >= 0
        and isinstance(findings, list)
        and not stub
    )
    step(f"review score={score} findings={len(findings)} ok={ok}")
    return {
        "ok": ok,
        "id": job_id,
        "score": score,
        "findings": len(findings),
        "is_valid": result.get("is_valid"),
        "extract_chars": len(text),
        "stub": stub,
        "assessment_preview": str(result.get("assessment") or result.get("summary") or "")[:400],
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    report: dict = {"started": datetime.now().isoformat(timespec="seconds")}
    with httpx.Client(base_url=API, timeout=httpx.Timeout(900.0, connect=20.0)) as client:
        health = client.get("/health", timeout=10.0)
        report["health"] = health.status_code
        if health.status_code != 200:
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            return 1
        login(client)
        step("login ok")
        report["chat"] = test_chat(client)
        report["review"] = test_review(client)
    report["ok"] = bool(report["chat"].get("ok") and report["review"].get("ok"))
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    step(f"wrote {OUT} ok={report['ok']}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
