"""Chat room ACL, validation, and SSE persistence tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db
from app.main import app
from app.models.user import User
from app.rag.retrieval import RetrievalResult

USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
OTHER_USER_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")
ROOM_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
PROJECT_ID = uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")


def _make_user(user_id=USER_ID, role="officer"):
    user = MagicMock(spec=User)
    user.id = user_id
    user.role = role
    user.email = "test@example.go.th"
    user.name = "Test User"
    return user


def _make_room(*, user_id=USER_ID, kind="kb", project_id=None, title="งวดจ่าย"):
    room = MagicMock()
    room.id = ROOM_ID
    room.user_id = user_id
    room.kind = kind
    room.project_id = project_id
    room.title = title
    room.updated_at = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
    room.messages = []
    return room


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


def test_list_rooms_rejects_invalid_kind(client, mock_officer_user):
    response = client.get("/api/v1/chat/rooms", params={"kind": "other"})
    assert response.status_code == 400
    assert response.json()["ok"] is False


def test_create_draft_room_requires_project(client, mock_officer_user):
    response = client.post("/api/v1/chat/rooms", json={"kind": "draft_intake", "title": "ร่าง"})
    assert response.status_code == 400
    assert "โครงการ" in response.json()["error"]["message"]


def test_list_rooms_returns_only_current_user_rows(client, mock_officer_user):
    room = _make_room()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [room]
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.get("/api/v1/chat/rooms", params={"kind": "kb"})
    assert response.status_code == 200
    rooms = response.json()["data"]["rooms"]
    assert len(rooms) == 1
    assert rooms[0]["title"] == "งวดจ่าย"
    assert rooms[0]["kind"] == "kb"


def test_messages_forbidden_for_other_owner(client, mock_officer_user):
    room = _make_room(user_id=OTHER_USER_ID)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = room
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.get(f"/api/v1/chat/rooms/{ROOM_ID}/messages")
    assert response.status_code == 403


def test_messages_not_found(client, mock_officer_user):
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.get(f"/api/v1/chat/rooms/{ROOM_ID}/messages")
    assert response.status_code == 404


def test_create_kb_room_returns_card_without_lazy_io(client, mock_officer_user):
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = client.post("/api/v1/chat/rooms", json={"kind": "kb", "title": "ถามกฎหมาย"})
    assert response.status_code == 201
    payload = response.json()["data"]
    assert payload["kind"] == "kb"
    assert payload["title"] == "ถามกฎหมาย"
    assert payload["last_message"] == ""
    mock_db.add.assert_called_once()


def test_create_draft_room_reuses_existing(client, mock_officer_user):
    existing = _make_room(kind="draft_intake", project_id=PROJECT_ID, title="แชทร่าง TOR")
    mock_db = AsyncMock()
    first = MagicMock()
    first.scalar_one_or_none.return_value = existing
    second = MagicMock()
    second.scalar_one_or_none.return_value = existing
    mock_db.execute = AsyncMock(side_effect=[first, second])
    _override_db(mock_db)

    response = client.post(
        "/api/v1/chat/rooms",
        json={"kind": "draft_intake", "project_id": str(PROJECT_ID), "title": "แชทร่าง TOR"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "แชทร่าง TOR"


def test_chat_sse_streams_tokens(client, mock_officer_user, monkeypatch):
    room = _make_room()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = room
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    persist = AsyncMock()
    persist.add = MagicMock()
    persist.commit = AsyncMock()

    class _CM:
        async def __aenter__(self):
            return persist

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(app.state, "db_session_factory", lambda: _CM(), raising=False)

    empty = RetrievalResult(chunks=[], query="งวดจ่าย", top_k=5, actual_count=0)

    async def fake_stream(*_args, **_kwargs):
        yield "งวด"
        yield "จ่าย"

    mock_llm = MagicMock()
    mock_llm.stream = fake_stream
    mock_factory = MagicMock()
    mock_factory.get_llm.return_value = mock_llm

    with (
        patch("app.api.v1.endpoints.chat.hybrid_retrieve", new_callable=AsyncMock) as retrieve,
        patch("app.api.v1.endpoints.chat.ProviderFactory", return_value=mock_factory),
    ):
        retrieve.return_value = (empty, [{"type": "article", "label": "ข้อ 85"}], False)
        with client.stream(
            "POST",
            f"/api/v1/chat/rooms/{ROOM_ID}/messages",
            json={"content": "งวดจ่ายตามระเบียบข้อใด", "search_scope": "both"},
        ) as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")

    assert response.status_code == 200
    assert "event: token" in body
    assert "งวด" in body
    assert "event: done" in body
    persist.add.assert_called()
