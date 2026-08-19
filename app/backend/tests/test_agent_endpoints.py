"""Mocked API tests for /api/v1/agent and /api/v1/kb-chat."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db
from app.main import app
from app.models.user import User
from app.services.intake_service import empty_slot_map

USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
SESSION_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PROJECT_ID = uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")


def _user():
    user = MagicMock(spec=User)
    user.id = USER_ID
    user.role = "officer"
    user.email = "test@example.go.th"
    user.name = "Tester"
    user.organization = "กระทรวงทดสอบ"
    return user


@pytest.fixture(autouse=True)
def setup_app_state():
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
def officer():
    user = _user()

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


def _session_row():
    row = MagicMock()
    row.id = SESSION_ID
    row.project_id = PROJECT_ID
    row.user_id = USER_ID
    row.phase = "gap_filling"
    row.slot_map = empty_slot_map()
    row.gap_iteration = 0
    row.graph_state = {
        "session_id": str(SESSION_ID),
        "project_id": str(PROJECT_ID),
        "user_id": str(USER_ID),
        "phase": "gap_filling",
        "slot_map": empty_slot_map(),
        "coverage_map": [],
        "readiness_score": 0,
        "ready": False,
        "gap_questions": ["ขอข้อมูล s1"],
        "gap_iteration": 0,
        "warnings": [],
        "messages": [],
        "section_drafts": {},
        "sections_acknowledged": [],
    }
    row.messages = []
    row.warnings = []
    return row


def _project():
    project = MagicMock()
    project.id = PROJECT_ID
    project.owner_id = USER_ID
    project.name = "โครงการ"
    project.ministry = "กระทรวง"
    project.budget = 1000
    project.project_type = "general"
    return project


def test_create_session_requires_input(client, officer):
    del officer
    response = client.post("/api/v1/agent/sessions", data={"free_text": "สั้น"})
    assert response.status_code == 400


def test_create_session_success(client, officer):
    del officer
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    mock_db.add = MagicMock()
    _override_db(mock_db)
    fake_state = {
        "session_id": str(SESSION_ID),
        "project_id": str(PROJECT_ID),
        "phase": "gap_filling",
        "coverage_map": [],
        "readiness_score": 0.0,
        "ready": False,
        "gap_questions": ["q"],
        "warnings": [],
        "error": None,
    }
    with (
        patch("app.api.v1.endpoints.agent.run_start", new=AsyncMock(return_value=fake_state)),
        patch("app.api.v1.endpoints.agent.persist_state", new=AsyncMock()),
        patch("app.api.v1.endpoints.agent.AgentSession") as session_cls,
        patch("app.api.v1.endpoints.agent.Project") as project_cls,
    ):
        project = _project()
        project_cls.return_value = project
        session = _session_row()
        session_cls.return_value = session
        response = client.post(
            "/api/v1/agent/sessions",
            data={
                "free_text": "ก" * 60,
                "name": "โครงการทดสอบ",
                "ministry": "กระทรวง",
                "budget": 1000000,
            },
        )
    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["phase"] == "gap_filling"


def test_coverage_and_status(client, officer):
    mock_db = AsyncMock()
    session = _session_row()
    project = _project()

    async def execute(stmt):
        result = MagicMock()
        text = str(stmt)
        if "agent_sessions" in text.lower() or "AgentSession" in text:
            result.scalar_one_or_none.return_value = session
        else:
            result.scalar_one_or_none.return_value = project
        return result

    mock_db.execute = AsyncMock(side_effect=execute)
    _override_db(mock_db)
    cov = client.get(f"/api/v1/agent/sessions/{SESSION_ID}/coverage")
    assert cov.status_code == 200
    status = client.get(f"/api/v1/agent/sessions/{SESSION_ID}/status")
    assert status.status_code == 200


def test_export_blocked_without_ack(client, officer):
    mock_db = AsyncMock()
    session = _session_row()
    session.graph_state["phase"] = "human_review"
    session.graph_state["sections_acknowledged"] = []
    project = _project()

    calls = {"n": 0}

    async def execute2(_stmt):
        result = MagicMock()
        calls["n"] += 1
        if calls["n"] % 2 == 1:
            result.scalar_one_or_none.return_value = session
        else:
            result.scalar_one_or_none.return_value = project
        return result

    mock_db.execute = AsyncMock(side_effect=execute2)
    _override_db(mock_db)
    response = client.get(f"/api/v1/agent/sessions/{SESSION_ID}/export")
    assert response.status_code == 400


def test_kb_chat_create_and_message_no_results(client, officer):
    mock_db = AsyncMock()
    mock_db.flush = AsyncMock()
    _override_db(mock_db)
    kb_id = uuid.uuid4()
    with patch("app.api.v1.endpoints.kb_chat.KnowledgeChatService") as svc_cls:
        service = MagicMock()
        service.create_session = AsyncMock(return_value=MagicMock(id=kb_id))
        svc_cls.return_value = service
        created = client.post("/api/v1/kb-chat/sessions")
        assert created.status_code == 201

    row = MagicMock()
    row.id = kb_id
    row.user_id = USER_ID
    row.history = []
    row.last_active_at = datetime.now(timezone.utc)
    with patch("app.api.v1.endpoints.kb_chat.KnowledgeChatService") as svc_cls:
        service = MagicMock()
        service.load_session = AsyncMock(return_value=row)
        service.answer = AsyncMock(
            return_value=MagicMock(
                answer="ไม่พบข้อมูลที่เกี่ยวข้อง",
                citations=[],
                no_results=True,
            )
        )
        svc_cls.return_value = service
        sent = client.post(
            f"/api/v1/kb-chat/sessions/{kb_id}/message",
            json={"message": "งบประมาณต้องอ้างอิงอะไร"},
        )
    assert sent.status_code == 200
    assert sent.json()["data"]["no_results"] is True


def _owned_db(session, project):
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.delete = AsyncMock()

    async def execute(_stmt):
        result = MagicMock()
        text = str(_stmt)
        if "agent_sessions" in text.lower() or "AgentSession" in text:
            result.scalar_one_or_none.return_value = session
        else:
            result.scalar_one_or_none.return_value = project
        return result

    mock_db.execute = AsyncMock(side_effect=execute)
    _override_db(mock_db)
    return mock_db


def test_answer_confirm_draft_review_delete(client, officer):
    del officer
    session = _session_row()
    project = _project()
    _owned_db(session, project)
    answered = {
        **session.graph_state,
        "phase": "gap_filling",
        "coverage_map": [],
        "readiness_score": 0.2,
        "ready": False,
        "gap_questions": ["q2"],
        "gap_iteration": 1,
        "slot_map": empty_slot_map(),
    }
    with (
        patch("app.api.v1.endpoints.agent.run_answer", new=AsyncMock(return_value=answered)),
        patch("app.api.v1.endpoints.agent.persist_state", new=AsyncMock()),
    ):
        response = client.post(
            f"/api/v1/agent/sessions/{SESSION_ID}/answer",
            json={"answer": "งบประมาณ 5 ล้านบาท"},
        )
    assert response.status_code == 200

    drafted = {
        **answered,
        "phase": "human_review",
        "section_drafts": {"s1": "ร่าง"},
        "draft_quality_scores": {"s1": 80},
        "overall_quality_score": 80,
        "validation_findings": [],
        "warnings": [],
        "mandatory_review_sections": ["s3"],
    }
    with (
        patch("app.api.v1.endpoints.agent.run_confirm", new=AsyncMock(return_value=drafted)),
        patch("app.api.v1.endpoints.agent.persist_state", new=AsyncMock()),
    ):
        confirmed = client.post(
            f"/api/v1/agent/sessions/{SESSION_ID}/confirm",
            json={"user_confirmed": True},
        )
    assert confirmed.status_code == 200

    session.graph_state = drafted
    session.phase = "human_review"
    draft = client.get(f"/api/v1/agent/sessions/{SESSION_ID}/draft")
    assert draft.status_code == 200

    exported = {
        **drafted,
        "phase": "complete",
        "export_docx_url": "https://x/a.docx",
        "export_pdf_url": "https://x/a.pdf",
        "error": None,
    }
    with (
        patch("app.api.v1.endpoints.agent.run_review", new=AsyncMock(return_value=exported)),
        patch("app.api.v1.endpoints.agent.persist_state", new=AsyncMock()),
    ):
        reviewed = client.post(
            f"/api/v1/agent/sessions/{SESSION_ID}/review",
            json={
                "human_approved": True,
                "acknowledged_sections": ["s3", "s6", "s8", "s10", "s13"],
            },
        )
    assert reviewed.status_code == 200
    deleted = client.delete(f"/api/v1/agent/sessions/{SESSION_ID}")
    assert deleted.status_code == 200


def test_kb_chat_history(client, officer):
    mock_db = AsyncMock()
    _override_db(mock_db)
    kb_id = uuid.uuid4()
    row = MagicMock()
    row.id = kb_id
    row.user_id = USER_ID
    row.history = [{"role": "user", "content": "ถาม"}]
    with patch("app.api.v1.endpoints.kb_chat.KnowledgeChatService") as svc_cls:
        service = MagicMock()
        service.load_session = AsyncMock(return_value=row)
        svc_cls.return_value = service
        history = client.get(f"/api/v1/kb-chat/sessions/{kb_id}/history")
    assert history.status_code == 200
    assert history.json()["data"]["messages"][0]["content"] == "ถาม"
