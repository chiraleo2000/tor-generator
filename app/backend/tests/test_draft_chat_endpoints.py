"""Phase 3 draft-chat start / message / status endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db
from app.domain.slots import FACT_REQUIRED_SLOTS
from app.llm_admission import AdmissionTimeoutError
from app.main import app
from app.models.project import Project
from app.models.user import User
from app.services.intake_service import empty_slot_map

USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
PROJECT_ID = uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")


def _make_user():
    user = MagicMock(spec=User)
    user.id = USER_ID
    user.role = "officer"
    user.email = "test@example.go.th"
    user.name = "Test User"
    return user


def _ready_analysis():
    slots = empty_slot_map()
    for key in FACT_REQUIRED_SLOTS:
        slots[key] = {"content": "ข้อมูลโครงการทดสอบ", "status": "filled", "sources": []}
    return {"slot_map": slots, "ready_to_compose": True, "analyzed": True}


def _make_project(*, analysis=None):
    project = MagicMock(spec=Project)
    project.id = PROJECT_ID
    project.owner_id = USER_ID
    project.name = "โครงการทดสอบ"
    project.analysis_json = analysis or {}
    project.extracted_fields = {}
    project.current_phase = 3
    project.created_at = datetime(2026, 8, 24, tzinfo=timezone.utc)
    project.updated_at = datetime(2026, 8, 24, tzinfo=timezone.utc)
    return project


@pytest.fixture(autouse=True)
def setup_app_state():
    from app.api.v1.endpoints import draft_chat as draft_chat_ep

    draft_chat_ep._DRAFT_JOBS.clear()
    from app.draft_job_store import clear_memory

    clear_memory()
    app.state.db_session_factory = None
    app.state.db_engine = None
    app.state.redis = None
    app.state.minio = None

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_officer_user():
    user = _make_user()

    async def override():
        return user

    app.dependency_overrides[get_current_user] = override
    return user


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _override_db(mock_db):
    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db


class _SessionCM:
    def __init__(self, persist):
        self._persist = persist

    async def __aenter__(self):
        return self._persist

    async def __aexit__(self, *_args):
        return False


def _project_db(project):
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=result)
    return mock_db


def _persist_with_section(content: str | None):
    persist = AsyncMock()
    persist.commit = AsyncMock()
    persist.add = MagicMock()
    result = MagicMock()
    if content is None:
        result.scalar_one_or_none.return_value = None
    else:
        row = MagicMock()
        row.content = content
        row.ai_draft = content
        row.is_approved = False
        result.scalar_one_or_none.return_value = row
    persist.execute = AsyncMock(return_value=result)
    return persist


def test_start_rejects_when_not_ready(client, mock_officer_user):
    project = _make_project(analysis={"ready_to_compose": False})
    _override_db(_project_db(project))
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/draft-chat/start")
    assert response.status_code == 400
    assert "confirm-ready" in response.json()["error"]["message"]


def test_start_skips_existing_sections(client, mock_officer_user, monkeypatch):
    project = _make_project(analysis=_ready_analysis())
    _override_db(_project_db(project))
    persist = _persist_with_section("ร่างที่มีอยู่แล้วอย่างน้อยยี่สิบตัวอักษร")
    monkeypatch.setattr(app.state, "db_session_factory", lambda: _SessionCM(persist), raising=False)

    async def existing(*_args, **_kwargs):
        return "ร่างที่มีอยู่แล้วอย่างน้อยยี่สิบตัวอักษร"

    async def should_not_draft(*_args, **_kwargs):
        raise AssertionError("existing drafts must not call LM Studio")
        yield "x"

    with (
        patch("app.api.v1.endpoints.draft_chat._existing_section_text", side_effect=existing),
        patch("app.api.v1.endpoints.draft_chat.draft_single_section", side_effect=should_not_draft),
        patch("app.api.v1.endpoints.draft_chat.draft_scope_subsection", side_effect=should_not_draft),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        with client.stream("POST", f"/api/v1/projects/{PROJECT_ID}/draft-chat/start") as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")
    assert response.status_code == 200
    assert "event: all_done" in body
    assert "event: section_done" in body
    assert "drafted_count" in body


def test_start_drafts_empty_section_then_saves(client, mock_officer_user, monkeypatch):
    project = _make_project(analysis=_ready_analysis())
    _override_db(_project_db(project))
    persist = _persist_with_section(None)
    monkeypatch.setattr(app.state, "db_session_factory", lambda: _SessionCM(persist), raising=False)

    async def fake_draft(section_key, *_args, **_kwargs):
        yield f"เนื้อหาร่างหมวด {section_key} จากโมเดลทดสอบ"

    async def existing(_factory, _project_id, section_key):
        if section_key == "s1":
            return None
        return "มีแล้ว"

    with (
        patch("app.api.v1.endpoints.draft_chat._existing_section_text", side_effect=existing),
        patch("app.api.v1.endpoints.draft_chat.draft_single_section", side_effect=fake_draft),
        patch("app.api.v1.endpoints.draft_chat.draft_scope_subsection", side_effect=fake_draft),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        with client.stream("POST", f"/api/v1/projects/{PROJECT_ID}/draft-chat/start") as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")
    assert response.status_code == 200
    assert "event: all_done" in body
    persist.add.assert_called()


def test_start_drafts_sections_sequentially_from_llm(client, mock_officer_user, monkeypatch):
    project = _make_project(analysis=_ready_analysis())
    _override_db(_project_db(project))
    persist = _persist_with_section(None)
    monkeypatch.setattr(app.state, "db_session_factory", lambda: _SessionCM(persist), raising=False)
    order: list[str] = []

    async def fake_draft(section_key, *_args, **_kwargs):
        order.append(section_key)
        yield f"llm-{section_key}"

    async def existing(_factory, _project_id, section_key):
        if section_key in {"s1", "s2", "s3"}:
            return None
        return "มีแล้ว"

    with (
        patch("app.api.v1.endpoints.draft_chat._existing_section_text", side_effect=existing),
        patch("app.api.v1.endpoints.draft_chat.draft_single_section", side_effect=fake_draft),
        patch("app.api.v1.endpoints.draft_chat.draft_scope_subsection", side_effect=fake_draft),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        with client.stream("POST", f"/api/v1/projects/{PROJECT_ID}/draft-chat/start") as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")
    assert response.status_code == 200
    assert order == ["s1", "s2", "s3"]
    assert "event: all_done" in body


def test_start_reports_empty_model_output(client, mock_officer_user, monkeypatch):
    project = _make_project(analysis=_ready_analysis())
    _override_db(_project_db(project))
    persist = _persist_with_section(None)
    monkeypatch.setattr(app.state, "db_session_factory", lambda: _SessionCM(persist), raising=False)

    async def fake_draft(*_args, **_kwargs):
        if False:
            yield ""
        return

    async def existing(_factory, _project_id, section_key):
        return None if section_key == "s1" else "มีแล้ว"

    with (
        patch("app.api.v1.endpoints.draft_chat._existing_section_text", side_effect=existing),
        patch("app.api.v1.endpoints.draft_chat.draft_single_section", side_effect=fake_draft),
        patch("app.api.v1.endpoints.draft_chat.draft_scope_subsection", side_effect=fake_draft),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        with client.stream("POST", f"/api/v1/projects/{PROJECT_ID}/draft-chat/start") as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "event: all_done" in body
    persist.add.assert_not_called()


def test_message_accept_and_redraft(client, mock_officer_user, monkeypatch):
    project = _make_project(analysis=_ready_analysis())
    _override_db(_project_db(project))
    persist = _persist_with_section("ร่างเดิมของหมวดหนึ่ง")
    monkeypatch.setattr(app.state, "db_session_factory", lambda: _SessionCM(persist), raising=False)

    with client.stream(
        "POST",
        f"/api/v1/projects/{PROJECT_ID}/draft-chat/message",
        json={"content": "ยอมรับ", "section_key": "s1"},
    ) as accepted:
        accept_body = b"".join(accepted.iter_bytes()).decode("utf-8")
    assert accepted.status_code == 200
    assert "event: accepted" in accept_body

    async def fake_draft(*_args, **_kwargs):
        yield "ร่างใหม่หมวดหนึ่ง"

    with patch("app.api.v1.endpoints.draft_chat.draft_single_section", side_effect=fake_draft):
        with client.stream(
            "POST",
            f"/api/v1/projects/{PROJECT_ID}/draft-chat/message",
            json={"content": "ร่างใหม่ หมวด 1"},
        ) as redraft:
            redraft_body = b"".join(redraft.iter_bytes()).decode("utf-8")
    assert "event: token" in redraft_body
    assert "ร่างใหม่หมวดหนึ่ง" in redraft_body
    assert "event: section_done" in redraft_body


def test_message_requires_section(client, mock_officer_user):
    project = _make_project(analysis=_ready_analysis())
    _override_db(_project_db(project))
    with client.stream(
        "POST",
        f"/api/v1/projects/{PROJECT_ID}/draft-chat/message",
        json={"content": "ยอมรับ"},
    ) as response:
        body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "กรุณาระบุหมวดที่ยอมรับ" in body


def test_status_counts_drafted_sections(client, mock_officer_user):
    project = _make_project(analysis=_ready_analysis())
    mock_db = AsyncMock()
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    row = MagicMock()
    row.section_key = "s1"
    row.content = "ความเป็นมาของโครงการทดสอบระบบ"
    row.ai_draft = "ความเป็นมาของโครงการทดสอบระบบ"
    row.is_approved = True
    sections_result = MagicMock()
    sections_result.scalars.return_value.all.return_value = [row]
    s4_result = MagicMock()
    s4_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[project_result, sections_result, s4_result])
    _override_db(mock_db)

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/draft-chat/status")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["drafted_count"] == 1
    assert data["total"] == 13
    assert data["all_drafted"] is False
    assert data["sections"][0]["human_confirmed"] is True


def test_status_partial_s4_is_not_fully_drafted(client, mock_officer_user):
    from app.domain.tor_sections import SCOPE_SUBSECTIONS

    project = _make_project(analysis=_ready_analysis())
    mock_db = AsyncMock()
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    sections_result = MagicMock()
    sections_result.scalars.return_value.all.return_value = []
    sub = MagicMock()
    sub.sub_key = "s4.1"
    sub.content = "ขอบเขตงานหลักที่ร่างแล้วอย่างน้อยยี่สิบตัวอักษร"
    sub.ai_draft = "ขอบเขตงานหลักที่ร่างแล้วอย่างน้อยยี่สิบตัวอักษร"
    s4_result = MagicMock()
    s4_result.scalars.return_value.all.return_value = [sub]
    mock_db.execute = AsyncMock(side_effect=[project_result, sections_result, s4_result])
    _override_db(mock_db)

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/draft-chat/status")
    assert response.status_code == 200
    data = response.json()["data"]
    s4 = next(item for item in data["sections"] if item["section_key"] == "s4")
    assert s4["ai_drafted"] is False
    assert data["all_drafted"] is False
    assert len(SCOPE_SUBSECTIONS) == 14


def test_s4_complete_requires_all_fourteen():
    from app.api.v1.endpoints.draft_chat import _s4_complete
    from app.domain.tor_sections import SCOPE_SUBSECTIONS

    partial = {"s4.1": "มีเนื้อหาแล้วอย่างน้อยยี่สิบตัว"}
    assert _s4_complete(partial) is False
    full = {key: f"เนื้อหา {key} อย่างน้อยยี่สิบตัวอักษร" for key in SCOPE_SUBSECTIONS}
    assert _s4_complete(full) is True


@pytest.mark.asyncio
async def test_iter_llm_section_sse_timeout_and_error():
    from contextlib import asynccontextmanager

    from app.api.v1.endpoints.draft_chat import _iter_llm_section_sse

    parts: list[str] = []
    errors: list[str] = []

    @asynccontextmanager
    async def timeout_admit(*_args, **_kwargs):
        raise AdmissionTimeoutError("หมดเวลารอคิว LLM")
        yield "rid"

    with patch("app.api.v1.endpoints.draft_chat.admit", timeout_admit):
        events = [
            event
            async for event in _iter_llm_section_sse(
                None, "req", "s1", {}, USER_ID, parts, errors
            )
        ]
    assert errors
    assert "section_error" in events[0]

    parts.clear()
    errors.clear()

    async def fail_draft(*_args, **_kwargs):
        raise RuntimeError("llm down")
        yield ""

    with patch("app.api.v1.endpoints.draft_chat.draft_single_section", fail_draft):
        events = [
            event
            async for event in _iter_llm_section_sse(
                None, "req", "s2", {}, USER_ID, parts, errors
            )
        ]
    assert "llm down" in errors[0]
    assert "section_error" in events[0]


def test_start_llm_error_does_not_save_fallback(client, mock_officer_user, monkeypatch):
    project = _make_project(analysis=_ready_analysis())
    _override_db(_project_db(project))
    persist = _persist_with_section(None)
    monkeypatch.setattr(app.state, "db_session_factory", lambda: _SessionCM(persist), raising=False)

    async def fail_draft(*_args, **_kwargs):
        raise TimeoutError("LM Studio did not respond")
        yield "x"

    async def existing(_factory, _project_id, section_key):
        return None if section_key == "s1" else "มีแล้ว"

    with (
        patch("app.api.v1.endpoints.draft_chat._existing_section_text", side_effect=existing),
        patch("app.api.v1.endpoints.draft_chat.draft_single_section", side_effect=fail_draft),
        patch("app.api.v1.endpoints.draft_chat.draft_scope_subsection", side_effect=fail_draft),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        with client.stream("POST", f"/api/v1/projects/{PROJECT_ID}/draft-chat/start") as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")
    assert response.status_code == 200
    assert "event: all_done" in body
    persist.add.assert_not_called()


@pytest.mark.asyncio
async def test_iter_s4_subsection_sse_drafts_each_sub_in_order():
    from contextlib import asynccontextmanager

    from app.api.v1.endpoints.draft_chat import _iter_s4_subsection_sse
    from app.domain.tor_sections import SCOPE_SUBSECTIONS

    order: list[str] = []
    collected: dict[str, str] = {}
    errors: list[str] = []

    @asynccontextmanager
    async def passthrough_admit(*_args, **_kwargs):
        yield "rid"

    async def fake_sub(sub_key, *_args, **_kwargs):
        order.append(sub_key)
        yield f"llm-{sub_key}"

    with (
        patch("app.api.v1.endpoints.draft_chat.admit", passthrough_admit),
        patch("app.api.v1.endpoints.draft_chat.draft_scope_subsection", side_effect=fake_sub),
    ):
        events = [
            event
            async for event in _iter_s4_subsection_sse(
                None, "req", {}, USER_ID, {}, collected, errors
            )
        ]
    assert order == list(SCOPE_SUBSECTIONS)
    assert collected == {key: f"llm-{key}" for key in SCOPE_SUBSECTIONS}
    assert not errors
    assert any("subsection_start" in event for event in events)
    assert any("subsection_done" in event for event in events)
