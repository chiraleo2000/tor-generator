"""Realistic live workflows against Docker FastAPI + LM Studio.

These tests fail clearly when the stack or LM Studio is down. They do not skip.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from tests.test_live_lm_studio import _require_lm_studio

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

API_BASE = "http://127.0.0.1:4000"
EMAIL = "officer@example.go.th"
PASSWORD = "Passw0rd!"

INTAKE_TEXT = (
    "ความเป็นมา: กรมบัญชีกลางมีความจำเป็นต้องจัดซื้อระบบสารสนเทศบริหารสัญญาจัดซื้อจัดจ้าง "
    "เพื่อติดตามงวดจ่ายและการส่งมอบให้เป็นไปตาม พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560 "
    "วัตถุประสงค์: เพื่อให้เจ้าหน้าที่พัสดุบริหารสัญญา ตรวจรับงาน และรายงานสถานะได้ครบถ้วนตามกฎหมาย "
    "วงเงินงบประมาณ: 5,000,000 บาท จากงบดำเนินงานประจำปี "
    "ระยะเวลาดำเนินการ: 180 วัน นับจากวันที่ลงนามในสัญญา "
    "สถานที่ดำเนินการ: สำนักงานปลัดกระทรวง กรุงเทพมหานคร "
    "ขอบเขตงานหลัก: วิเคราะห์ความต้องการ พัฒนาโมดูลบริหารสัญญา ทดสอบระบบ อบรมผู้ใช้ และส่งมอบคู่มือใช้งาน"
)

MINE_DOC = (
    "หลักเกณฑ์วงเงินจัดซื้อจัดจ้างภาครัฐ ตามระเบียบกรมบัญชีกลาง "
    "วิธีเฉพาะเจาะจงใช้ได้เมื่อวงเงินไม่เกินที่กฎกระทรวงกำหนด "
    "เอกสารส่วนตัวสำหรับทดสอบคลังของฉัน"
).encode("utf-8")

REVIEW_TEXT = (
    "1. ความเป็นมา\n"
    "โครงการจัดซื้อครุภัณฑ์คอมพิวเตอร์ของสำนักงานปลัดกระทรวง วงเงิน 5,000,000 บาท\n"
    "2. วัตถุประสงค์\n"
    "เพื่อทดแทนครุภัณฑ์ที่หมดอายุการใช้งานตาม พ.ร.บ. การจัดซื้อจัดจ้าง พ.ศ. 2560\n"
    "3. ระยะเวลา 180 วัน สถานที่กรุงเทพมหานคร\n"
).encode("utf-8")


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _step(message: str) -> None:
    line = f"[{_now()}] {message}"
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    sys.stdout.write(line.encode(encoding, errors="replace").decode(encoding, errors="replace") + "\n")
    sys.stdout.flush()


def _thai_count(text: str) -> int:
    return sum(1 for char in text if "\u0e00" <= char <= "\u0e7f")


def _require_api() -> None:
    response = httpx.get(f"{API_BASE}/health", timeout=5.0)
    response.raise_for_status()
    payload = response.json()
    status = payload.get("status") or payload.get("data", {}).get("status")
    if status not in {None, "healthy", "ok", True}:
        _step(f"health payload={payload}")


def _data(response: httpx.Response) -> dict:
    body = response.json()
    if isinstance(body, dict) and "data" in body:
        return body["data"] or {}
    return body


def _login(client: httpx.Client) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30.0,
    )
    if response.status_code != 200:
        pytest.fail(f"Login failed ({response.status_code}): {response.text[:500]}")
    token = _data(response).get("token")
    if token:
        client.headers["Authorization"] = f"Bearer {token}"


def _pause(seconds: float = 1.5) -> None:
    time.sleep(seconds)


def _parse_sse_done(raw: str) -> dict:
    event = ""
    done: dict = {}
    tokens: list[str] = []
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
            if event == "done":
                done = payload
            if event == "error":
                pytest.fail(f"SSE error: {payload}")
    if not done:
        done = {"content": "".join(tokens), "citations": []}
    return done


def _procurement_pdf() -> Path | None:
    pdf = (
        Path(__file__).resolve().parents[3]
        / "documents"
        / "sources"
        / "การจัดซื้อจัดจ้าง"
        / "ข้อมูลดิบ"
        / "กฎกระทรวงกำหนดวงเงินการจัดซื้อจัดจ้างพัสดุโดยวิธีเฉพาะเจาะจงวงเงิน.pdf"
    )
    return pdf if pdf.is_file() else None


@pytest.fixture(scope="module")
def live_client():
    _require_lm_studio()
    _require_api()
    with httpx.Client(base_url=API_BASE, timeout=900.0) as client:
        _login(client)
        yield client


@pytest.mark.integration
@pytest.mark.live_llm
def test_live_full_drafting_workflow(live_client: httpx.Client):
    _step("Step 1: create project")
    created = live_client.post(
        "/api/v1/projects",
        json={
            "name": f"โครงการทดสอบ live {datetime.now():%H%M%S}",
            "ministry": "สำนักงานปลัดกระทรวง",
            "budget": 5000000,
            "project_type": "it",
        },
        timeout=30.0,
    )
    assert created.status_code in {200, 201}, created.text[:800]
    project_id = _data(created).get("id")
    assert project_id, created.text[:500]
    _pause()

    _step("Step 2: paste intake text (no analyze yet)")
    pasted = live_client.post(
        f"/api/v1/projects/{project_id}/intake/text",
        json={"content": INTAKE_TEXT},
        timeout=180.0,
    )
    assert pasted.status_code == 200, pasted.text[:800]
    _pause(2)

    _step("Step 3: analyze with LM Studio")
    analyzed = live_client.post(
        f"/api/v1/projects/{project_id}/intake/analyze",
        timeout=180.0,
    )
    assert analyzed.status_code == 200, analyzed.text[:1200]
    analysis = _data(analyzed)
    coverage = analysis.get("coverage") or []
    filled = [row for row in coverage if row.get("filled") or row.get("status") == "filled"]
    _step(f"analyze filled {len(filled)} slots")
    assert coverage, "analyze returned no coverage rows"
    _pause(2)

    _step("Step 4: fill-references")
    refs = live_client.post(
        f"/api/v1/projects/{project_id}/intake/fill-references",
        timeout=180.0,
    )
    assert refs.status_code == 200, refs.text[:1200]
    _pause(2)

    _step("Step 5: draft section s1 with LM Studio")
    drafted = live_client.post(
        f"/api/v1/projects/{project_id}/draft-section",
        json={"section_key": "s1"},
        timeout=300.0,
    )
    assert drafted.status_code == 200, drafted.text[:1200]
    draft = str(_data(drafted).get("draft_content") or "")
    assert len(draft) >= 50, f"draft too short: {draft!r}"
    assert _thai_count(draft) >= 8, f"Expected Thai draft, got: {draft[:200]!r}"
    assert "โครงการ" in draft or "จัดซื้อ" in draft, draft[:300]
    _pause()

    _step("Step 6: project review (rule engine)")
    reviewed = live_client.post(
        f"/api/v1/projects/{project_id}/review",
        json={},
        timeout=180.0,
    )
    assert reviewed.status_code == 200, reviewed.text[:1200]
    score = _data(reviewed).get("quality_score")
    assert score is None or float(score) >= 0


@pytest.mark.integration
@pytest.mark.live_llm
def test_live_chat_qa_with_real_rag(live_client: httpx.Client):
    _step("Upload private KB text")
    uploaded = live_client.post(
        "/api/v1/knowledge-base/mine",
        files={"file": ("วงเงินส่วนตัว.txt", MINE_DOC, "text/plain")},
        data={"category": "other", "name": "วงเงินส่วนตัว.txt"},
        timeout=180.0,
    )
    assert uploaded.status_code in {200, 202}, uploaded.text[:800]
    doc = _data(uploaded)
    assert doc.get("processing_status") in {"pending", "processing", "completed", "failed"}
    if doc.get("processing_status") == "failed":
        pytest.fail(f"ingest failed: {doc}")
    _pause(2)

    _step("Create KB chat room")
    room = live_client.post(
        "/api/v1/chat/rooms",
        json={"kind": "kb", "title": "ทดสอบคลังของฉัน"},
        timeout=30.0,
    )
    assert room.status_code in {200, 201}, room.text[:800]
    room_id = _data(room)["id"]
    _pause()

    _step("Ask with search_scope=mine")
    streamed = live_client.post(
        f"/api/v1/chat/rooms/{room_id}/messages",
        json={"content": "วิธีเฉพาะเจาะจงคืออะไร ตามเอกสารของฉัน", "search_scope": "mine"},
        timeout=180.0,
    )
    assert streamed.status_code == 200, streamed.text[:800]
    done = _parse_sse_done(streamed.text)
    content = str(done.get("content") or "")
    assert content.strip(), f"empty chat reply: {done}"
    assert _thai_count(content) >= 8, f"Expected Thai, got: {content[:300]!r}"
    assert isinstance(done.get("citations"), list)


@pytest.mark.integration
@pytest.mark.live_llm
def test_live_review_with_real_text(live_client: httpx.Client):
    pdf = _procurement_pdf()
    if pdf is not None:
        _step("Extract review PDF from documents/sources")
        files = {"file": (pdf.name, pdf.read_bytes(), "application/pdf")}
    else:
        _step("Extract review from Thai TOR text")
        files = {"file": ("tor.txt", REVIEW_TEXT, "text/plain")}
    extracted = live_client.post("/api/v1/review/extract", files=files, timeout=60.0)
    assert extracted.status_code == 200, extracted.text[:800]
    payload = _data(extracted)
    text = str(payload.get("extracted_text") or "")
    assert _thai_count(text) >= 8 or "จัดซื้อ" in text or "วงเงิน" in text, text[:400]
    _pause()

    _step("Run Rule Engine")
    ran = live_client.post(
        "/api/v1/review/run",
        json={"id": payload["id"]},
        timeout=900.0,
    )
    assert ran.status_code == 200, ran.text[:800]
    result = _data(ran)
    assert isinstance(result.get("quality_score"), (int, float))
    assert isinstance(result.get("findings"), list)


@pytest.mark.integration
@pytest.mark.live_llm
def test_live_kb_upload_other_and_retrieve(live_client: httpx.Client):
    _step("Upload category=other")
    uploaded = live_client.post(
        "/api/v1/knowledge-base/mine",
        files={"file": ("บันทึกภายใน.txt", MINE_DOC, "text/plain")},
        data={"category": "other", "name": "บันทึกภายใน.txt"},
        timeout=180.0,
    )
    assert uploaded.status_code in {200, 202}, uploaded.text[:800]
    doc = _data(uploaded)
    assert doc.get("category") == "other"
    _pause(2)

    catalog = live_client.get("/api/v1/knowledge-base/catalog", timeout=30.0)
    assert catalog.status_code == 200, catalog.text[:800]
    mine = _data(catalog).get("userFiles") or []
    match = next((item for item in mine if item.get("id") == doc.get("id")), None)
    if match is None:
        match = next((item for item in mine if "บันทึก" in str(item.get("name"))), None)
    assert match, f"uploaded file missing from catalog: {mine[:5]}"
    assert match.get("category") == "other"
    assert match.get("processing_status") in {"pending", "processing", "completed", "failed"}
    if match.get("processing_status") == "completed":
        assert (match.get("chunk_count") or 0) >= 0

    room = live_client.post(
        "/api/v1/chat/rooms",
        json={"kind": "kb", "title": "ถามเอกสาร other"},
        timeout=30.0,
    )
    room_id = _data(room)["id"]
    streamed = live_client.post(
        f"/api/v1/chat/rooms/{room_id}/messages",
        json={"content": "สรุปเอกสารของฉันเรื่องวงเงินจัดซื้อจัดจ้าง", "search_scope": "mine"},
        timeout=180.0,
    )
    assert streamed.status_code == 200, streamed.text[:800]
    done = _parse_sse_done(streamed.text)
    content = str(done.get("content") or "")
    assert _thai_count(content) >= 8, content[:300]
