"""Focused tests for Phase 3 cost worksheet, training scope, and product search."""

from __future__ import annotations

import sys
import types
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db
from app.main import app
from app.models.project import Project
from app.models.user import User
from app.services.cost_training import (
    category_has_training,
    cost_worksheet_of,
    merge_cost_worksheet,
    normalize_cost_worksheet,
    training_scope_prose,
)
from app.services.draft_chat_service import parse_draft_message_intent
from app.services.draft_product_search import (
    format_search_reference,
    normalize_search_hits,
    run_product_search,
)

USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
PROJECT_ID = uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")


def _stub_search_web(monkeypatch, hits):
    async def fake_search_web(query, **_kwargs):
        fake_search_web.queries.append(query)
        return hits

    fake_search_web.queries = []
    module = types.ModuleType("app.services.web_search")
    module.search_web = fake_search_web
    monkeypatch.setitem(sys.modules, "app.services.web_search", module)
    return fake_search_web


def test_cost_worksheet_is_not_announced_price():
    sheet = normalize_cost_worksheet(
        {
            "license": "1000",
            "labor": 2000,
            "maintenance": 300,
            "training": 700,
            "announcedPrice": 999999,
            "ราคากลาง": 888888,
        }
    )
    assert sheet["equipment"] == 1000
    assert sheet["personnel"] == 2000
    assert sheet["procurement"] == 300
    assert sheet["training"] == 700
    assert sheet["total"] == 4000
    assert sheet["is_announced_price"] is False
    assert "ราคากลาง" in sheet["label"]
    assert "announcedPrice" not in sheet
    assert "ราคากลาง" not in sheet
    assert sheet["equipment"] != 999999


def test_merge_cost_worksheet_keeps_existing_analysis():
    merged = merge_cost_worksheet(
        {"slot_map": {"s1": {"content": "คงไว้"}}, "ready_to_compose": True},
        {"license": 10, "labor": 20, "maintenance": 0, "training": 5},
    )
    assert merged["slot_map"]["s1"]["content"] == "คงไว้"
    assert merged["ready_to_compose"] is True
    assert merged["cost_worksheet"]["total"] == 35
    assert merged["cost_worksheet"]["is_announced_price"] is False


def test_training_scope_from_hire_develop_and_buy_goods_profiles():
    assert category_has_training("hire_develop") is True
    assert category_has_training("buy_goods") is True
    assert category_has_training("construction") is False
    prose = training_scope_prose(
        {"cohorts": "2", "hours": "12", "attendees": "30", "documents": "คู่มือผู้ใช้, รายงานอบรม"},
        project_type="hire_develop",
    )
    assert "2 รุ่น" in prose
    assert "12 ชั่วโมง" in prose
    assert "30 คน" in prose
    assert "คู่มือผู้ใช้" in prose
    assert "การฝึกอบรม" in prose


def test_parse_product_search_and_insert_intents():
    intent, _, _ = parse_draft_message_intent("ขอสเปกเซิร์ฟเวอร์จากผู้ขาย")
    assert intent == "product_search"
    intent, key, _ = parse_draft_message_intent("ยืนยันแทรกแหล่งค้นหา หมวด 4")
    assert intent == "insert_search"
    assert key == "s4"
    intent, key, _ = parse_draft_message_intent("วงเงินงบประมาณให้ระบุแหล่งงบด้วย")
    assert intent == "freeform"
    assert key == "s6"


@pytest.mark.asyncio
async def test_run_product_search_uses_shared_search_web(monkeypatch):
    fake = _stub_search_web(
        monkeypatch,
        [{"title": "เซิร์ฟเวอร์อ้างอิง", "url": "https://example.go.th/spec", "snippet": "สเปกกลาง"}],
    )
    hits = await run_product_search("สเปกเซิร์ฟเวอร์ราชการ")
    assert fake.queries == ["สเปกเซิร์ฟเวอร์ราชการ"]
    assert hits == [
        {
            "title": "เซิร์ฟเวอร์อ้างอิง",
            "url": "https://example.go.th/spec",
            "snippet": "สเปกกลาง",
        }
    ]


def test_format_search_reference_is_not_brand_locked():
    text = format_search_reference(
        [{"title": "Oracle Database", "url": "https://example.com/o", "snippet": "license"}],
        query="สเปกฐานข้อมูล",
    )
    assert "ข้อมูลอ้างอิง" in text
    assert "ไม่ใช่สเปกที่ผูกยี่ห้อ" in text
    assert "https://example.com/o" in text


def test_normalize_search_hits_keeps_title_url_snippet_only():
    hits = normalize_search_hits(
        [
            {"title": "A", "url": "https://a.example", "snippet": "one", "score": 9},
            {"title": "A", "url": "https://a.example", "snippet": "dup"},
        ]
    )
    assert hits == [{"title": "A", "url": "https://a.example", "snippet": "one"}]


def _make_user():
    user = MagicMock(spec=User)
    user.id = USER_ID
    user.role = "officer"
    user.email = "test@example.go.th"
    user.name = "Test User"
    return user


def _make_project(*, analysis=None, project_type="hire_develop"):
    project = MagicMock(spec=Project)
    project.id = PROJECT_ID
    project.owner_id = USER_ID
    project.name = "โครงการทดสอบ"
    project.analysis_json = analysis or {}
    project.extracted_fields = {}
    project.current_phase = 3
    project.project_type = project_type
    project.created_at = datetime(2026, 8, 24, tzinfo=timezone.utc)
    project.updated_at = datetime(2026, 8, 24, tzinfo=timezone.utc)
    return project


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    app.state.db_session_factory = None
    app.state.db_engine = None
    app.state.redis = None
    app.state.minio = None

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_get_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def officer(client):
    user = _make_user()

    async def override():
        return user

    app.dependency_overrides[get_current_user] = override
    return user


def _override_db(mock_db):
    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db


def test_cost_worksheet_endpoints_persist_analysis(client, officer):
    project = _make_project(analysis={"slot_map": {"s6": {"content": "งบ"}}})
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    listed = client.get(f"/api/v1/projects/{PROJECT_ID}/draft-chat/cost-worksheet")
    assert listed.status_code == 200
    assert listed.json()["data"]["is_announced_price"] is False

    saved = client.put(
        f"/api/v1/projects/{PROJECT_ID}/draft-chat/cost-worksheet",
        json={"license": 100, "labor": 200, "maintenance": 50, "training": 25},
    )
    assert saved.status_code == 200
    payload = saved.json()["data"]
    assert payload["total"] == 375
    assert payload["is_announced_price"] is False
    assert project.analysis_json["slot_map"]["s6"]["content"] == "งบ"
    assert cost_worksheet_of(project.analysis_json)["personnel"] == 200


def test_product_search_message_does_not_insert_until_confirm(client, officer, monkeypatch):
    _stub_search_web(
        monkeypatch,
        [{"title": "สินค้าอ้างอิง", "url": "https://example.go.th/p", "snippet": "สเปกกลาง"}],
    )
    project = _make_project()
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=result)
    _override_db(mock_db)
    persist = AsyncMock()
    persist.commit = AsyncMock()
    persist.add = MagicMock()
    persist.execute = AsyncMock(return_value=result)
    monkeypatch.setattr(
        app.state,
        "db_session_factory",
        lambda: types.SimpleNamespace(
            __aenter__=AsyncMock(return_value=persist),
            __aexit__=AsyncMock(return_value=False),
        ),
        raising=False,
    )

    with client.stream(
        "POST",
        f"/api/v1/projects/{PROJECT_ID}/draft-chat/message",
        json={"content": "ขอสเปกเครื่องเซิร์ฟเวอร์จากผู้ขาย"},
    ) as response:
        body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "event: product_search" in body
    assert "สินค้าอ้างอิง" in body
    assert "pending_insert" in body
    assert "event: section_done" not in body
    persist.add.assert_not_called()
    persist.commit.assert_not_called()


def test_insert_search_without_hits_is_rejected(client, officer, monkeypatch):
    project = _make_project()
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = project
    mock_db.execute = AsyncMock(return_value=result)
    _override_db(mock_db)
    persist = AsyncMock()
    persist.commit = AsyncMock()
    persist.add = MagicMock()
    monkeypatch.setattr(
        app.state,
        "db_session_factory",
        lambda: types.SimpleNamespace(
            __aenter__=AsyncMock(return_value=persist),
            __aexit__=AsyncMock(return_value=False),
        ),
        raising=False,
    )

    with client.stream(
        "POST",
        f"/api/v1/projects/{PROJECT_ID}/draft-chat/message",
        json={"content": "ยืนยันแทรกแหล่งค้นหา", "confirm_insert": True, "search_hits": []},
    ) as response:
        body = b"".join(response.iter_bytes()).decode("utf-8")
    assert "ยืนยันก่อนแทรกลง TOR" in body
    persist.add.assert_not_called()
