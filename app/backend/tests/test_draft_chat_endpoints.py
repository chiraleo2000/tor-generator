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


def test_s4_ai_map_and_overview_helpers():
    from types import SimpleNamespace

    from app.api.v1.endpoints.draft_chat import _s4_ai_map, _s4_overview_text

    rows = [
        SimpleNamespace(sub_key="s4.1", ai_draft="ขอบเขต", content=""),
        SimpleNamespace(sub_key=None, ai_draft="ข้าม", content=""),
        SimpleNamespace(sub_key="s4.2", ai_draft="  ", content=""),
    ]
    mapped = _s4_ai_map(rows)
    assert mapped == {"s4.1": "ขอบเขต"}
    assert _s4_overview_text({}, "สั้น") == "สั้น"
    with patch(
        "app.api.v1.endpoints.draft_chat.build_scope_overview",
        return_value="",
    ):
        clipped = _s4_overview_text({"s4.1": "x"}, "ก" * 400)
    assert "…" in clipped


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

    from app.api.v1.endpoints.draft_chat import _S4Work, _iter_s4_subsection_sse
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

    work = _S4Work(
        redis=None,
        request_id="req",
        slot_map={},
        user_id=USER_ID,
        collected=collected,
        errors=errors,
    )
    with (
        patch("app.api.v1.endpoints.draft_chat.admit", passthrough_admit),
        patch("app.api.v1.endpoints.draft_chat.draft_scope_subsection", side_effect=fake_sub),
    ):
        events = [event async for event in _iter_s4_subsection_sse(work, {})]
    assert order == list(SCOPE_SUBSECTIONS)
    assert collected == {key: f"llm-{key}" for key in SCOPE_SUBSECTIONS}
    assert not errors
    assert any("subsection_start" in event for event in events)
    assert any("subsection_done" in event for event in events)


def test_start_project_not_found(client, mock_officer_user):
    _override_db(_project_db(None))
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/draft-chat/start")
    assert response.status_code == 404


def test_start_forbidden_for_other_officer(client, mock_officer_user):
    project = _make_project(analysis=_ready_analysis())
    project.owner_id = uuid.UUID("99999999-9999-9999-9999-999999999999")
    _override_db(_project_db(project))
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/draft-chat/start")
    assert response.status_code == 403


def test_start_follows_background_job_when_already_running(
    client, mock_officer_user, monkeypatch
):
    project = _make_project(analysis=_ready_analysis())
    _override_db(_project_db(project))
    persist = _persist_with_section(None)
    monkeypatch.setattr(app.state, "db_session_factory", lambda: _SessionCM(persist), raising=False)

    with (
        patch(
            "app.api.v1.endpoints.draft_chat._ensure_draft_job",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.api.v1.endpoints.draft_chat.get_job",
            new_callable=AsyncMock,
            return_value={"status": "done", "drafted_count": 13, "total": 13},
        ),
        patch(
            "app.api.v1.endpoints.draft_chat._existing_section_text",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        with client.stream("POST", f"/api/v1/projects/{PROJECT_ID}/draft-chat/start") as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")
    assert response.status_code == 200
    assert "event: all_done" in body
    assert "event: progress" in body


def test_status_overlays_job_progress(client, mock_officer_user):
    project = _make_project(analysis=_ready_analysis())
    mock_db = AsyncMock()
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    sections_result = MagicMock()
    sections_result.scalars.return_value.all.return_value = []
    s4_result = MagicMock()
    s4_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[project_result, sections_result, s4_result])
    _override_db(mock_db)

    with patch(
        "app.api.v1.endpoints.draft_chat.get_job",
        new_callable=AsyncMock,
        return_value={"status": "running", "drafted_count": 4, "total": 13},
    ):
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/draft-chat/status")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["job_status"] == "running"
    assert data["drafted_count"] == 4
    assert data["all_drafted"] is False


def test_status_job_done_marks_all_drafted(client, mock_officer_user):
    project = _make_project(analysis=_ready_analysis())
    mock_db = AsyncMock()
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    sections_result = MagicMock()
    sections_result.scalars.return_value.all.return_value = []
    s4_result = MagicMock()
    s4_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(side_effect=[project_result, sections_result, s4_result])
    _override_db(mock_db)

    with patch(
        "app.api.v1.endpoints.draft_chat.get_job",
        new_callable=AsyncMock,
        return_value={"status": "done", "drafted_count": 13, "total": 13},
    ):
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/draft-chat/status")
    assert response.json()["data"]["all_drafted"] is True


def test_message_accept_missing_draft(client, mock_officer_user, monkeypatch):
    project = _make_project(analysis=_ready_analysis())
    _override_db(_project_db(project))
    persist = _persist_with_section(None)
    monkeypatch.setattr(app.state, "db_session_factory", lambda: _SessionCM(persist), raising=False)

    with client.stream(
        "POST",
        f"/api/v1/projects/{PROJECT_ID}/draft-chat/message",
        json={"content": "ยอมรับ", "section_key": "s1"},
    ) as response:
        body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "ยังไม่มีร่างหมวด s1" in body


def test_message_edit_requires_section(client, mock_officer_user):
    project = _make_project(analysis=_ready_analysis())
    _override_db(_project_db(project))
    with client.stream(
        "POST",
        f"/api/v1/projects/{PROJECT_ID}/draft-chat/message",
        json={"content": "แก้ไขให้สั้นลง"},
    ) as response:
        body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "กรุณาระบุหมวดที่ต้องการแก้ไข" in body


def test_message_s4_redraft_and_edit_timeout(
    client, mock_officer_user, monkeypatch
):
    from contextlib import asynccontextmanager

    project = _make_project(analysis=_ready_analysis())
    _override_db(_project_db(project))
    persist = _persist_with_section("ร่างเดิมของหมวดสี่")
    monkeypatch.setattr(app.state, "db_session_factory", lambda: _SessionCM(persist), raising=False)

    async def fake_s4(work, _existing):
        work.collected["s4.1"] = "ขอบเขตงานหลักของโครงการทดสอบ"
        yield 'event: subsection_done\ndata: {"sub_key": "s4.1"}\n\n'

    with patch("app.api.v1.endpoints.draft_chat._iter_s4_subsection_sse", side_effect=fake_s4):
        with client.stream(
            "POST",
            f"/api/v1/projects/{PROJECT_ID}/draft-chat/message",
            json={"content": "ร่างใหม่ หมวด 4", "section_key": "s4"},
        ) as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "event: section_start" in body
    assert "event: section_done" in body

    @asynccontextmanager
    async def timeout_admit(*_args, **_kwargs):
        raise AdmissionTimeoutError("หมดเวลารอคิวโมเดลภาษา")
        yield "rid"

    with patch("app.api.v1.endpoints.draft_chat.admit", timeout_admit):
        with client.stream(
            "POST",
            f"/api/v1/projects/{PROJECT_ID}/draft-chat/message",
            json={"content": "แก้ไขให้สั้นลง", "section_key": "s1"},
        ) as response:
            timeout_body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "event: error" in timeout_body
    assert "หมดเวลารอคิวโมเดลภาษา" in timeout_body


def test_message_revision_llm_error(client, mock_officer_user, monkeypatch):
    project = _make_project(analysis=_ready_analysis())
    _override_db(_project_db(project))
    persist = _persist_with_section("ร่างเดิมของหมวดหนึ่ง")
    monkeypatch.setattr(app.state, "db_session_factory", lambda: _SessionCM(persist), raising=False)

    async def boom(*_args, **_kwargs):
        raise RuntimeError("llm down")
        yield "x"

    with patch("app.api.v1.endpoints.draft_chat.edit_section_draft", side_effect=boom):
        with client.stream(
            "POST",
            f"/api/v1/projects/{PROJECT_ID}/draft-chat/message",
            json={"content": "แก้ไขให้สั้นลง", "section_key": "s1"},
        ) as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "event: error" in body
    assert "llm down" in body


@pytest.mark.asyncio
async def test_existing_section_text_s4_complete_and_plain_empty():
    from app.api.v1.endpoints.draft_chat import _existing_section_text
    from app.domain.tor_sections import SCOPE_SUBSECTIONS

    persist = AsyncMock()
    persist.commit = AsyncMock()
    empty_result = MagicMock()
    empty_result.scalar_one_or_none.return_value = None
    persist.execute = AsyncMock(return_value=empty_result)

    text = await _existing_section_text(lambda: _SessionCM(persist), PROJECT_ID, "s1")
    assert text is None

    row = MagicMock()
    row.ai_draft = "ร่างหมวดหนึ่งที่มีเนื้อหาพอ"
    row.content = "เนื้อหาหมวดหนึ่งที่มีเนื้อหาพอ"
    filled = MagicMock()
    filled.scalar_one_or_none.return_value = row
    persist.execute = AsyncMock(return_value=filled)
    text = await _existing_section_text(lambda: _SessionCM(persist), PROJECT_ID, "s2")
    assert "ร่างหมวดหนึ่ง" in text or "เนื้อหาหมวดหนึ่ง" in text

    complete = {
        key: MagicMock(sub_key=key, ai_draft=f"เนื้อหา {key} อย่างน้อยยี่สิบตัวอักษร", content="")
        for key in SCOPE_SUBSECTIONS
    }
    with patch(
        "app.api.v1.endpoints.draft_chat._load_s4_rows",
        new_callable=AsyncMock,
        return_value=list(complete.values()),
    ):
        merged = await _existing_section_text(lambda: _SessionCM(persist), PROJECT_ID, "s4")
    assert merged

    partial = [MagicMock(sub_key="s4.1", ai_draft="มีบางส่วนอย่างน้อยยี่สิบตัว", content="")]
    with patch(
        "app.api.v1.endpoints.draft_chat._load_s4_rows",
        new_callable=AsyncMock,
        return_value=partial,
    ):
        missing = await _existing_section_text(lambda: _SessionCM(persist), PROJECT_ID, "s4")
    assert missing is None


@pytest.mark.asyncio
async def test_upsert_sub_insert_and_update():
    from app.api.v1.endpoints.draft_chat import _upsert_sub

    persist = AsyncMock()
    persist.add = MagicMock()
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    persist.execute = AsyncMock(return_value=missing)
    await _upsert_sub(persist, PROJECT_ID, "s4.1", "ขอบเขตงานหลัก")
    persist.add.assert_called_once()

    row = MagicMock()
    row.content = ""
    row.ai_draft = ""
    found = MagicMock()
    found.scalar_one_or_none.return_value = row
    persist.execute = AsyncMock(return_value=found)
    await _upsert_sub(persist, PROJECT_ID, "s4.1", "ขอบเขตงานใหม่")
    assert row.content == "ขอบเขตงานใหม่"
    assert row.ai_draft == "ขอบเขตงานใหม่"


@pytest.mark.asyncio
async def test_replay_emit_and_load_section_draft():
    from app.api.v1.endpoints.draft_chat import (
        _emit_s4_sub_done,
        _load_section_draft,
        _replay_existing_s4_sub,
        _save_section,
    )

    collected: dict[str, str] = {}
    events = [
        event
        async for event in _replay_existing_s4_sub(
            "s4.1", "ขอบเขต", "มีอยู่แล้วอย่างน้อยยี่สิบตัว", collected, None, None
        )
    ]
    assert collected["s4.1"].startswith("มีอยู่แล้ว")
    assert any("subsection_done" in event or "token" in event for event in events)

    persist = _persist_with_section(None)
    with patch(
        "app.api.v1.endpoints.draft_chat._persist_s4_sub", new_callable=AsyncMock
    ) as persist_sub:
        done = [
            event
            async for event in _emit_s4_sub_done(
                lambda: _SessionCM(persist), PROJECT_ID, "s4.2", "วิธี", "รายละเอียด"
            )
        ]
    persist_sub.assert_awaited()
    assert "subsection_done" in done[0]

    persist = _persist_with_section("ร่างหมวดหนึ่ง")
    loaded = await _load_section_draft(lambda: _SessionCM(persist), PROJECT_ID, "s1")
    assert loaded == "ร่างหมวดหนึ่ง"

    with patch(
        "app.api.v1.endpoints.draft_chat._load_s4_subs",
        new_callable=AsyncMock,
        return_value={"s4.1": "ขอบเขต"},
    ), patch(
        "app.api.v1.endpoints.draft_chat.build_merged_scope",
        return_value="รวมขอบเขต",
    ):
        s4 = await _load_section_draft(lambda: _SessionCM(persist), PROJECT_ID, "s4")
    assert s4 == "รวมขอบเขต"

    with patch(
        "app.api.v1.endpoints.draft_chat._save_s4_bundle", new_callable=AsyncMock
    ) as bundle:
        await _save_section(persist, PROJECT_ID, "s4", "เนื้อหา s4")
    bundle.assert_awaited()


@pytest.mark.asyncio
async def test_save_s4_bundle_updates_existing_overview():
    from app.api.v1.endpoints.draft_chat import _save_s4_bundle

    persist = AsyncMock()
    persist.add = MagicMock()
    overview = MagicMock()
    overview.content = ""
    overview.ai_draft = ""
    with (
        patch(
            "app.api.v1.endpoints.draft_chat.split_scope_subsection_draft",
            return_value={"s4.1": "ขอบเขตงานหลัก", "nope": "ข้าม"},
        ),
        patch("app.api.v1.endpoints.draft_chat._upsert_sub", new_callable=AsyncMock),
        patch(
            "app.api.v1.endpoints.draft_chat._get_section",
            new_callable=AsyncMock,
            return_value=overview,
        ),
    ):
        await _save_s4_bundle(persist, PROJECT_ID, "เนื้อหา s4")
    assert overview.content
    persist.add.assert_not_called()


@pytest.mark.asyncio
async def test_draft_missing_section_errors_and_s4_complete():
    from app.api.v1.endpoints.draft_chat import (
        _SeqDraft,
        _draft_missing_s4,
        _draft_missing_section,
    )
    from app.domain.tor_sections import SCOPE_SUBSECTIONS

    persist = _persist_with_section(None)
    job = _SeqDraft(
        session_factory=lambda: _SessionCM(persist),
        project_id=PROJECT_ID,
        slot_map={},
        user_id=USER_ID,
        request_id="req",
        redis=None,
    )

    async def fail_sse(_redis, _rid, _key, _slots, _uid, _parts, errors):
        errors.append("หมดเวลา")
        yield "event: section_error\ndata: {}\n\n"

    with patch("app.api.v1.endpoints.draft_chat._iter_llm_section_sse", fail_sse):
        assert await _draft_missing_section(job, "s1") is False

    async def ok_sse(_redis, _rid, _key, _slots, _uid, parts, _errors):
        parts.append("ร่างหมวดหนึ่งจากโมเดล")
        yield "event: token\ndata: {}\n\n"

    with (
        patch("app.api.v1.endpoints.draft_chat._iter_llm_section_sse", ok_sse),
        patch("app.api.v1.endpoints.draft_chat._save_section", new_callable=AsyncMock) as save,
    ):
        assert await _draft_missing_section(job, "s2") is True
    save.assert_awaited()

    async def fill_s4(work, _existing):
        for key in SCOPE_SUBSECTIONS:
            work.collected[key] = f"เนื้อหา {key} อย่างน้อยยี่สิบตัวอักษร"
        if False:
            yield ""

    with (
        patch("app.api.v1.endpoints.draft_chat._load_s4_rows", new_callable=AsyncMock, return_value=[]),
        patch("app.api.v1.endpoints.draft_chat._iter_s4_subsection_sse", fill_s4),
        patch("app.api.v1.endpoints.draft_chat._save_s4_bundle", new_callable=AsyncMock) as bundle,
    ):
        assert await _draft_missing_s4(job) is True
    bundle.assert_awaited()


@pytest.mark.asyncio
async def test_run_sequential_draft_marks_failed_on_outer_error():
    from app.api.v1.endpoints.draft_chat import _SeqDraft, _run_sequential_draft

    persist = _persist_with_section(None)
    job = _SeqDraft(
        session_factory=lambda: _SessionCM(persist),
        project_id=PROJECT_ID,
        slot_map={},
        user_id=USER_ID,
        request_id="req",
        redis="redis",
    )
    with (
        patch("app.api.v1.endpoints.draft_chat.set_job", new_callable=AsyncMock),
        patch("app.api.v1.endpoints.draft_chat._try_draft_one_section", new_callable=AsyncMock, return_value=True),
        patch(
            "app.api.v1.endpoints.draft_chat.bump_progress",
            new_callable=AsyncMock,
            side_effect=RuntimeError("redis down"),
        ),
        patch("app.api.v1.endpoints.draft_chat.mark_status", new_callable=AsyncMock) as marked,
        pytest.raises(RuntimeError, match="redis down"),
    ):
        await _run_sequential_draft(job, remaining_passes=0)
    marked.assert_awaited_with("redis", PROJECT_ID, "failed")


@pytest.mark.asyncio
async def test_stream_attached_job_progress_swallows_job_error():
    import asyncio

    from app.api.v1.endpoints.draft_chat import _stream_attached_job_progress

    async def boom():
        raise RuntimeError("job failed")

    job = asyncio.create_task(boom())
    persist = _persist_with_section(None)

    async def empty_emit(*_args, **_kwargs):
        if False:
            yield ""

    with patch("app.api.v1.endpoints.draft_chat._emit_newly_done_sections", empty_emit):
        events = [
            event
            async for event in _stream_attached_job_progress(
                job, lambda: _SessionCM(persist), PROJECT_ID, set()
            )
        ]
    assert any("all_done" in event for event in events)


@pytest.mark.asyncio
async def test_stream_s4_redraft_skips_when_empty():
    from app.api.v1.endpoints.draft_chat import _ChatStream, _stream_s4_redraft

    request = MagicMock()
    persist = _persist_with_section(None)
    stream = _ChatStream(
        request=request,
        project_id=PROJECT_ID,
        section_key="s4",
        intent="redraft",
        detail="",
        slot_map={},
        user_id=USER_ID,
        request_id="req",
        session_factory=lambda: _SessionCM(persist),
    )

    async def empty(_work, _existing):
        if False:
            yield ""

    with patch("app.api.v1.endpoints.draft_chat._iter_s4_subsection_sse", empty):
        events = [event async for event in _stream_s4_redraft(stream, None, "ขอบเขต")]
    assert events == []


@pytest.mark.asyncio
async def test_emit_newly_done_sections_and_status_row_partial_s4():
    from app.api.v1.endpoints.draft_chat import _draft_status_row, _emit_newly_done_sections

    persist = _persist_with_section(None)

    async def existing(_factory, _pid, key):
        return "มีแล้วอย่างน้อยยี่สิบตัวอักษร" if key == "s1" else None

    with patch("app.api.v1.endpoints.draft_chat._existing_section_text", side_effect=existing):
        events = [
            event
            async for event in _emit_newly_done_sections(
                lambda: _SessionCM(persist), PROJECT_ID, set()
            )
        ]
    assert any("section_done" in event for event in events)

    data, drafted = _draft_status_row(
        "s4", None, s4_ready=False, s4_subs={"s4.1": "ขอบเขตบางส่วน"}
    )
    assert drafted is False
    assert data["has_content"] is True


@pytest.mark.asyncio
async def test_iter_s4_replays_existing_then_drafts_rest():
    from contextlib import asynccontextmanager

    from app.api.v1.endpoints.draft_chat import _S4Work, _iter_s4_subsection_sse
    from app.domain.tor_sections import SCOPE_SUBSECTIONS

    collected: dict[str, str] = {}
    first = next(iter(SCOPE_SUBSECTIONS))

    @asynccontextmanager
    async def passthrough_admit(*_args, **_kwargs):
        yield "rid"

    async def fake_sub(sub_key, *_args, **_kwargs):
        yield f"llm-{sub_key}"

    work = _S4Work(
        redis=None,
        request_id="req",
        slot_map={},
        user_id=USER_ID,
        collected=collected,
        errors=[],
    )
    with (
        patch("app.api.v1.endpoints.draft_chat.admit", passthrough_admit),
        patch("app.api.v1.endpoints.draft_chat.draft_scope_subsection", side_effect=fake_sub),
    ):
        events = [
            event
            async for event in _iter_s4_subsection_sse(
                work, {first: "มีอยู่แล้วอย่างน้อยยี่สิบตัวอักษร"}
            )
        ]
    assert first in collected
    assert any("subsection_start" in event for event in events)
    assert collected[first].startswith("มีอยู่แล้ว")
