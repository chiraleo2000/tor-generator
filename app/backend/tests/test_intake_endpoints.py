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


def test_coverage_project_not_found(client, mock_officer_user):
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)
    response = client.get(f"/api/v1/projects/{PROJECT_ID}/intake/coverage")
    assert response.status_code == 404


def test_intake_upload_skips_empty_and_rejects_oversize(client, mock_officer_user):
    project = _make_project()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    empty = client.post(
        f"/api/v1/projects/{PROJECT_ID}/intake/upload",
        files={"files": ("empty.txt", b"", "text/plain")},
    )
    assert empty.status_code == 200
    assert empty.json()["data"]["count"] == 0

    with patch("app.api.v1.endpoints.intake.INTAKE_MAX_UPLOAD_BYTES", 8):
        huge = client.post(
            f"/api/v1/projects/{PROJECT_ID}/intake/upload",
            files={"files": ("big.txt", b"x" * 20, "text/plain")},
        )
    assert huge.status_code == 400


@patch("app.api.v1.endpoints.intake.extract_text")
@patch("app.api.v1.endpoints.intake.unlink_path", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.intake.write_temp_bytes", new_callable=AsyncMock)
def test_intake_upload_marks_empty_ocr(
    write_tmp, unlink_mock, extract_mock, client, mock_officer_user
):
    extracted = MagicMock()
    extracted.text = "   "
    extracted.method = "ocr"
    extracted.warnings = ["OCR timed out"]
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
        files={"files": ("scan.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 200
    assert project.analysis_json["intake_files"][0]["status"] == "empty"


def test_confirm_phase4_requires_confirm_flag(client, mock_officer_user):
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
    _override_db(mock_db)

    response = client.post(
        f"/api/v1/projects/{PROJECT_ID}/intake/confirm-phase4",
        json={"confirm": False},
    )
    assert response.status_code == 400


def test_confirm_phase4_attests_sections(client, mock_officer_user):
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
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    section = MagicMock()
    sec_result = MagicMock()
    sec_result.scalars.return_value.all.return_value = [section]
    mock_db.execute = AsyncMock(side_effect=[project_result, sec_result])
    _override_db(mock_db)

    with patch("app.api.v1.endpoints.intake.attest_hitl_sections") as attest:
        response = client.post(
            f"/api/v1/projects/{PROJECT_ID}/intake/confirm-phase4",
            json={"confirm": True},
        )
    assert response.status_code == 200
    attest.assert_called_once()


def test_qa_next_advances_asking_slot(client, mock_officer_user):
    project = _make_project(
        analysis={"slot_map": empty_slot_map(), "current_asking_slot": None},
        phase=2,
    )
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/intake/qa-next")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["current_slot"] == "s1"
    assert body["all_fact_filled"] is False
    mock_db.flush.assert_awaited()


def test_open_draft_requires_analyze(client, mock_officer_user):
    project = _make_project()
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=mock_result)
    _override_db(mock_db)
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/intake/open-draft")
    assert response.status_code == 400


def test_open_draft_skips_seed_when_already_opened(client, mock_officer_user):
    project = _make_project(analysis={"analyzed": True, "phase3_opened": True}, phase=3)
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
    _override_db(mock_db)
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/intake/open-draft")
    assert response.status_code == 200
    mock_db.add.assert_not_called()


def test_intake_helper_pack_flag_and_payload():
    from app.api.v1.endpoints.intake import (
        _asking_key,
        _chat_done_payload,
        _flag_analysis,
        _gap_questions_for,
        _intake_pack,
    )

    pack, names = _intake_pack("not-a-list")
    assert pack == ""
    assert names == []
    pack, names = _intake_pack(
        [{"text": "วงเงินโครงการ", "name": "a.txt"}, "skip", {"text": "  "}]
    )
    assert "วงเงินโครงการ" in pack
    assert "a.txt" in names
    assert _asking_key(1) is None
    assert _asking_key("s1") == "s1"
    questions = _gap_questions_for(empty_slot_map())
    assert any("s1" in item for item in questions)
    payload = _chat_done_payload(
        content="ตอบ",
        slot_map=empty_slot_map(),
        filled_keys=["s1"],
        asking_key="s2",
        extra={"graph_degraded": True},
    )
    assert payload["graph_degraded"] is True
    project = MagicMock(spec=Project)
    _flag_analysis(project)


@pytest.mark.asyncio
async def test_ensure_intake_room_creates_when_missing():
    from app.api.v1.endpoints.intake import _ensure_intake_room

    mock_db = AsyncMock()
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=missing)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    project = _make_project()
    room = await _ensure_intake_room(mock_db, project, _make_user())
    mock_db.add.assert_called_once()
    assert room.kind == "draft_intake"
    assert str(PROJECT_ID) in str(room.project_id)


@pytest.mark.asyncio
async def test_persist_heuristic_and_apply_analyze():
    from app.api.v1.endpoints.intake import _apply_analyze_result, _persist_heuristic_slot_map

    project = _make_project()
    mock_db = AsyncMock()
    slots = empty_slot_map()
    slots["s1"] = {"content": "โครงการ", "status": "filled", "sources": []}
    await _persist_heuristic_slot_map(project, mock_db, slots)
    assert project.analysis_json["analyzed"] is True
    mock_db.flush.assert_awaited()
    mock_db.commit.assert_awaited()

    result = {"slot_map": slots, "gap_questions": ["ขอวงเงิน"]}
    analysis = _apply_analyze_result(project, result)
    assert analysis["analyzed"] is True
    assert analysis["standard_fill_keys"] == []


@pytest.mark.asyncio
async def test_retrieve_legal_context_unpacks_three_and_four_tuple():
    from app.api.v1.endpoints.intake import _retrieve_legal_context
    from app.rag.retrieval import RetrievalResult, RetrievedChunk

    empty, cites, degraded = await _retrieve_legal_context("q", USER_ID, "both", False)
    assert empty == ""
    assert cites == []
    assert degraded is False

    chunk = RetrievedChunk(id="1", text="กฎหมาย", score=0.9, source_document="พ.ร.บ.")
    result = RetrievalResult(chunks=[chunk], query="q", top_k=3, actual_count=1)
    with patch(
        "app.api.v1.endpoints.intake.hybrid_retrieve",
        new_callable=AsyncMock,
        return_value=(result, [{"label": "พ.ร.บ."}], True),
    ):
        context, citations, degraded = await _retrieve_legal_context(
            "งวด", USER_ID, "weird", True
        )
    assert "กฎหมาย" in context
    assert citations
    assert degraded is True

    with patch(
        "app.api.v1.endpoints.intake.hybrid_retrieve",
        new_callable=AsyncMock,
        return_value=(result, [{"label": "mcp"}], False, True),
    ):
        context, citations, degraded = await _retrieve_legal_context(
            "งวด", USER_ID, "mine", True
        )
    assert degraded is False
    assert citations[0]["label"] == "mcp"


@patch("app.api.v1.endpoints.intake.fill_reference_slot", new_callable=AsyncMock)
def test_intake_chat_fill_reference_slot(
    fill_mock, client, mock_officer_user, monkeypatch
):
    fill_mock.return_value = {"content": "มาตรฐานกลาง", "sources": ["พ.ร.บ."]}
    project = _make_project(analysis={"slot_map": empty_slot_map(), "analyzed": True})
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
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
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

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(app.state, "db_session_factory", lambda: _CM(), raising=False)

    with patch(
        "app.api.v1.endpoints.intake.apply_reference_to_slot", return_value="filled"
    ):
        with client.stream(
            "POST",
            f"/api/v1/projects/{PROJECT_ID}/intake/chat",
            json={"content": "ดึงอ้างอิงกฎหมายให้ s10"},
        ) as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")
    assert response.status_code == 200
    assert "event: done" in body
    assert "s10" in body or "มาตรฐาน" in body or "ใส่มาตรฐาน" in body


def test_intake_chat_fill_reference_prompt(client, mock_officer_user, monkeypatch):
    project = _make_project(analysis={"slot_map": empty_slot_map(), "analyzed": True})
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
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
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

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(app.state, "db_session_factory", lambda: _CM(), raising=False)

    with patch(
        "app.api.v1.endpoints.intake.parse_fill_reference_request", return_value=None
    ), patch(
        "app.api.v1.endpoints.intake.apply_chat_answer_to_slots", return_value=[]
    ):
        with client.stream(
            "POST",
            f"/api/v1/projects/{PROJECT_ID}/intake/chat",
            json={"content": "ดึงอ้างอิงกฎหมาย"},
        ) as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "event: done" in body
    assert "ดึงอ้างอิง" in body


@patch("app.api.v1.endpoints.intake.hybrid_retrieve", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.intake.ProviderFactory")
def test_intake_chat_llm_path_unpacks_mcp_degraded(
    factory, retrieve, client, mock_officer_user, monkeypatch
):
    from app.rag.retrieval import RetrievalResult, RetrievedChunk

    project = _make_project(analysis={"slot_map": empty_slot_map(), "analyzed": True})
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
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
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

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(app.state, "db_session_factory", lambda: _CM(), raising=False)

    chunk = RetrievedChunk(id="1", text="อ้างอิงกฎหมาย", score=0.8, source_document="พ.ร.บ.")
    retrieve.return_value = (
        RetrievalResult(chunks=[chunk], query="q", top_k=3, actual_count=1),
        [{"label": "พ.ร.บ."}],
        True,
        True,
    )

    async def fake_stream(*_args, **_kwargs):
        yield "รับทราบ"

    mock_llm = MagicMock()
    mock_llm.stream = fake_stream
    factory.return_value.get_llm.return_value = mock_llm

    with patch(
        "app.api.v1.endpoints.intake.apply_chat_answer_to_slots", return_value=[]
    ), patch(
        "app.api.v1.endpoints.intake.parse_fill_reference_request", return_value=None
    ), patch(
        "app.api.v1.endpoints.intake.is_fill_reference_request", return_value=False
    ):
        with client.stream(
            "POST",
            f"/api/v1/projects/{PROJECT_ID}/intake/chat",
            json={
                "content": "ขอคำแนะนำสั้น ๆ",
                "attach_legal_reference": True,
                "search_scope": "both",
            },
        ) as response:
            body = b"".join(response.iter_bytes()).decode("utf-8")
    assert response.status_code == 200
    assert "event: done" in body
    assert "graph_degraded" in body
    retrieve.assert_awaited()


@pytest.mark.asyncio
async def test_run_intake_llm_job_empty_stream_uses_template():
    import asyncio
    from contextlib import asynccontextmanager

    from app.api.v1.endpoints.intake import _IntakeLlmWork, _run_intake_llm_job

    request = MagicMock()
    request.app.state.redis = None
    request.app.state.db_session_factory = MagicMock()
    work = _IntakeLlmWork(
        request=request,
        project=_make_project(),
        room=MagicMock(id=uuid.uuid4()),
        analysis={"current_asking_slot": "s1"},
        slot_map=empty_slot_map(),
        filled_keys=[],
        asking_key="s1",
        all_filled_now=False,
        request_id="rid",
        attached="",
        citations=[],
        degraded=False,
        user_prompt="ถาม",
    )
    queue: asyncio.Queue = asyncio.Queue()

    class _LLM:
        async def stream(self, *_args, **_kwargs):
            if False:
                yield ""
            return

    @asynccontextmanager
    async def admit_ok(*_args, **_kwargs):
        yield "rid"

    with patch("app.api.v1.endpoints.intake.admit", admit_ok), patch(
        "app.api.v1.endpoints.intake.ProviderFactory"
    ) as factory, patch(
        "app.api.v1.endpoints.intake._persist_llm_reply", new_callable=AsyncMock
    ):
        factory.return_value.get_llm.return_value = _LLM()
        await _run_intake_llm_job(work, queue)
    events = []
    while not queue.empty():
        events.append(await queue.get())
    done = [item for item in events if item and item[0] == "done"]
    assert done
    assert done[0][1]["content"]
