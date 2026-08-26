"""Intake coverage, confirm-ready, and analyze validation tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db
from app.domain.slots import FACT_REQUIRED_SLOTS
from app.main import app
from app.models.project import Project
from app.models.user import User
from app.services.intake_service import empty_slot_map

USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
OTHER_USER_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")
PROJECT_ID = uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")


def _make_user(user_id=USER_ID, role="officer"):
    user = MagicMock(spec=User)
    user.id = user_id
    user.role = role
    user.email = "test@example.go.th"
    user.name = "Test User"
    return user


def _make_project(*, owner_id=USER_ID, analysis=None, phase=0):
    project = MagicMock(spec=Project)
    project.id = PROJECT_ID
    project.owner_id = owner_id
    project.name = "โครงการทดสอบ"
    project.analysis_json = analysis or {}
    project.extracted_fields = {}
    project.current_phase = phase
    project.created_at = datetime(2026, 8, 18, tzinfo=timezone.utc)
    project.updated_at = datetime(2026, 8, 18, tzinfo=timezone.utc)
    return project


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


def test_coverage_returns_s4_subslots(client, mock_officer_user):
    project = _make_project()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/intake/coverage")
    assert response.status_code == 200
    keys = [row["key"] for row in response.json()["data"]["coverage"]]
    assert "s1" in keys
    assert "s4.1" in keys
    assert "s4.14" in keys
    assert response.json()["data"]["ready_to_compose"] is False


def test_coverage_forbidden_for_other_officer(client, mock_officer_user):
    project = _make_project(owner_id=OTHER_USER_ID)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/intake/coverage")
    assert response.status_code == 403


def test_analyze_without_texts_returns_400(client, mock_officer_user):
    project = _make_project()
    project.extracted_fields = {}
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/intake/analyze")
    assert response.status_code == 400


def test_confirm_ready_rejects_reference_only_facts(client, mock_officer_user):
    slots = empty_slot_map()
    for key in FACT_REQUIRED_SLOTS:
        slots[key] = {"content": "อ้างระเบียบ", "status": "reference_only", "sources": ["พ.ร.บ."]}
    project = _make_project(analysis={"slot_map": slots}, phase=1)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/intake/confirm-ready",
        json={"confirm": True},
    )
    assert response.status_code == 400


def test_confirm_ready_sets_phase_three(client, mock_officer_user):
    slots = empty_slot_map()
    for key in FACT_REQUIRED_SLOTS:
        slots[key] = {
            "content": "ข้อมูลข้อเท็จจริงของโครงการทดสอบ",
            "status": "filled",
            "sources": ["ผู้ใช้ตอบในแชท"],
        }
    project = _make_project(analysis={"slot_map": slots}, phase=1)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/intake/confirm-ready",
        json={"confirm": True},
    )
    assert response.status_code == 200
    assert response.json()["data"]["ready_to_compose"] is True
    assert project.current_phase >= 3
    assert project.analysis_json["ready_to_compose"] is True
    mock_db.commit.assert_awaited()


def test_intake_text_appends_pack(client, mock_officer_user):
    project = _make_project()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/intake/text",
        json={"content": "โครงการทดสอบวงเงินหนึ่งแสนบาท ระยะเวลา 180 วัน"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["count"] == 1
    texts = project.extracted_fields["intake_texts"]
    assert texts[0]["text"].startswith("โครงการทดสอบ")


def test_confirm_phase4_sets_phase_four(client, mock_officer_user):
    slots = empty_slot_map()
    for key in FACT_REQUIRED_SLOTS:
        slots[key] = {
            "content": "ข้อมูลข้อเท็จจริงของโครงการทดสอบ",
            "status": "filled",
            "sources": ["ผู้ใช้ตอบในแชท"],
        }
    project = _make_project(
        analysis={"slot_map": slots, "ready_to_compose": True},
        phase=3,
    )
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/intake/confirm-phase4",
        json={"confirm": True},
    )
    assert response.status_code == 200
    assert response.json()["data"]["phase4_confirmed"] is True
    assert project.current_phase >= 4
    assert project.analysis_json["phase4_confirmed"] is True
    mock_db.commit.assert_awaited()


def test_confirm_phase4_requires_ready(client, mock_officer_user):
    project = _make_project(phase=3)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/intake/confirm-phase4",
        json={"confirm": True},
    )
    assert response.status_code == 400


def test_fill_references_requires_analyze(client, mock_officer_user):
    project = _make_project()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/intake/fill-references")
    assert response.status_code == 400


@patch("app.api.v1.endpoints.intake.hybrid_retrieve", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.intake.ProviderFactory")
def test_intake_chat_streams_and_fills_gap(
    factory, retrieve, client, mock_officer_user, monkeypatch
):
    from app.rag.retrieval import RetrievalResult

    slots = empty_slot_map()
    slots["s1"] = {"content": "", "status": "gap", "sources": []}
    project = _make_project(analysis={"slot_map": slots, "gap_questions": ["ขอชื่อโครงการ"]})
    room = MagicMock()
    room.id = uuid.uuid4()
    room.user_id = USER_ID
    room.kind = "draft_intake"
    room.project_id = PROJECT_ID
    room.title = "ร่าง"
    room.updated_at = datetime(2026, 8, 18, tzinfo=timezone.utc)
    room.messages = []

    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    room_result = MagicMock()
    room_result.scalar_one_or_none.return_value = room
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[project_result, room_result])
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    persist = AsyncMock()
    persist.add = MagicMock()
    persist.commit = AsyncMock()
    persist_result = MagicMock()
    persist_result.scalar_one.return_value = project
    persist.execute = AsyncMock(return_value=persist_result)

    class _CM:
        async def __aenter__(self):
            return persist

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr(app.state, "db_session_factory", lambda: _CM(), raising=False)

    chunk = MagicMock()
    chunk.source_document = "คลัง"
    chunk.text = "อ้างอิงกฎหมาย"
    retrieve.return_value = (
        RetrievalResult(chunks=[chunk], query="q", top_k=5, actual_count=1),
        [{"label": "พ.ร.บ."}],
        False,
    )

    async def fake_stream(*_args, **_kwargs):
        yield "รับ"
        yield "ทราบ"

    mock_llm = MagicMock()
    mock_llm.stream = fake_stream
    factory.return_value.get_llm.return_value = mock_llm

    with client.stream(
        "POST",
        f"/api/v1/projects/{PROJECT_ID}/intake/chat",
        json={"content": "ความเป็นมาคือกรมบัญชีกลางต้องมีระบบบริหารสัญญาจัดซื้อจัดจ้างภาครัฐ"},
    ) as response:
        body = b"".join(response.iter_bytes()).decode("utf-8")

    assert response.status_code == 200
    assert "event: done" in body
    assert "บันทึก" in body or "event: token" in body


@patch("app.api.v1.endpoints.intake.analyze_pack", new_callable=AsyncMock)
def test_analyze_with_pack_advances_phase(analyze_mock, client, mock_officer_user):
    slots = empty_slot_map()
    slots["s1"] = {"content": "โครงการจัดซื้อ", "status": "filled", "sources": []}
    analyze_mock.return_value = {
        "slot_map": slots,
        "gap_questions": ["ขอวงเงิน"],
        "ready_to_compose": False,
        "analyzed": True,
    }
    project = _make_project()
    project.extracted_fields = {
        "intake_texts": [{"name": "ข้อความผู้ใช้.txt", "text": "โครงการทดสอบวงเงิน"}],
    }
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/intake/analyze")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["analyzed"] is True
    assert project.current_phase >= 1
    analyze_mock.assert_awaited()


@patch("app.api.v1.endpoints.intake.extract_text")
@patch("app.api.v1.endpoints.intake.unlink_path", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.intake.write_temp_bytes", new_callable=AsyncMock)
def test_intake_upload_does_not_analyze(
    write_tmp, unlink_mock, extract_mock, client, mock_officer_user
):
    extracted = MagicMock()
    extracted.text = "เนื้อหาไฟล์โครงการจัดซื้อ"
    extracted.method = "direct"
    extract_mock.return_value = extracted
    write_tmp.return_value = "tmp.bin"
    project = _make_project()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/intake/upload",
        files={"files": ("pack.txt", b"hello pack", "text/plain")},
    )
    assert response.status_code == 200
    assert response.json()["data"]["count"] == 1
    texts = project.extracted_fields["intake_texts"]
    assert texts[0]["text"] == "เนื้อหาไฟล์โครงการจัดซื้อ"
    analyze_mock_calls = getattr(project, "analysis_json", {}) or {}
    assert analyze_mock_calls.get("analyzed") is not True


def test_confirm_ready_requires_confirm_flag(client, mock_officer_user):
    slots = empty_slot_map()
    for key in FACT_REQUIRED_SLOTS:
        slots[key] = {
            "content": "ข้อมูลข้อเท็จจริงของโครงการทดสอบ",
            "status": "filled",
            "sources": ["ผู้ใช้ตอบในแชท"],
        }
    project = _make_project(analysis={"slot_map": slots}, phase=1)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/intake/confirm-ready",
        json={"confirm": False},
    )
    assert response.status_code == 400


@patch("app.api.v1.endpoints.intake.fill_non_fact_reference_slots", new_callable=AsyncMock)
def test_fill_references_returns_coverage(fill_mock, client, mock_officer_user):
    slots = empty_slot_map()
    slots["s3"] = {
        "content": "คุณสมบัติตาม พ.ร.บ. 2560",
        "status": "reference_only",
        "sources": ["พ.ร.บ."],
    }
    fill_mock.return_value = {"filled_keys": ["s3"], "slot_map": slots}
    project = _make_project(analysis={"analyzed": True, "slot_map": empty_slot_map()}, phase=1)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/intake/fill-references")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["filled_keys"] == ["s3"]
    keys = [row["key"] for row in body["coverage"]]
    assert "s3" in keys
    fill_mock.assert_awaited()


@patch("app.api.v1.endpoints.intake.fill_reference_slot", new_callable=AsyncMock)
def test_fill_reference_single_slot(fill_mock, client, mock_officer_user):
    fill_mock.return_value = {
        "content": "อ้างอิงระเบียบกระทรวงการคลัง",
        "sources": ["ระเบียบ"],
    }
    project = _make_project(analysis={"analyzed": True, "slot_map": empty_slot_map()}, phase=1)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/intake/fill-reference",
        json={"slot_key": "s10"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["slot_key"] == "s10"
    assert "อ้างอิงระเบียบ" in body["content"]
    fill_mock.assert_awaited()


@patch("app.api.v1.endpoints.intake.fill_reference_slot", new_callable=AsyncMock)
def test_fill_reference_skips_filled_fact_slot(fill_mock, client, mock_officer_user):
    fill_mock.return_value = {"content": "ไม่ควรทับ", "sources": ["x"]}
    slots = empty_slot_map()
    slots["s1"] = {"content": "กรมบัญชีกลางจัดซื้อระบบ", "status": "filled", "sources": []}
    project = _make_project(analysis={"analyzed": True, "slot_map": slots}, phase=1)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/intake/fill-reference",
        json={"slot_key": "s1"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["skipped"] is True
    assert body["action"] == "skipped"
    assert "กรมบัญชีกลาง" in body["content"]
    fill_mock.assert_not_called()


def test_fill_reference_rejects_unknown_slot(client, mock_officer_user):
    project = _make_project(analysis={"analyzed": True}, phase=1)
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/intake/fill-reference",
        json={"slot_key": "not-a-slot"},
    )
    assert response.status_code == 400


def test_open_qa_seeds_brief_from_phase1(client, mock_officer_user):
    slots = empty_slot_map()
    slots["s1"] = {
        "content": "กรมบัญชีกลางจัดซื้อระบบบริหารสัญญา",
        "status": "filled",
        "sources": [],
    }
    project = _make_project(
        analysis={"slot_map": slots, "analyzed": True, "gap_questions": ["ขอวงเงิน"]},
        phase=1,
    )
    room = MagicMock()
    room.id = uuid.uuid4()
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    room_result = MagicMock()
    room_result.scalar_one_or_none.return_value = room
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[project_result, room_result])
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    _override_db(mock_db)

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/intake/open-qa")
    assert response.status_code == 200
    brief = response.json()["data"]["brief"]
    assert "กรมบัญชีกลางจัดซื้อระบบบริหารสัญญา" in brief
    assert "สวัสดี" in brief
    mock_db.add.assert_called()
    mock_db.commit.assert_awaited()
    assert project.analysis_json["phase2_briefed"] is True

    mock_db.add.reset_mock()
    mock_db.commit.reset_mock()
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=project)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=room)),
        ]
    )
    again = client.post(f"/api/v1/projects/{PROJECT_ID}/intake/open-qa")
    assert again.status_code == 200
    mock_db.add.assert_not_called()


def test_open_qa_reasks_when_fact_gap_remains(client, mock_officer_user):
    slots = empty_slot_map()
    project = _make_project(
        analysis={
            "slot_map": slots,
            "analyzed": True,
            "phase2_briefed": True,
            "phase2_followup_slot": None,
        },
        phase=2,
    )
    room = MagicMock()
    room.id = uuid.uuid4()
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=project)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=room)),
        ]
    )
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    _override_db(mock_db)

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/intake/open-qa")
    assert response.status_code == 200
    mock_db.add.assert_called()
    seeded = mock_db.add.call_args[0][0]
    assert "s1" in seeded.content
    assert project.analysis_json["phase2_followup_slot"] == "s1"


def test_open_qa_requires_analyze(client, mock_officer_user):
    project = _make_project()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/intake/open-qa")
    assert response.status_code == 400


def test_open_draft_seeds_phase3_brief(client, mock_officer_user):
    project = _make_project(analysis={"analyzed": True}, phase=3)
    room = MagicMock()
    room.id = uuid.uuid4()
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    room_result = MagicMock()
    room_result.scalar_one_or_none.return_value = room
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[project_result, room_result])
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    _override_db(mock_db)

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/intake/open-draft")
    assert response.status_code == 200
    assert "๑๓ หมวด" in response.json()["data"]["brief"]
    mock_db.commit.assert_awaited()
    assert project.analysis_json["phase3_opened"] is True
