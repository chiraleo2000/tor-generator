"""Unit tests for project CRUD endpoints.

Tests cover:
- GET /api/v1/projects (list with pagination and status filtering)
- POST /api/v1/projects (create project)
- GET /api/v1/projects/{id} (get detail)
- PUT /api/v1/projects/{id} (update)
- DELETE /api/v1/projects/{id} (archive)
- GET /api/v1/projects/{id}/versions (list versions)
- POST /api/v1/projects/{id}/versions/{v}/restore (restore)

Validates: Requirements 9.4, 9.5, 9.6, 9.9
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.projects import officer_can_submit
from app.deps import get_current_user, get_db
from app.main import app
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.user import User


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
OTHER_USER_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")
PROJECT_ID = uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")


def _make_user(user_id=USER_ID, role="officer"):
    """Create a mock User object."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.role = role
    user.email = "test@example.go.th"
    user.name = "Test User"
    return user


def _make_project(
    project_id=PROJECT_ID,
    owner_id=USER_ID,
    name="โครงการทดสอบ",
    ministry="กระทรวงทดสอบ",
    budget=5000000,
    project_type="it",
    status="draft",
    current_step=1,
    quality_score=None,
    template_id=None,
    current_phase=0,
):
    """Create a mock Project object."""
    project = MagicMock(spec=Project)
    project.id = project_id
    project.owner_id = owner_id
    project.name = name
    project.ministry = ministry
    project.budget = budget
    project.project_type = project_type
    project.status = status
    project.current_step = current_step
    project.current_phase = current_phase
    project.analysis_json = {}
    project.extracted_fields = {}
    project.quality_score = quality_score
    project.template_id = template_id
    project.created_at = datetime(2024, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    project.updated_at = datetime(2024, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    return project


def _make_version(
    version_id=None,
    project_id=PROJECT_ID,
    version_number=1,
    step_number=1,
    snapshot_data=None,
):
    """Create a mock ProjectVersion object."""
    version = MagicMock(spec=ProjectVersion)
    version.id = version_id or uuid.uuid4()
    version.project_id = project_id
    version.version_number = version_number
    version.step_number = step_number
    version.snapshot_data = snapshot_data or {"step_1": {"name": "test"}}
    version.created_at = datetime(2024, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    return version


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
    """A valid project creation request body."""
    return {
        "name": "โครงการจัดซื้อระบบคอมพิวเตอร์",
        "ministry": "กระทรวงการพัฒนาสังคมและความมั่นคงของมนุษย์",
        "budget": 5000000,
        "project_type": "it",
    }


# ---------------------------------------------------------------------------
# POST /projects — Create project
# ---------------------------------------------------------------------------


class TestCreateProject:
    """Tests for POST /api/v1/projects."""

    def test_create_project_success(self, client, mock_officer_user, valid_create_body):
        """Successfully creates a project and returns 201."""
        mock_project = _make_project()

        with patch("app.api.v1.endpoints.projects.select") as mock_select:
            # Mock the DB session behavior in the dependency
            mock_db = AsyncMock()
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()
            mock_db.refresh = AsyncMock(side_effect=lambda p: _apply_defaults(p))

            async def override_db():
                yield mock_db

            app.dependency_overrides[get_db] = override_db

            response = client.post("/api/v1/projects", json=valid_create_body)

        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["name"] == valid_create_body["name"]
        assert data["data"]["status"] == "draft"
        assert data["data"]["current_step"] == 1

    def test_create_project_missing_name_returns_422(self, client, mock_officer_user):
        """Missing required field 'name' returns 422."""
        body = {
            "ministry": "กระทรวงทดสอบ",
            "budget": 5000000,
        }
        response = client.post("/api/v1/projects", json=body)
        assert response.status_code == 422

    def test_create_project_invalid_budget_returns_422(self, client, mock_officer_user):
        """Budget must be positive integer."""
        body = {
            "name": "โครงการทดสอบ",
            "ministry": "กระทรวงทดสอบ",
            "budget": -100,
            "project_type": "it",
        }
        response = client.post("/api/v1/projects", json=body)
        assert response.status_code == 422

    def test_create_project_invalid_type_returns_422(self, client, mock_officer_user):
        """Invalid project_type value returns 422."""
        body = {
            "name": "โครงการทดสอบ",
            "ministry": "กระทรวงทดสอบ",
            "budget": 5000000,
            "project_type": "invalid_type",
        }
        response = client.post("/api/v1/projects", json=body)
        assert response.status_code == 422

    def test_create_project_unauthenticated_returns_401(self, client):
        """Request without authentication returns 401."""
        # No get_current_user override — no auth header
        body = {
            "name": "โครงการทดสอบ",
            "ministry": "กระทรวงทดสอบ",
            "budget": 5000000,
            "project_type": "it",
        }
        response = client.post("/api/v1/projects", json=body)
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /projects — List projects
# ---------------------------------------------------------------------------


class TestListProjects:
    """Tests for GET /api/v1/projects."""

    def test_list_projects_returns_paginated_response(self, client, mock_officer_user):
        """List endpoint returns paginated response structure."""
        mock_db = AsyncMock()

        # Mock count query
        count_result = MagicMock()
        count_result.scalar_one.return_value = 1

        # Mock items query
        projects_result = MagicMock()
        project = _make_project()
        projects_result.scalars.return_value.all.return_value = [project]

        mock_db.execute = AsyncMock(side_effect=[count_result, projects_result])

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/projects")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "items" in data["data"]
        assert "pagination" in data["data"]
        assert data["data"]["pagination"]["per_page"] == 20

    def test_list_projects_with_status_filter(self, client, mock_officer_user):
        """Filter by status parameter."""
        mock_db = AsyncMock()
        count_result = MagicMock()
        count_result.scalar_one.return_value = 0
        projects_result = MagicMock()
        projects_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[count_result, projects_result])

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get("/api/v1/projects?status=draft")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["pagination"]["total"] == 0

    def test_list_projects_unauthenticated_returns_401(self, client):
        """Unauthenticated list request returns 401."""
        response = client.get("/api/v1/projects")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /projects/{id} — Get project detail
# ---------------------------------------------------------------------------


class TestGetProject:
    """Tests for GET /api/v1/projects/{id}."""

    def test_get_project_success(self, client, mock_officer_user):
        """Get project by ID returns project data."""
        project = _make_project()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/projects/{PROJECT_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["id"] == str(PROJECT_ID)

    def test_get_project_clamps_skipped_phase_two(self, client, mock_officer_user):
        project = _make_project()
        project.current_phase = 2
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/projects/{PROJECT_ID}")
        assert response.status_code == 200
        assert project.current_phase == 0
        mock_db.flush.assert_awaited()

    def test_get_project_not_found(self, client, mock_officer_user):
        """Returns 404 when project doesn't exist."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/projects/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_get_project_forbidden_for_other_user(self, client, mock_officer_user):
        """Officer cannot access another user's project."""
        project = _make_project(owner_id=OTHER_USER_ID)
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/projects/{PROJECT_ID}")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# PUT /projects/{id} — Update project
# ---------------------------------------------------------------------------


class TestUpdateProject:
    """Tests for PUT /api/v1/projects/{id}."""

    def test_update_project_success(self, client, mock_officer_user):
        """Successful update returns 200 with updated data."""
        project = _make_project()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        body = {"name": "โครงการใหม่"}
        response = client.put(f"/api/v1/projects/{PROJECT_ID}", json=body)
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_update_project_not_found(self, client, mock_officer_user):
        """Returns 404 when project doesn't exist."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        body = {"name": "โครงการใหม่"}
        response = client.put(f"/api/v1/projects/{uuid.uuid4()}", json=body)
        assert response.status_code == 404

    def test_update_project_empty_body_returns_400(self, client, mock_officer_user):
        """Empty update body returns 400 validation error."""
        project = _make_project()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.put(f"/api/v1/projects/{PROJECT_ID}", json={})
        assert response.status_code == 400

    def test_update_project_invalid_status_returns_422(self, client, mock_officer_user):
        """Invalid status value returns 422."""
        body = {"status": "invalid_status"}
        response = client.put(f"/api/v1/projects/{PROJECT_ID}", json=body)
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /projects/{id} — Archive project
# ---------------------------------------------------------------------------


class TestDeleteProject:
    """Tests for DELETE /api/v1/projects/{id}."""

    def test_archive_project_success(self, client, mock_officer_user):
        """Archiving a project returns 200."""
        project = _make_project(status="draft")
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.delete(f"/api/v1/projects/{PROJECT_ID}")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert "จัดเก็บโครงการเรียบร้อย" in data["data"]["message"]

    def test_archive_already_archived_returns_400(self, client, mock_officer_user):
        """Archiving an already archived project returns 400."""
        project = _make_project(status="archived")
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.delete(f"/api/v1/projects/{PROJECT_ID}")
        assert response.status_code == 400

    def test_archive_project_not_found(self, client, mock_officer_user):
        """Returns 404 when project doesn't exist."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.delete(f"/api/v1/projects/{uuid.uuid4()}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# GET /projects/{id}/versions — List versions
# ---------------------------------------------------------------------------


class TestListVersions:
    """Tests for GET /api/v1/projects/{id}/versions."""

    def test_list_versions_success(self, client, mock_officer_user):
        """Returns version list for a project."""
        project = _make_project()
        version = _make_version()

        mock_db = AsyncMock()
        # First call: select project
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = project
        # Second call: select versions
        versions_result = MagicMock()
        versions_result.scalars.return_value.all.return_value = [version]

        mock_db.execute = AsyncMock(side_effect=[project_result, versions_result])

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/projects/{PROJECT_ID}/versions")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["total"] == 1
        assert len(data["data"]["items"]) == 1

    def test_list_versions_project_not_found(self, client, mock_officer_user):
        """Returns 404 when project doesn't exist."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/projects/{uuid.uuid4()}/versions")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /projects/{id}/versions/{v}/restore — Restore version
# ---------------------------------------------------------------------------


class TestRestoreVersion:
    """Tests for POST /api/v1/projects/{id}/versions/{v}/restore."""

    def test_restore_version_success(self, client, mock_officer_user):
        """Successfully restores a version."""
        project = _make_project()
        version = _make_version(version_number=2, step_number=3)

        mock_db = AsyncMock()
        # 1st: select project
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = project
        # 2nd: select version to restore
        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = version
        # 3rd: count versions
        count_result = MagicMock()
        count_result.scalar_one.return_value = 5
        # 4th: max version number
        max_result = MagicMock()
        max_result.scalar_one.return_value = 5

        mock_db.execute = AsyncMock(
            side_effect=[project_result, version_result, count_result, max_result]
        )
        mock_db.add = MagicMock()
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock(side_effect=lambda v: _apply_version_defaults(v))

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.post(f"/api/v1/projects/{PROJECT_ID}/versions/2/restore")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True

    def test_restore_version_not_found(self, client, mock_officer_user):
        """Returns 404 when version doesn't exist."""
        project = _make_project()

        mock_db = AsyncMock()
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = project
        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(side_effect=[project_result, version_result])

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.post(f"/api/v1/projects/{PROJECT_ID}/versions/99/restore")
        assert response.status_code == 404

    def test_restore_version_max_limit(self, client, mock_officer_user):
        """Returns 400 when project has reached max versions (50)."""
        project = _make_project()
        version = _make_version(version_number=2)

        mock_db = AsyncMock()
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = project
        version_result = MagicMock()
        version_result.scalar_one_or_none.return_value = version
        count_result = MagicMock()
        count_result.scalar_one.return_value = 50  # At max limit

        mock_db.execute = AsyncMock(
            side_effect=[project_result, version_result, count_result]
        )

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.post(f"/api/v1/projects/{PROJECT_ID}/versions/2/restore")
        assert response.status_code == 400


class TestPhaseAndExtractionHitl:
    """Phase 0-2 APIs used by the mockup draft workspace."""

    def test_apply_without_confirm_is_rejected(self, client, mock_officer_user):
        response = client.post(
            f"/api/v1/projects/{PROJECT_ID}/extraction/apply",
            json={"sections": {"s1": "ข้อความ"}, "confirm": False},
        )
        assert response.status_code == 400

    def test_patch_phase_rejects_skip_to_two_without_intake(self, client, mock_officer_user):
        project = _make_project()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.patch(
            f"/api/v1/projects/{PROJECT_ID}/phase",
            json={"phase": 2},
        )
        assert response.status_code == 400
        assert project.current_phase == 0

    def test_patch_phase_allows_two_when_ready(self, client, mock_officer_user):
        project = _make_project()
        project.current_phase = 1
        slots = {
            key: {"content": "ข้อมูลข้อเท็จจริงของโครงการทดสอบ", "status": "filled"}
            for key in ("s1", "s2", "s5", "s6", "s7", "s4.1")
        }
        project.analysis_json = {"ready_to_compose": True, "slot_map": slots}
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.patch(
            f"/api/v1/projects/{PROJECT_ID}/phase",
            json={"phase": 2},
        )
        assert response.status_code == 200
        assert project.current_phase == 2

    def test_patch_phase(self, client, mock_officer_user):
        project = _make_project()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.patch(
            f"/api/v1/projects/{PROJECT_ID}/phase",
            json={"phase": 0},
        )
        assert response.status_code == 200
        assert project.current_phase == 0

    def test_list_sections_returns_thirteen_keys(self, client, mock_officer_user):
        project = _make_project()
        mock_db = AsyncMock()
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = project
        section_result = MagicMock()
        section_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(side_effect=[project_result, section_result])

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.get(f"/api/v1/projects/{PROJECT_ID}/sections")
        assert response.status_code == 200
        sections = response.json()["data"]["sections"]
        assert len(sections) == 13
        assert sections[0]["key"] == "s1"


class TestOfficerCanSubmit:
    def test_status_matrix(self):
        assert officer_can_submit("draft", 0) is True
        assert officer_can_submit("rejected", 1) is True
        assert officer_can_submit("archived", 4) is True
        assert officer_can_submit("archived", 3, True) is True
        assert officer_can_submit("archived", 2) is False
        assert officer_can_submit("in_review", 4) is False
        assert officer_can_submit("approved", 4) is False


class TestWorkflowAndWorkspaceWrites:
    """Submit / approve / reject, analysis, section save, extraction apply."""

    def test_submit_draft_moves_to_in_review(self, client, mock_officer_user):
        project = _make_project(status="draft")
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        with patch(
            "app.api.v1.endpoints.projects.AuditService.log",
            new_callable=AsyncMock,
        ):
            response = client.post(f"/api/v1/projects/{PROJECT_ID}/submit")
        assert response.status_code == 200
        assert project.status == "in_review"

    def test_submit_archived_phase4_moves_to_in_review(self, client, mock_officer_user):
        project = _make_project(status="archived", current_phase=4)
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        with patch(
            "app.api.v1.endpoints.projects.AuditService.log",
            new_callable=AsyncMock,
        ):
            response = client.post(f"/api/v1/projects/{PROJECT_ID}/submit")
        assert response.status_code == 200
        assert project.status == "in_review"

    def test_submit_archived_before_phase4_is_rejected(self, client, mock_officer_user):
        project = _make_project(status="archived", current_phase=2)
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/submit")
        assert response.status_code == 400

    def test_submit_archived_with_review_score_moves_to_in_review(
        self, client, mock_officer_user
    ):
        project = _make_project(status="archived", current_phase=3, quality_score=82)
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        with patch(
            "app.api.v1.endpoints.projects.AuditService.log",
            new_callable=AsyncMock,
        ):
            response = client.post(f"/api/v1/projects/{PROJECT_ID}/submit")
        assert response.status_code == 200
        assert project.status == "in_review"

    def test_submit_approved_is_rejected(self, client, mock_officer_user):
        project = _make_project(status="approved")
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/submit")
        assert response.status_code == 400

    def test_approve_sets_status(self, client, mock_admin_user):
        project = _make_project(status="in_review")
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/approve")
        assert response.status_code == 200
        assert project.status == "approved"

    def test_reject_sets_status(self, client, mock_admin_user):
        project = _make_project(status="in_review")
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/reject")
        assert response.status_code == 200
        assert project.status == "rejected"

    def test_put_analysis(self, client, mock_officer_user):
        project = _make_project()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)
        mock_db.flush = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        body = {"analysis": {"need": "พัฒนาระบบ", "budget_note": "5 ล้านบาท"}}
        response = client.put(f"/api/v1/projects/{PROJECT_ID}/analysis", json=body)
        assert response.status_code == 200
        assert project.analysis_json["need"] == "พัฒนาระบบ"
        assert response.json()["data"]["analysis"]["need"] == "พัฒนาระบบ"

    def test_put_section_creates_row(self, client, mock_officer_user):
        project = _make_project()
        mock_db = AsyncMock()
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = project
        section_result = MagicMock()
        section_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(side_effect=[project_result, section_result])
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.put(
            f"/api/v1/projects/{PROJECT_ID}/sections/s1",
            json={"content": "ความเป็นมาของโครงการ", "filled": True, "human_confirmed": True},
        )
        assert response.status_code == 200
        assert response.json()["data"]["sectionKey"] == "s1"
        mock_db.add.assert_called_once()

    def test_put_section_invalid_key(self, client, mock_officer_user):
        project = _make_project()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.put(
            f"/api/v1/projects/{PROJECT_ID}/sections/not-a-section",
            json={"content": "x"},
        )
        assert response.status_code == 400

    def test_extraction_apply_with_confirm(self, client, mock_officer_user):
        project = _make_project()
        mock_db = AsyncMock()
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = project
        missing_section = MagicMock()
        missing_section.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(side_effect=[project_result, missing_section])
        mock_db.flush = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.add = MagicMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        with patch(
            "app.api.v1.endpoints.projects.AuditService.log",
            new_callable=AsyncMock,
        ):
            response = client.post(
                f"/api/v1/projects/{PROJECT_ID}/extraction/apply",
                json={
                    "sections": {"s1": "ข้อความจาก TOR อ้างอิง"},
                    "extracted": {"projectName": "โครงการใหม่จากสกัด"},
                    "confirm": True,
                },
            )
        assert response.status_code == 200
        assert response.json()["data"]["written"] == 1
        assert project.name == "โครงการใหม่จากสกัด"

    def test_submit_not_found(self, client, mock_officer_user):
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.post(f"/api/v1/projects/{PROJECT_ID}/submit")
        assert response.status_code == 404

    def test_approve_and_reject_not_found(self, client, mock_admin_user):
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        assert client.post(f"/api/v1/projects/{PROJECT_ID}/approve").status_code == 404
        assert client.post(f"/api/v1/projects/{PROJECT_ID}/reject").status_code == 404

    def test_put_section_updates_existing(self, client, mock_officer_user):
        project = _make_project()
        existing = MagicMock()
        existing.content = "เดิม"
        existing.version = 1
        existing.is_approved = False
        mock_db = AsyncMock()
        project_result = MagicMock()
        project_result.scalar_one_or_none.return_value = project
        section_result = MagicMock()
        section_result.scalar_one_or_none.return_value = existing
        mock_db.execute = AsyncMock(side_effect=[project_result, section_result])
        mock_db.flush = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.put(
            f"/api/v1/projects/{PROJECT_ID}/sections/s1",
            json={"content": "ใหม่", "human_confirmed": True},
        )
        assert response.status_code == 200
        assert existing.content == "ใหม่"
        assert existing.version == 2
        assert existing.is_approved is True

    def test_extraction_apply_not_found(self, client, mock_officer_user):
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.post(
            f"/api/v1/projects/{PROJECT_ID}/extraction/apply",
            json={"sections": {"s1": "x"}, "confirm": True},
        )
        assert response.status_code == 404


    def test_extract_reference_not_found(self, client, mock_officer_user):
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.post(
            f"/api/v1/projects/{PROJECT_ID}/extraction",
            files={"file": ("note.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 404

    def test_extract_reference_empty_file(self, client, mock_officer_user):
        project = _make_project()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        response = client.post(
            f"/api/v1/projects/{PROJECT_ID}/extraction",
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert response.status_code == 400

    def test_extract_reference_success(self, client, mock_officer_user):
        from app.rag.extraction import ExtractionResult

        project = _make_project()
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db
        with patch(
            "app.api.v1.endpoints.projects.extract_text",
            return_value=ExtractionResult(
                text="1. ความเป็นมา\nโครงการพัฒนาระบบ",
                page_count=1,
                method="direct",
                warnings=[],
            ),
        ), patch(
            "app.api.v1.endpoints.projects.require_allowed_upload",
            return_value="text/plain",
        ):
            response = client.post(
                f"/api/v1/projects/{PROJECT_ID}/extraction",
                files={"file": ("tor.txt", b"dummy", "text/plain")},
                data={"doc_class": "other"},
            )
        assert response.status_code == 200
        assert response.json()["data"]["extractionStatus"] == "success"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_defaults(project):
    """Apply defaults to a real Project instance after flush/refresh."""
    if not hasattr(project, "id") or project.id is None:
        project.id = uuid.uuid4()
    if not hasattr(project, "created_at") or project.created_at is None:
        project.created_at = datetime.now(timezone.utc)
    if not hasattr(project, "updated_at") or project.updated_at is None:
        project.updated_at = datetime.now(timezone.utc)


def _apply_version_defaults(version):
    """Apply defaults to a ProjectVersion instance after flush/refresh."""
    if not hasattr(version, "id") or version.id is None:
        version.id = uuid.uuid4()
    if not hasattr(version, "created_at") or version.created_at is None:
        version.created_at = datetime.now(timezone.utc)
