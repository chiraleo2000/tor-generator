"""Unit tests for template management endpoints.

Tests cover:
- GET /api/v1/templates (list with role-based filtering)
- POST /api/v1/templates (create template, admin only)
- GET /api/v1/templates/{id} (get detail with role-based access)
- PUT /api/v1/templates/{id} (update, admin only)
- PUT /api/v1/templates/{id}/publish (publish, admin only)
- PUT /api/v1/templates/{id}/unpublish (unpublish with warning, admin only)
- DELETE /api/v1/templates/{id} (delete with warning, admin only)

Validates: Requirements 7.1, 7.2, 7.4, 7.5, 7.6, 7.8
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db
from app.main import app
from app.models.project import Project
from app.models.template import Template
from app.models.template_version import TemplateVersion
from app.models.user import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
TEMPLATE_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")
PROJECT_ID = uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")


def _make_user(user_id=USER_ID, role="officer"):
    """Create a mock User object."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.role = role
    user.email = "test@example.go.th"
    user.name = "Test User"
    return user


def _make_template(
    template_id=TEMPLATE_ID,
    name="เทมเพลต IT",
    industry="it",
    status="published",
    created_by=USER_ID,
):
    """Create a mock Template object."""
    template = MagicMock(spec=Template)
    template.id = template_id
    template.name = name
    template.industry = industry
    template.status = status
    template.section_structure = {"sections": [{"key": "s1", "title": "ความเป็นมา"}]}
    template.placeholder_guidance = {"s1": "อธิบายความเป็นมา"}
    template.created_by = created_by
    template.created_at = datetime(2024, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    template.updated_at = datetime(2024, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    return template


def _make_project(
    project_id=PROJECT_ID,
    owner_id=USER_ID,
    name="โครงการทดสอบ",
    status="draft",
    template_id=TEMPLATE_ID,
):
    """Create a mock Project object."""
    project = MagicMock(spec=Project)
    project.id = project_id
    project.owner_id = owner_id
    project.name = name
    project.status = status
    project.template_id = template_id
    return project


@pytest.fixture(autouse=True)
def setup_app_state():
    """Setup app state and override get_db for tests."""
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
    """Override get_current_user to return an officer user."""
    user = _make_user(role="officer")

    async def override():
        return user

    app.dependency_overrides[get_current_user] = override
    return user


@pytest.fixture
def mock_admin_user():
    """Override get_current_user to return an admin user."""
    user = _make_user(role="admin")

    async def override():
        return user

    app.dependency_overrides[get_current_user] = override
    return user


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def valid_create_body():
    """A valid template creation request body."""
    return {
        "name": "เทมเพลต TOR ระบบ IT",
        "industry": "it",
        "section_structure": {"sections": [{"key": "s1", "title": "ความเป็นมา"}]},
        "placeholder_guidance": {"s1": "อธิบายความเป็นมาของโครงการ"},
    }


# ---------------------------------------------------------------------------
# GET /templates — List templates
# ---------------------------------------------------------------------------


class TestListTemplates:
    """Tests for GET /api/v1/templates."""

    def test_officer_sees_only_published_templates(self, client, mock_officer_user):
        """Officers can only see published templates."""
        published_template = _make_template(status="published")

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [published_template]
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["total"] == 1

    def test_admin_sees_all_templates(self, client, mock_admin_user):
        """Admin can see both draft and published templates."""
        templates = [
            _make_template(status="published"),
            _make_template(
                template_id=uuid.uuid4(), status="draft", name="เทมเพลตร่าง"
            ),
        ]

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = templates
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["total"] == 2

    def test_admin_can_filter_by_status(self, client, mock_admin_user):
        """Admin can filter templates by status."""
        draft_template = _make_template(status="draft")

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [draft_template]
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/templates?status=draft")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_filter_by_industry(self, client, mock_admin_user):
        """Can filter templates by industry."""
        it_template = _make_template(industry="it")

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalars.return_value.all.return_value = [it_template]
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/templates?industry=it")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_invalid_industry_returns_400(self, client, mock_admin_user):
        """Invalid industry filter value returns 400."""
        response = client.get("/api/v1/templates?industry=invalid")
        assert response.status_code == 400

    def test_unauthenticated_returns_401(self, client):
        """Unauthenticated request returns 401."""
        response = client.get("/api/v1/templates")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# POST /templates — Create template (admin only)
# ---------------------------------------------------------------------------


class TestCreateTemplate:
    """Tests for POST /api/v1/templates."""

    def test_admin_creates_template_success(
        self, client, mock_admin_user, valid_create_body
    ):
        """Admin successfully creates a template in draft status."""
        mock_db = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock(
            side_effect=lambda t: _apply_template_defaults(t)
        )

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.post("/api/v1/templates", json=valid_create_body)
        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["name"] == valid_create_body["name"]
        assert data["data"]["status"] == "draft"
        assert data["data"]["industry"] == "it"

    def test_officer_cannot_create_template(
        self, client, mock_officer_user, valid_create_body
    ):
        """Officers are forbidden from creating templates."""
        response = client.post("/api/v1/templates", json=valid_create_body)
        assert response.status_code == 403

    def test_missing_name_returns_422(self, client, mock_admin_user):
        """Missing required field 'name' returns 422."""
        body = {
            "industry": "it",
            "section_structure": {"sections": []},
            "placeholder_guidance": {},
        }
        response = client.post("/api/v1/templates", json=body)
        assert response.status_code == 422

    def test_invalid_industry_returns_422(self, client, mock_admin_user):
        """Invalid industry value returns 422."""
        body = {
            "name": "เทมเพลต",
            "industry": "invalid_industry",
            "section_structure": {"sections": []},
            "placeholder_guidance": {},
        }
        response = client.post("/api/v1/templates", json=body)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /templates/{id} — Get template detail
# ---------------------------------------------------------------------------


class TestGetTemplate:
    """Tests for GET /api/v1/templates/{id}."""

    def test_officer_can_access_published_template(self, client, mock_officer_user):
        """Officer can access a published template."""
        template = _make_template(status="published")
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = template
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/templates/{TEMPLATE_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["id"] == str(TEMPLATE_ID)

    def test_officer_cannot_access_draft_template(self, client, mock_officer_user):
        """Officer cannot see draft templates (returns 404)."""
        template = _make_template(status="draft")
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = template
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/templates/{TEMPLATE_ID}")
        assert response.status_code == 404

    def test_admin_can_access_draft_template(self, client, mock_admin_user):
        """Admin can access draft templates."""
        template = _make_template(status="draft")
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = template
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/templates/{TEMPLATE_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_template_not_found_returns_404(self, client, mock_admin_user):
        """Returns 404 when template doesn't exist."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/templates/{uuid.uuid4()}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /templates/{id} — Update template (admin only)
# ---------------------------------------------------------------------------


class TestUpdateTemplate:
    """Tests for PUT /api/v1/templates/{id}."""

    def test_admin_updates_template_name(self, client, mock_admin_user):
        """Admin can update template name."""
        template = _make_template()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = template
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        body = {"name": "เทมเพลตใหม่"}
        response = client.put(f"/api/v1/templates/{TEMPLATE_ID}", json=body)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_admin_updates_section_structure_creates_version(
        self, client, mock_admin_user
    ):
        """Updating section_structure creates a new template version."""
        template = _make_template()
        mock_db = AsyncMock()

        # First call: select template
        template_result = MagicMock()
        template_result.scalar_one_or_none.return_value = template
        # Second call: max version number
        max_version_result = MagicMock()
        max_version_result.scalar_one.return_value = 1

        mock_db.execute = AsyncMock(
            side_effect=[template_result, max_version_result]
        )
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        body = {"section_structure": {"sections": [{"key": "s1", "title": "ใหม่"}]}}
        response = client.put(f"/api/v1/templates/{TEMPLATE_ID}", json=body)
        assert response.status_code == 200
        # Verify db.add was called (for the new version)
        mock_db.add.assert_called()

    def test_officer_cannot_update_template(self, client, mock_officer_user):
        """Officers cannot update templates."""
        body = {"name": "เทมเพลตใหม่"}
        response = client.put(f"/api/v1/templates/{TEMPLATE_ID}", json=body)
        assert response.status_code == 403

    def test_update_empty_body_returns_400(self, client, mock_admin_user):
        """Empty update body returns 400."""
        template = _make_template()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = template
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.put(f"/api/v1/templates/{TEMPLATE_ID}", json={})
        assert response.status_code == 400

    def test_update_template_not_found(self, client, mock_admin_user):
        """Returns 404 when template doesn't exist."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        body = {"name": "เทมเพลตใหม่"}
        response = client.put(f"/api/v1/templates/{uuid.uuid4()}", json=body)
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PUT /templates/{id}/publish — Publish template
# ---------------------------------------------------------------------------


class TestPublishTemplate:
    """Tests for PUT /api/v1/templates/{id}/publish."""

    def test_publish_draft_template_success(self, client, mock_admin_user):
        """Successfully publish a draft template."""
        template = _make_template(status="draft")
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = template
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.put(f"/api/v1/templates/{TEMPLATE_ID}/publish")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_publish_already_published_returns_400(self, client, mock_admin_user):
        """Publishing an already published template returns 400."""
        template = _make_template(status="published")
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = template
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.put(f"/api/v1/templates/{TEMPLATE_ID}/publish")
        assert response.status_code == 400

    def test_publish_template_not_found(self, client, mock_admin_user):
        """Returns 404 when template doesn't exist."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.put(f"/api/v1/templates/{uuid.uuid4()}/publish")
        assert response.status_code == 404

    def test_officer_cannot_publish(self, client, mock_officer_user):
        """Officers cannot publish templates."""
        response = client.put(f"/api/v1/templates/{TEMPLATE_ID}/publish")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# PUT /templates/{id}/unpublish — Unpublish template
# ---------------------------------------------------------------------------


class TestUnpublishTemplate:
    """Tests for PUT /api/v1/templates/{id}/unpublish."""

    def test_unpublish_without_affected_projects(self, client, mock_admin_user):
        """Unpublish succeeds when no projects reference the template."""
        template = _make_template(status="published")
        mock_db = AsyncMock()

        # First call: select template
        template_result = MagicMock()
        template_result.scalar_one_or_none.return_value = template
        # Second call: select affected projects (none)
        projects_result = MagicMock()
        projects_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[template_result, projects_result]
        )
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.put(f"/api/v1/templates/{TEMPLATE_ID}/unpublish")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_unpublish_with_affected_projects_returns_warning(
        self, client, mock_admin_user
    ):
        """Returns warning when affected projects exist and confirm=false."""
        template = _make_template(status="published")
        affected_project = _make_project()

        mock_db = AsyncMock()
        template_result = MagicMock()
        template_result.scalar_one_or_none.return_value = template
        projects_result = MagicMock()
        projects_result.scalars.return_value.all.return_value = [affected_project]

        mock_db.execute = AsyncMock(
            side_effect=[template_result, projects_result]
        )

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.put(f"/api/v1/templates/{TEMPLATE_ID}/unpublish")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "warning" in data["data"]
        assert data["data"]["affected_count"] == 1

    def test_unpublish_with_confirm_proceeds(self, client, mock_admin_user):
        """Unpublish succeeds when confirm=true despite affected projects."""
        template = _make_template(status="published")
        affected_project = _make_project()

        mock_db = AsyncMock()
        template_result = MagicMock()
        template_result.scalar_one_or_none.return_value = template
        projects_result = MagicMock()
        projects_result.scalars.return_value.all.return_value = [affected_project]

        mock_db.execute = AsyncMock(
            side_effect=[template_result, projects_result]
        )
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.put(
            f"/api/v1/templates/{TEMPLATE_ID}/unpublish?confirm=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        # Should not have warning since we confirmed
        assert "warning" not in data["data"] or data["data"].get("status") == "draft"

    def test_unpublish_already_draft_returns_400(self, client, mock_admin_user):
        """Unpublishing a draft template returns 400."""
        template = _make_template(status="draft")
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = template
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.put(f"/api/v1/templates/{TEMPLATE_ID}/unpublish")
        assert response.status_code == 400

    def test_officer_cannot_unpublish(self, client, mock_officer_user):
        """Officers cannot unpublish templates."""
        response = client.put(f"/api/v1/templates/{TEMPLATE_ID}/unpublish")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# DELETE /templates/{id} — Delete template
# ---------------------------------------------------------------------------


class TestDeleteTemplate:
    """Tests for DELETE /api/v1/templates/{id}."""

    def test_delete_template_without_affected_projects(self, client, mock_admin_user):
        """Delete succeeds when no projects reference the template."""
        template = _make_template()
        mock_db = AsyncMock()

        # First call: select template
        template_result = MagicMock()
        template_result.scalar_one_or_none.return_value = template
        # Second call: select affected projects (none)
        projects_result = MagicMock()
        projects_result.scalars.return_value.all.return_value = []
        # Third call: select template versions
        versions_result = MagicMock()
        versions_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[template_result, projects_result, versions_result]
        )
        mock_db.delete = AsyncMock()
        mock_db.flush = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.delete(f"/api/v1/templates/{TEMPLATE_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "ลบเทมเพลตเรียบร้อย" in data["data"]["message"]

    def test_delete_with_affected_projects_returns_warning(
        self, client, mock_admin_user
    ):
        """Returns warning when affected projects exist and confirm=false."""
        template = _make_template()
        affected_project = _make_project()

        mock_db = AsyncMock()
        template_result = MagicMock()
        template_result.scalar_one_or_none.return_value = template
        projects_result = MagicMock()
        projects_result.scalars.return_value.all.return_value = [affected_project]

        mock_db.execute = AsyncMock(
            side_effect=[template_result, projects_result]
        )

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.delete(f"/api/v1/templates/{TEMPLATE_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "warning" in data["data"]
        assert data["data"]["affected_count"] == 1

    def test_delete_with_confirm_proceeds(self, client, mock_admin_user):
        """Delete succeeds when confirm=true despite affected projects."""
        template = _make_template()
        affected_project = _make_project()

        mock_db = AsyncMock()
        template_result = MagicMock()
        template_result.scalar_one_or_none.return_value = template
        projects_result = MagicMock()
        projects_result.scalars.return_value.all.return_value = [affected_project]
        # Select affected project for nullification
        proj_update_result = MagicMock()
        proj_update_result.scalar_one_or_none.return_value = affected_project
        # Select template versions
        versions_result = MagicMock()
        versions_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[
                template_result,
                projects_result,
                proj_update_result,
                versions_result,
            ]
        )
        mock_db.delete = AsyncMock()
        mock_db.flush = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.delete(f"/api/v1/templates/{TEMPLATE_ID}?confirm=true")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "ลบเทมเพลตเรียบร้อย" in data["data"]["message"]
        assert data["data"]["had_affected_projects"] is True

    def test_delete_template_not_found(self, client, mock_admin_user):
        """Returns 404 when template doesn't exist."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.delete(f"/api/v1/templates/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_officer_cannot_delete_template(self, client, mock_officer_user):
        """Officers cannot delete templates."""
        response = client.delete(f"/api/v1/templates/{TEMPLATE_ID}")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_template_defaults(template):
    """Apply defaults to a real Template instance after flush/refresh."""
    if not hasattr(template, "id") or template.id is None:
        template.id = uuid.uuid4()
    if not hasattr(template, "created_at") or template.created_at is None:
        template.created_at = datetime.now(timezone.utc)
    if not hasattr(template, "updated_at") or template.updated_at is None:
        template.updated_at = datetime.now(timezone.utc)
