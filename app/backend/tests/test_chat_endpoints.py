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
from app.rag.kb_qa import CHAT_MAX_TOKENS, chat_rag_top_k

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

    empty = RetrievalResult(chunks=[], query="งวดจ่าย", top_k=chat_rag_top_k(), actual_count=0)
    captured: dict = {}

    async def fake_stream(messages, **kwargs):
        captured["messages"] = messages
        captured.update(kwargs)
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
    retrieve.assert_awaited()
    assert retrieve.await_args.kwargs["top_k"] == chat_rag_top_k()
    assert captured["max_tokens"] == CHAT_MAX_TOKENS
    assert "ข้อความเนื้อหา" in captured["messages"][0]["content"]


def test_rename_and_delete_room(client, mock_officer_user):
    room = _make_room()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = room
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    mock_db.delete = AsyncMock()
    _override_db(mock_db)

    renamed = client.patch(
        f"/api/v1/chat/rooms/{ROOM_ID}",
        json={"title": "ห้องกฎหมาย"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["data"]["title"] == "ห้องกฎหมาย"

    deleted = client.delete(f"/api/v1/chat/rooms/{ROOM_ID}")
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True

    room = _make_room()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = room
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    saved = MagicMock()
    saved.id = uuid.uuid4()
    saved.name = "reg.pdf"
    saved.processing_status = "completed"
    saved.chunk_count = 4

    with (
        patch("app.api.v1.endpoints.chat._validate_kb_bytes", return_value="application/pdf"),
        patch("app.api.v1.endpoints.chat.ingest_file_bytes", new_callable=AsyncMock) as ingest,
    ):
        ingest.return_value = saved
        response = client.post(
            f"/api/v1/chat/rooms/{ROOM_ID}/attachments",
            files={"file": ("reg.pdf", b"%PDF-1.4 content", "application/pdf")},
        )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["document_id"] == str(saved.id)
    assert payload["name"] == "reg.pdf"
    assert payload["status"] == "completed"
    assert payload["processing_status"] == "completed"
    assert payload["chunk_count"] == 4
    ingest.assert_awaited()
    kwargs = ingest.await_args.kwargs
    assert kwargs["scope"] == "user"
    assert kwargs["owner_id"] == USER_ID
    assert kwargs["corpus_group"] == "user"
    assert kwargs["category"] == "other"


def test_attachment_appears_in_kb_catalog(client, mock_officer_user):
    from app.api.v1.endpoints.knowledge_base import _catalog_payload
    from tests.test_knowledge_base_endpoint import _make_kb_document

    room = _make_room()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = room
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    attached = _make_kb_document(
        name="chat-note.pdf",
        category="other",
        owner_id=USER_ID,
        scope="user",
        corpus_group="user",
        processing_status="completed",
        chunk_count=2,
    )
    with (
        patch("app.api.v1.endpoints.chat._validate_kb_bytes", return_value="application/pdf"),
        patch("app.api.v1.endpoints.chat.ingest_file_bytes", new_callable=AsyncMock) as ingest,
    ):
        ingest.return_value = attached
        response = client.post(
            f"/api/v1/chat/rooms/{ROOM_ID}/attachments",
            files={"file": ("chat-note.pdf", b"%PDF-1.4 content", "application/pdf")},
        )
    assert response.status_code == 200

    cat_db = AsyncMock()
    cat_result = MagicMock()
    cat_result.scalars.return_value.all.return_value = [attached]
    cat_db.execute = AsyncMock(return_value=cat_result)
    _override_db(cat_db)
    catalog = client.get("/api/v1/knowledge-base/catalog")
    assert catalog.status_code == 200
    names = {item["name"] for item in catalog.json()["data"]["userFiles"]}
    assert "chat-note.pdf" in names
    payload = _catalog_payload([attached], viewer_id=USER_ID)
    assert {item["name"] for item in payload["userFiles"]} == {"chat-note.pdf"}


def test_list_messages_for_owner(client, mock_officer_user):
    room = _make_room()
    msg = MagicMock()
    msg.id = uuid.uuid4()
    msg.role = "user"
    msg.content = "งวดจ่าย"
    msg.citations = []
    msg.created_at = datetime(2026, 8, 18, 10, 0, 0, tzinfo=timezone.utc)
    room.messages = [msg]
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = room
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.get(f"/api/v1/chat/rooms/{ROOM_ID}/messages")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["messages"][0]["content"] == "งวดจ่าย"


def test_list_prompts(client, mock_officer_user):
    prompt = MagicMock()
    prompt.id = uuid.uuid4()
    prompt.title = "วิธีเฉพาะเจาะจง"
    prompt.body = "วิธีเฉพาะเจาะจงใช้เมื่อใด"
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [prompt]
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.get("/api/v1/chat/prompts", params={"kind": "kb"})
    assert response.status_code == 200
    assert response.json()["data"]["prompts"][0]["title"] == "วิธีเฉพาะเจาะจง"


def test_empty_attachment_rejected(client, mock_officer_user):
    room = _make_room()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = room
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)
    response = client.post(
        f"/api/v1/chat/rooms/{ROOM_ID}/attachments",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 400
