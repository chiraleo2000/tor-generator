"""Unit tests for admin user management endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.constants import DISABLED_EMAIL_PREFIX
from app.deps import get_current_user, get_db
from app.main import app
from app.models.user import User


def _admin_user():
    user = MagicMock(spec=User)
    user.id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    user.role = "admin"
    user.email = "admin@example.go.th"
    user.name = "Admin"
    user.organization = "กระทรวง"
    user.created_at = datetime(2024, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    return user


def _listed_user(**overrides):
    user = MagicMock(spec=User)
    user.id = uuid.UUID("22222222-2222-2222-2222-222222222222")
    user.role = "officer"
    user.email = "officer@example.go.th"
    user.name = "เจ้าหน้าที่"
    user.organization = "กรม"
    user.created_at = datetime(2024, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    for key, value in overrides.items():
        setattr(user, key, value)
    return user


@pytest.fixture
def admin_client():
    app.state.db_session_factory = None
    app.state.db_engine = None
    app.state.redis = None
    app.state.minio = None

    async def override_user():
        return _admin_user()

    app.dependency_overrides[get_current_user] = override_user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _override_db(session):
    async def override():
        yield session

    app.dependency_overrides[get_db] = override


def test_list_users_masks_disabled_prefix(admin_client):
    listed = _listed_user(email=f"{DISABLED_EMAIL_PREFIX}officer@example.go.th")
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [listed]
    mock_db.execute = AsyncMock(return_value=result)
    _override_db(mock_db)

    response = admin_client.get("/api/v1/admin/users")
    assert response.status_code == 200
    item = response.json()["data"]["items"][0]
    assert item["email"] == "officer@example.go.th"
    assert item["disabled"] is True


def test_create_user_success(admin_client):
    mock_db = AsyncMock()
    existing = MagicMock()
    existing.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=existing)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = admin_client.post(
        "/api/v1/admin/users",
        json={
            "name": "ผู้ใช้ใหม่",
            "email": "new.user@example.go.th",
            "password": "Str0ng@Pass",
            "organization": "กรมบัญชีกลาง",
            "role": "reviewer",
        },
    )
    assert response.status_code == 201
    assert response.json()["data"]["email"] == "new.user@example.go.th"
    mock_db.add.assert_called()


def test_create_user_rejects_bad_role_and_duplicate(admin_client):
    mock_db = AsyncMock()
    _override_db(mock_db)
    bad_role = admin_client.post(
        "/api/v1/admin/users",
        json={
            "name": "ผู้ใช้",
            "email": "a@example.go.th",
            "password": "Str0ng@Pass",
            "organization": "กรม",
            "role": "superuser",
        },
    )
    assert bad_role.status_code == 400
    assert bad_role.json()["error"]["field"] == "role"

    existing = MagicMock()
    existing.scalar_one_or_none.return_value = _listed_user()
    mock_db.execute = AsyncMock(return_value=existing)
    duplicate = admin_client.post(
        "/api/v1/admin/users",
        json={
            "name": "ผู้ใช้",
            "email": "officer@example.go.th",
            "password": "Str0ng@Pass",
            "organization": "กรม",
            "role": "officer",
        },
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["error"]["field"] == "email"


def test_create_user_rejects_weak_password(admin_client):
    mock_db = AsyncMock()
    existing = MagicMock()
    existing.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=existing)
    _override_db(mock_db)
    response = admin_client.post(
        "/api/v1/admin/users",
        json={
            "name": "ผู้ใช้",
            "email": "weak@example.go.th",
            "password": "short",
            "organization": "กรม",
            "role": "officer",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["field"] == "password"


def test_update_user_not_found_and_disable(admin_client):
    user_id = "22222222-2222-2222-2222-222222222222"
    mock_db = AsyncMock()
    missing = MagicMock()
    missing.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=missing)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)
    not_found = admin_client.put(f"/api/v1/admin/users/{user_id}", json={"role": "admin"})
    assert not_found.status_code == 404

    target = _listed_user()
    found = MagicMock()
    found.scalar_one_or_none.return_value = target
    mock_db.execute = AsyncMock(return_value=found)
    disabled = admin_client.put(
        f"/api/v1/admin/users/{user_id}",
        json={"role": "reviewer", "disabled": True},
    )
    assert disabled.status_code == 200
    assert target.role == "reviewer"
    assert target.email.startswith(DISABLED_EMAIL_PREFIX)

    found.scalar_one_or_none.return_value = target
    enabled = admin_client.put(
        f"/api/v1/admin/users/{user_id}",
        json={"disabled": False},
    )
    assert enabled.status_code == 200
    assert not target.email.startswith(DISABLED_EMAIL_PREFIX)


def test_update_user_rejects_invalid_role(admin_client):
    user_id = "22222222-2222-2222-2222-222222222222"
    mock_db = AsyncMock()
    found = MagicMock()
    found.scalar_one_or_none.return_value = _listed_user()
    mock_db.execute = AsyncMock(return_value=found)
    _override_db(mock_db)
    response = admin_client.put(f"/api/v1/admin/users/{user_id}", json={"role": "root"})
    assert response.status_code == 400
    assert response.json()["error"]["field"] == "role"
