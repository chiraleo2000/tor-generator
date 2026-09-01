"""Live ECT AI Chatbot pack: full intake coverage, 13-section draft, TOR review.

Uses the officer's real TOR prose (tests/fixtures/ect_ai_chatbot_pack.txt)
against Docker FastAPI + LM Studio. Fails clearly when the stack is down.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx
import pytest

from app.services.tor_assemble import plain_tor_from_section_items
from tests.test_live_lm_studio import _require_lm_studio
from tests.test_live_realistic_workflow import (
    API_BASE,
    EMAIL,
    PASSWORD,
    _data,
    _login,
    _require_api,
    _step,
    _thai_count,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ECT_PACK = Path(__file__).with_name("fixtures").joinpath("ect_ai_chatbot_pack.txt")
FACT_KEYS = ("s1", "s2", "s5", "s6", "s7", "s4.1")
# Drafting 13 sections + s4.1–s4.14 on local Gemma can take well over an hour.
DRAFT_POLL_SEC = 20
DRAFT_DEADLINE_SEC = 14_400


def _pack() -> str:
    text = ECT_PACK.read_text(encoding="utf-8").strip()
    assert "ECT AI Chatbot" in text
    assert "15,000,000" in text
    return text


def _filled_rows(coverage: list[dict]) -> list[dict]:
    return [
        row
        for row in coverage
        if row.get("filled") or row.get("status") == "filled"
    ]


@pytest.fixture(scope="module")
def live_client():
    _require_lm_studio()
    _require_api()
    with httpx.Client(base_url=API_BASE, timeout=900.0) as client:
        _login(client)
        yield client


@pytest.fixture(scope="module")
def ect_project(live_client: httpx.Client) -> str:
    pack = _pack()
    _step("Create ECT project")
    created = live_client.post(
        "/api/v1/projects",
        json={
            "name": f"ECT AI Chatbot live {datetime.now():%H%M%S}",
            "ministry": "สำนักงาน กกต.",
            "budget": 15_000_000,
            "project_type": "it",
        },
        timeout=30.0,
    )
    assert created.status_code in {200, 201}, created.text[:800]
    project_id = _data(created)["id"]
    _step(f"project {project_id}")

    pasted = live_client.post(
        f"/api/v1/projects/{project_id}/intake/text",
        json={"content": pack},
        timeout=60.0,
    )
    assert pasted.status_code == 200, pasted.text[:800]

    uploaded = live_client.post(
        f"/api/v1/projects/{project_id}/intake/upload",
        files={"files": ("ect-ai-chatbot-tor.txt", pack.encode("utf-8"), "text/plain")},
        timeout=60.0,
    )
    assert uploaded.status_code == 200, uploaded.text[:800]

    analyzed = live_client.post(
        f"/api/v1/projects/{project_id}/intake/analyze",
        timeout=900.0,
    )
    assert analyzed.status_code == 200, analyzed.text[:1200]
    coverage = _data(analyzed).get("coverage") or []
    filled = _filled_rows(coverage)
    empty = [
        row.get("key")
        for row in coverage
        if not (row.get("filled") or row.get("status") == "filled")
    ]
    _step(f"analyze filled {len(filled)}/{len(coverage)} empty={empty}")
    assert coverage, "analyze returned no coverage"
    for key in FACT_KEYS:
        row = next((item for item in coverage if item.get("key") == key), None)
        assert row, f"missing coverage row {key}"
        assert row.get("status") == "filled", f"{key} not filled: {row}"
        assert str(row.get("preview") or "").strip(), f"{key} empty preview"
    assert len(filled) >= 20, f"expected broad slot coverage, got {len(filled)}"

    try:
        refs = live_client.post(
            f"/api/v1/projects/{project_id}/intake/fill-references",
            timeout=90.0,
        )
        keys = _data(refs).get("filled_keys") if refs.status_code == 200 else refs.text[:200]
        _step(f"fill-references {refs.status_code} keys={keys}")
    except Exception as exc:
        _step(f"fill-references skipped: {exc}")

    ready = live_client.post(
        f"/api/v1/projects/{project_id}/intake/confirm-ready",
        json={"confirm": True},
        timeout=30.0,
    )
    assert ready.status_code == 200, ready.text[:800]
    assert _data(ready).get("ready_to_compose") is True
    return project_id


@pytest.mark.integration
@pytest.mark.live_llm
def test_live_ect_intake_covers_document_slots(ect_project: str, live_client: httpx.Client):
    coverage = live_client.get(
        f"/api/v1/projects/{ect_project}/intake/coverage",
        timeout=30.0,
    )
    assert coverage.status_code == 200, coverage.text[:800]
    rows = _data(coverage).get("coverage") or []
    filled = {row["key"] for row in _filled_rows(rows)}
    for key in FACT_KEYS + ("s3", "s8", "s11", "s4.14"):
        assert key in filled, f"{key} should be filled from ECT pack, have {sorted(filled)}"


@pytest.mark.integration
@pytest.mark.live_llm
def test_live_ect_standalone_review_source_document(live_client: httpx.Client):
    pack = _pack()
    _step("Standalone review extract of ECT pack")
    extracted = live_client.post(
        "/api/v1/review/extract",
        files={"file": ("ect-ai-chatbot-tor.txt", pack.encode("utf-8"), "text/plain")},
        timeout=60.0,
    )
    assert extracted.status_code == 200, extracted.text[:800]
    job_id = _data(extracted).get("id")
    preview = str(_data(extracted).get("extracted_text") or "")
    assert "ECT AI Chatbot" in preview or "กกต" in preview
    _step(f"extract job {job_id} chars={len(preview)}")

    ran = live_client.post(
        "/api/v1/review/run",
        json={"id": job_id},
        timeout=900.0,
    )
    assert ran.status_code == 200, ran.text[:1200]
    payload = _data(ran)
    score = payload.get("quality_score")
    findings = payload.get("findings") or []
    _step(f"standalone source score={score} findings={len(findings)}")
    assert score is not None
    assert 0 <= float(score) <= 100
    assert payload.get("status") == "completed"


def _kick_draft(client: httpx.Client, project_id: str) -> None:
    _step("Start 13-section draft job")
    opened = client.post(
        f"/api/v1/projects/{project_id}/intake/open-draft",
        timeout=30.0,
    )
    assert opened.status_code == 200, opened.text[:800]
    try:
        with client.stream(
            "POST",
            f"/api/v1/projects/{project_id}/draft-chat/start",
            json={},
            timeout=httpx.Timeout(10.0, read=8.0),
        ) as streamed:
            for _line in streamed.iter_lines():
                break
    except (httpx.ReadTimeout, httpx.RemoteProtocolError):
        _step("draft-chat/start handed off to background job")


def _poll_draft(client: httpx.Client, project_id: str) -> dict:
    deadline = time.monotonic() + DRAFT_DEADLINE_SEC
    last = ""
    while time.monotonic() < deadline:
        status = client.get(
            f"/api/v1/projects/{project_id}/draft-chat/status",
            timeout=30.0,
        )
        assert status.status_code == 200, status.text[:800]
        payload = _data(status)
        drafted = int(payload.get("drafted_count") or 0)
        total = int(payload.get("total") or 13)
        done_keys = [
            row.get("section_key")
            for row in payload.get("sections") or []
            if row.get("ai_drafted") or row.get("has_content")
        ]
        line = f"draft {drafted}/{total} keys={done_keys}"
        if line != last:
            _step(line)
            last = line
        if payload.get("all_drafted") or drafted >= total:
            return payload
        time.sleep(DRAFT_POLL_SEC)
    pytest.fail(f"draft did not finish in {DRAFT_DEADLINE_SEC}s last={last}")


@pytest.mark.integration
@pytest.mark.live_llm
def test_live_ect_draft_all_sections_then_project_review(
    ect_project: str, live_client: httpx.Client
):
    _kick_draft(live_client, ect_project)
    status = _poll_draft(live_client, ect_project)
    sections = status.get("sections") or []
    missing = [
        row.get("section_key")
        for row in sections
        if not (row.get("ai_drafted") or row.get("has_content"))
    ]
    assert not missing, f"undrafted sections: {missing}"

    for row in sections:
        preview = str(row.get("content_preview") or "")
        if row.get("section_key") == "s4":
            assert len(preview) >= 40, preview[:120]
            continue
        assert _thai_count(preview) >= 8 or len(preview) >= 40, (
            f"{row.get('section_key')} too short: {preview[:160]!r}"
        )

    _step("confirm-phase4")
    phase4 = live_client.post(
        f"/api/v1/projects/{ect_project}/intake/confirm-phase4",
        json={"confirm": True},
        timeout=30.0,
    )
    assert phase4.status_code == 200, phase4.text[:800]
    assert _data(phase4).get("phase4_confirmed") is True
    assert int(_data(phase4).get("phase") or 0) >= 4

    _step("Project Rule Engine + ReviewAgent")
    reviewed = live_client.post(
        f"/api/v1/projects/{ect_project}/review",
        json={},
        timeout=1800.0,
    )
    assert reviewed.status_code == 200, reviewed.text[:1500]
    payload = _data(reviewed)
    score = payload.get("quality_score")
    _step(
        "project review "
        f"score={score} valid={payload.get('is_valid')} "
        f"findings={len(payload.get('findings') or [])} "
        f"suggestions={payload.get('suggestions_generated')} "
        f"assessment={(str(payload.get('overall_assessment') or '')[:180])}"
    )
    assert score is not None
    assert 0 <= float(score) <= 100

    assembled = live_client.get(
        f"/api/v1/projects/{ect_project}/sections",
        timeout=30.0,
    )
    assert assembled.status_code == 200, assembled.text[:800]
    tor_text = plain_tor_from_section_items(_data(assembled).get("sections") or [])
    assert "โครงการ" in tor_text or "กกต" in tor_text or len(tor_text) > 400

    _step("Standalone review of assembled TOR")
    extracted = live_client.post(
        "/api/v1/review/extract",
        files={
            "file": (
                "ect-drafted-tor.txt",
                tor_text.encode("utf-8"),
                "text/plain",
            )
        },
        timeout=60.0,
    )
    assert extracted.status_code == 200, extracted.text[:800]
    ran = live_client.post(
        "/api/v1/review/run",
        json={"id": _data(extracted)["id"]},
        timeout=900.0,
    )
    assert ran.status_code == 200, ran.text[:1200]
    drafted_score = _data(ran).get("quality_score")
    _step(f"standalone drafted TOR score={drafted_score}")
    assert drafted_score is not None
    assert float(drafted_score) > 0, "assembled drafted TOR must map to scoreable sections"

    compared = live_client.post(
        "/api/v1/review/compare-projects",
        json={"project_ids": [ect_project], "extract_ids": [_data(extracted)["id"]]},
        timeout=60.0,
    )
    _step(f"compare {compared.status_code} {compared.text[:400]}")

    _step("Export DOCX/PDF")
    exported = live_client.post(
        f"/api/v1/projects/{ect_project}/export",
        json={},
        timeout=30.0,
    )
    assert exported.status_code in {200, 202}, exported.text[:800]
    export_deadline = time.monotonic() + 120
    export_status = ""
    while time.monotonic() < export_deadline:
        status = live_client.get(
            f"/api/v1/projects/{ect_project}/export/status",
            timeout=30.0,
        )
        if status.status_code == 404:
            time.sleep(2)
            continue
        assert status.status_code == 200, status.text[:800]
        export_status = str(_data(status).get("status") or "")
        if export_status == "completed":
            break
        if export_status == "failed":
            pytest.fail(f"export failed: {status.text[:800]}")
        time.sleep(2)
    assert export_status == "completed", f"export status={export_status}"

    print(json.dumps({"project_id": ect_project, "project_score": score, "drafted_score": drafted_score}, ensure_ascii=False))
