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


@patch("app.api.v1.endpoints.intake.apply_slot_map_to_sections", new_callable=AsyncMock)
def test_confirm_ready_sets_phase_two(apply_sections, client, mock_officer_user):
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
    assert project.current_phase >= 2
    assert project.analysis_json["ready_to_compose"] is True
    apply_sections.assert_awaited()


@patch("app.api.v1.endpoints.intake.ingest_file_bytes", new_callable=AsyncMock)
def test_intake_text_appends_pack(ingest_mock, client, mock_officer_user):
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
    ingest_mock.assert_awaited()
    texts = project.extracted_fields["intake_texts"]
    assert texts[0]["text"].startswith("โครงการทดสอบ")
