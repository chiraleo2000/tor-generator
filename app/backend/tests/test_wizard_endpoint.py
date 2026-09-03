"""Unit tests for wizard step endpoints.

Tests:
- PUT /api/v1/projects/{id}/steps/{step}: Save step data
- GET /api/v1/projects/{id}/steps/{step}: Retrieve step data
- POST /api/v1/projects/{id}/steps/{step}/draft: Trigger AI drafting

Uses FastAPI's TestClient with mocked dependencies.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db
from app.main import app
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.tor_section import TORSection
from app.models.user import User


# =============================================================================
# Fixtures
# =============================================================================

SAMPLE_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
SAMPLE_PROJECT_ID = UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")
OTHER_USER_ID = UUID("99999999-9999-9999-9999-999999999999")


@pytest.fixture(autouse=True)
def setup_app_state():
    """Set up app state and clear dependency overrides after each test."""
    app.state.db_session_factory = None
    app.state.db_engine = None
    app.state.redis = None
    app.state.minio = None
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    user = MagicMock(spec=User)
    user.id = SAMPLE_USER_ID
    user.email = "test@example.go.th"
    user.name = "ทดสอบ ผู้ใช้"
    user.role = "officer"
    return user


@pytest.fixture
def mock_project():
    """Create a mock project owned by the sample user."""
    project = MagicMock(spec=Project)
    project.id = SAMPLE_PROJECT_ID
    project.owner_id = SAMPLE_USER_ID
    project.name = "โครงการทดสอบ"
    project.ministry = "กระทรวงทดสอบ"
    project.budget = 5000000
    project.project_type = "it"
    project.status = "draft"
    project.current_step = 1
    project.quality_score = None
    project.template_id = None
    project.template = None
    return project


@pytest.fixture
def mock_tor_section():
    """Create a mock TOR section."""
    from datetime import datetime

    section = MagicMock(spec=TORSection)
    section.id = uuid4()
    section.project_id = SAMPLE_PROJECT_ID
    section.section_key = "s1"
    section.sub_key = None
    section.content = "เนื้อหาทดสอบ"
    section.ai_draft = "ร่างจาก AI"
    section.quality_score = 85.0
    section.validation_findings = None
    section.is_approved = False
    section.version = 1
    section.updated_at = datetime(2024, 8, 15, 10, 30, 0)
    return section


def _setup_overrides(mock_user, mock_db_session):
    """Configure dependency overrides for auth and DB."""

    async def override_get_current_user():
        return mock_user

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


# =============================================================================
# PUT /api/v1/projects/{id}/steps/{step} — Save step data
# =============================================================================


class TestSaveStepData:
    """Tests for PUT /api/v1/projects/{id}/steps/{step}."""

    def test_save_step_success(self, client, mock_user, mock_project):
        """Successfully save wizard step data."""
        mock_db = AsyncMock()

        # Mock select for project lookup
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project

        # Mock select for existing section lookup (no existing section)
        mock_section_result = MagicMock()
        mock_section_result.scalar_one_or_none.return_value = None

        # Mock select for existing sections (snapshot)
        mock_all_sections_result = MagicMock()
        mock_all_sections_result.scalars.return_value.all.return_value = []

        # Mock select for max version number
        mock_version_result = MagicMock()
        mock_version_result.scalar_one_or_none.return_value = None  # No existing versions

        mock_db.execute = AsyncMock(
            side_effect=[
                mock_project_result,      # Project lookup
                mock_section_result,      # Section lookup for s1
                mock_all_sections_result, # Snapshot
                mock_version_result,      # Max version number
            ]
        )
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        _setup_overrides(mock_user, mock_db)

        response = client.put(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1",
            json={"data": {"s1": "ความเป็นมาของโครงการ"}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["step"] == 1
        assert data["data"]["project_id"] == str(SAMPLE_PROJECT_ID)
        assert data["data"]["sections_updated"] == 1
        assert data["data"]["version_number"] == 1
        assert data["data"]["message"] == "บันทึกข้อมูลเรียบร้อยแล้ว"

    def test_save_step_updates_project_metadata_and_existing_section(
        self, client, mock_user, mock_project
    ):
        existing = MagicMock(spec=TORSection)
        existing.content = "เก่า"
        existing.version = 1
        mock_db = AsyncMock()
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project
        mock_section_result = MagicMock()
        mock_section_result.scalar_one_or_none.return_value = existing
        mock_location_result = MagicMock()
        mock_location_result.scalar_one_or_none.return_value = None
        mock_all_sections_result = MagicMock()
        mock_all_sections_result.scalars.return_value.all.return_value = [existing]
        mock_version_result = MagicMock()
        mock_version_result.scalar_one_or_none.return_value = 50
        mock_db.execute = AsyncMock(
            side_effect=[
                mock_project_result,
                mock_section_result,
                mock_location_result,
                mock_all_sections_result,
                mock_version_result,
            ]
        )
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()
        _setup_overrides(mock_user, mock_db)

        template_id = uuid4()
        response = client.put(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1",
            json={
                "data": {
                    "project_name": "ชื่อใหม่",
                    "ministry": "กระทรวงใหม่",
                    "budget": "1500000",
                    "project_type": "construction",
                    "template_id": str(template_id),
                    "duration_days": 180,
                    "location": "กรุงเทพมหานคร",
                }
            },
        )
        assert response.status_code == 200
        assert response.json()["data"]["version_number"] == 50
        assert mock_project.name == "ชื่อใหม่"
        assert mock_project.ministry == "กระทรวงใหม่"
        assert mock_project.budget == 1500000
        assert mock_project.project_type == "construction"
        assert mock_project.template_id == template_id
        assert existing.version == 2

    def test_save_step_ignores_bad_budget_and_template_id(
        self, client, mock_user, mock_project
    ):
        mock_project.budget = 5000000
        mock_project.template_id = None
        mock_db = AsyncMock()
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project
        mock_section_result = MagicMock()
        mock_section_result.scalar_one_or_none.return_value = None
        mock_all_sections_result = MagicMock()
        mock_all_sections_result.scalars.return_value.all.return_value = []
        mock_version_result = MagicMock()
        mock_version_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(
            side_effect=[
                mock_project_result,
                mock_section_result,
                mock_all_sections_result,
                mock_version_result,
            ]
        )
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()
        _setup_overrides(mock_user, mock_db)

        response = client.put(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1",
            json={
                "data": {
                    "s1": "ความเป็นมาของโครงการ",
                    "budget": "not-a-number",
                    "template_id": "not-a-uuid",
                }
            },
        )
        assert response.status_code == 200
        assert mock_project.budget == 5000000
        assert mock_project.template_id is None

    def test_save_step_persists_scope_subkeys(self, client, mock_user, mock_project):
        existing_sub = MagicMock(spec=TORSection)
        existing_sub.content = "เก่า"
        existing_sub.version = 1
        mock_db = AsyncMock()
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project
        mock_s4_result = MagicMock()
        mock_s4_result.scalar_one_or_none.return_value = None
        mock_sub_existing = MagicMock()
        mock_sub_existing.scalar_one_or_none.return_value = existing_sub
        mock_sub_new = MagicMock()
        mock_sub_new.scalar_one_or_none.return_value = None
        mock_all_sections_result = MagicMock()
        mock_all_sections_result.scalars.return_value.all.return_value = []
        mock_version_result = MagicMock()
        mock_version_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(
            side_effect=[
                mock_project_result,
                mock_s4_result,
                mock_sub_existing,
                mock_sub_new,
                mock_all_sections_result,
                mock_version_result,
            ]
        )
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()
        _setup_overrides(mock_user, mock_db)

        response = client.put(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/4",
            json={
                "data": {
                    "s4": {"title": "ขอบเขต"},
                    "s4.1": "ขอบเขตงานหลัก",
                    "s4.2": "วิธีดำเนินการ",
                }
            },
        )
        assert response.status_code == 200
        assert existing_sub.version == 2
        assert existing_sub.content == "ขอบเขตงานหลัก"
        assert mock_db.add.call_count >= 2

    def test_save_step_invalid_step_number(self, client, mock_user):
        """Step number outside 1-8 returns error."""
        mock_db = AsyncMock()
        _setup_overrides(mock_user, mock_db)

        # FastAPI path validation: step=0 (ge=1 constraint)
        response = client.put(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/0",
            json={"data": {"s1": "test"}},
        )
        assert response.status_code == 422

    def test_save_step_step_9_invalid(self, client, mock_user):
        """Step number 9 returns validation error."""
        mock_db = AsyncMock()
        _setup_overrides(mock_user, mock_db)

        response = client.put(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/9",
            json={"data": {"s1": "test"}},
        )
        assert response.status_code == 422

    def test_save_step_empty_data_returns_422(self, client, mock_user):
        """Empty data dict triggers Pydantic validation error."""
        mock_db = AsyncMock()
        _setup_overrides(mock_user, mock_db)

        response = client.put(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1",
            json={"data": {}},
        )
        assert response.status_code == 422

    def test_save_step_project_not_found(self, client, mock_user):
        """Non-existent project returns 404."""
        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        _setup_overrides(mock_user, mock_db)

        response = client.put(
            f"/api/v1/projects/{uuid4()}/steps/1",
            json={"data": {"s1": "test content"}},
        )
        assert response.status_code == 404

    def test_save_step_not_owner(self, client, mock_user, mock_project):
        """Non-owner accessing project returns 404 (hides existence)."""
        mock_project.owner_id = OTHER_USER_ID  # Different owner

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_db.execute = AsyncMock(return_value=mock_result)

        _setup_overrides(mock_user, mock_db)

        response = client.put(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1",
            json={"data": {"s1": "test content"}},
        )
        assert response.status_code == 404

    def test_save_step_requires_auth(self, client):
        """Unauthenticated request returns 401."""
        # Don't set up dependency overrides for auth
        async def override_get_db():
            yield AsyncMock()

        app.dependency_overrides[get_db] = override_get_db

        response = client.put(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1",
            json={"data": {"s1": "test"}},
        )
        assert response.status_code == 401


# =============================================================================
# GET /api/v1/projects/{id}/steps/{step} — Retrieve step data
# =============================================================================


class TestGetStepData:
    """Tests for GET /api/v1/projects/{id}/steps/{step}."""

    def test_get_step_success_with_sections(
        self, client, mock_user, mock_project, mock_tor_section
    ):
        """Successfully retrieve step data with sections."""
        mock_db = AsyncMock()

        # Mock project lookup
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project

        # Mock section lookup
        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = [mock_tor_section]

        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_sections_result]
        )

        _setup_overrides(mock_user, mock_db)

        response = client.get(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["step"] == 1
        assert data["data"]["project_id"] == str(SAMPLE_PROJECT_ID)
        assert data["data"]["project_name"] == "โครงการทดสอบ"
        assert data["data"]["current_step"] == 1
        assert len(data["data"]["sections"]) == 1
        assert data["data"]["sections"][0]["section_key"] == "s1"
        assert data["data"]["sections"][0]["content"] == "เนื้อหาทดสอบ"
        assert data["data"]["sections"][0]["ai_draft"] == "ร่างจาก AI"

    def test_get_step_empty_sections(self, client, mock_user, mock_project):
        """Step with no saved sections returns empty list."""
        mock_db = AsyncMock()

        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project

        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = []

        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_sections_result]
        )

        _setup_overrides(mock_user, mock_db)

        response = client.get(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["sections"] == []

    def test_get_step_project_not_found(self, client, mock_user):
        """Non-existent project returns 404."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        _setup_overrides(mock_user, mock_db)

        response = client.get(
            f"/api/v1/projects/{uuid4()}/steps/1",
        )
        assert response.status_code == 404

    def test_get_step_invalid_step(self, client, mock_user):
        """Invalid step number returns 422."""
        mock_db = AsyncMock()
        _setup_overrides(mock_user, mock_db)

        response = client.get(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/10",
        )
        assert response.status_code == 422

    def test_get_step_8_returns_empty(self, client, mock_user, mock_project):
        """Step 8 (export) has no section keys, returns empty sections."""
        mock_db = AsyncMock()

        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project

        mock_db.execute = AsyncMock(return_value=mock_project_result)

        _setup_overrides(mock_user, mock_db)

        response = client.get(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/8",
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["sections"] == []

    def test_get_step_requires_auth(self, client):
        """Unauthenticated request returns 401."""
        async def override_get_db():
            yield AsyncMock()

        app.dependency_overrides[get_db] = override_get_db

        response = client.get(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1",
        )
        assert response.status_code == 401


# =============================================================================
# POST /api/v1/projects/{id}/steps/{step}/draft — Trigger AI drafting
# =============================================================================


class TestTriggerDraft:
    """Tests for POST /api/v1/projects/{id}/steps/{step}/draft."""

    def test_draft_step_8_invalid(self, client, mock_user, mock_project):
        """Step 8 (export) cannot trigger drafting."""
        mock_db = AsyncMock()

        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project

        mock_db.execute = AsyncMock(return_value=mock_project_result)

        _setup_overrides(mock_user, mock_db)

        response = client.post(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/8/draft",
            json={},
        )

        assert response.status_code == 400

    def test_draft_project_not_found(self, client, mock_user):
        """Non-existent project returns 404."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        _setup_overrides(mock_user, mock_db)

        response = client.post(
            f"/api/v1/projects/{uuid4()}/steps/1/draft",
            json={},
        )
        assert response.status_code == 404

    def test_draft_invalid_target_section(self, client, mock_user, mock_project):
        """Specifying a target_section not in the step returns 400."""
        mock_db = AsyncMock()

        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project

        mock_db.execute = AsyncMock(return_value=mock_project_result)

        _setup_overrides(mock_user, mock_db)

        response = client.post(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1/draft",
            json={"target_section": "s1"},  # s1 belongs to step 2, not step 1
        )

        assert response.status_code == 400

    @patch("app.orchestrator.compile_tor_drafting_graph")
    def test_draft_success(
        self, mock_compile, client, mock_user, mock_project
    ):
        """Successfully trigger AI drafting via orchestrator."""
        mock_db = AsyncMock()

        # Mock project lookup
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project

        # Mock section query (existing sections)
        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = []

        # Mock section lookup for persisting AI draft
        mock_draft_section_result = MagicMock()
        mock_draft_section_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[
                mock_project_result,
                mock_sections_result,
                mock_draft_section_result,
            ]
        )
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        _setup_overrides(mock_user, mock_db)

        # Mock the orchestrator graph
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "draft_content": "ร่างเนื้อหาจาก AI สำหรับส่วนความเป็นมา",
            "quality_score": 85.0,
            "validation_findings": [],
            "rag_retrieval_failed": False,
            "error": None,
            "best_draft_content": None,
            "best_draft_score": -1.0,
            "best_draft_findings": [],
        })
        mock_compile.return_value = mock_graph

        response = client.post(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1/draft",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["step"] == 1
        assert data["data"]["target_section"] == "s5"
        assert data["data"]["draft_content"] == "ร่างเนื้อหาจาก AI สำหรับส่วนความเป็นมา"
        assert data["data"]["quality_score"] == 85.0
        assert data["data"]["rag_retrieval_failed"] is False

    @patch("app.orchestrator.compile_tor_drafting_graph")
    def test_draft_with_rag_failure(
        self, mock_compile, client, mock_user, mock_project
    ):
        """Draft succeeds even when RAG retrieval fails (graceful degradation)."""
        mock_db = AsyncMock()

        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project

        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = []

        mock_draft_section_result = MagicMock()
        mock_draft_section_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[
                mock_project_result,
                mock_sections_result,
                mock_draft_section_result,
            ]
        )
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        _setup_overrides(mock_user, mock_db)

        # Mock graph with RAG failure but draft still generated
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "draft_content": "ร่างเนื้อหาโดยไม่มีข้อมูล RAG",
            "quality_score": 65.0,
            "validation_findings": [
                {
                    "severity": "warning",
                    "rule_violated": "RAG_UNAVAILABLE",
                    "affected_section": "s1",
                    "message": "ไม่สามารถดึงข้อมูลอ้างอิงจากฐานความรู้ได้",
                    "recommended_correction": None,
                }
            ],
            "rag_retrieval_failed": True,
            "error": None,
            "best_draft_content": None,
            "best_draft_score": -1.0,
            "best_draft_findings": [],
        })
        mock_compile.return_value = mock_graph

        response = client.post(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1/draft",
            json={},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["rag_retrieval_failed"] is True
        assert data["data"]["draft_content"] == "ร่างเนื้อหาโดยไม่มีข้อมูล RAG"

    @patch("app.orchestrator.compile_tor_drafting_graph")
    def test_draft_uses_best_draft_and_existing_section(
        self, mock_compile, client, mock_user, mock_project, mock_tor_section
    ):
        mock_db = AsyncMock()
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project
        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = [mock_tor_section]
        mock_draft_section_result = MagicMock()
        mock_draft_section_result.scalar_one_or_none.return_value = mock_tor_section
        mock_db.execute = AsyncMock(
            side_effect=[
                mock_project_result,
                mock_sections_result,
                mock_draft_section_result,
            ]
        )
        mock_db.flush = AsyncMock()
        _setup_overrides(mock_user, mock_db)

        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "draft_content": "",
                "quality_score": None,
                "validation_findings": [],
                "rag_retrieval_failed": False,
                "error": None,
                "best_draft_content": "ร่างสำรองจากรอบก่อน",
                "best_draft_score": 72.0,
                "best_draft_findings": [{"severity": "warning"}],
            }
        )
        mock_compile.return_value = mock_graph
        mock_project.template = MagicMock()
        mock_project.template.section_structure = {"s5": {}}
        mock_project.template.placeholder_guidance = {"s5": "แนะนำ"}

        response = client.post(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1/draft",
            json={"additional_context": {"note": "เพิ่มบริบท"}, "target_section": "s5"},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["draft_content"] == "ร่างสำรองจากรอบก่อน"
        assert data["quality_score"] == 72.0
        assert mock_tor_section.ai_draft == "ร่างสำรองจากรอบก่อน"

    @patch("app.orchestrator.compile_tor_drafting_graph")
    def test_draft_error_without_content_returns_400(
        self, mock_compile, client, mock_user, mock_project
    ):
        mock_db = AsyncMock()
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project
        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_sections_result]
        )
        _setup_overrides(mock_user, mock_db)
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(
            return_value={
                "draft_content": "",
                "quality_score": None,
                "validation_findings": [],
                "rag_retrieval_failed": False,
                "error": "โมเดลล่ม",
                "best_draft_content": None,
                "best_draft_score": -1.0,
                "best_draft_findings": [],
            }
        )
        mock_compile.return_value = mock_graph
        response = client.post(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1/draft",
            json={},
        )
        assert response.status_code == 400
        assert "การสร้างร่างล้มเหลว" in response.json()["error"]["message"]

    @patch(
        "app.orchestrator.compile_tor_drafting_graph",
        side_effect=ImportError("orchestrator missing"),
    )
    def test_draft_import_error_returns_400(
        self, _mock_compile, client, mock_user, mock_project
    ):
        mock_db = AsyncMock()
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project
        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_sections_result]
        )
        _setup_overrides(mock_user, mock_db)
        response = client.post(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1/draft",
            json={},
        )
        assert response.status_code == 400
        assert "ระบบ AI ไม่พร้อม" in response.json()["error"]["message"]

    @patch(
        "app.orchestrator.compile_tor_drafting_graph",
        side_effect=RuntimeError("graph boom"),
    )
    def test_draft_unexpected_error_returns_400(
        self, _mock_compile, client, mock_user, mock_project
    ):
        mock_db = AsyncMock()
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = mock_project
        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_sections_result]
        )
        _setup_overrides(mock_user, mock_db)
        response = client.post(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1/draft",
            json={},
        )
        assert response.status_code == 400
        assert "การสร้างร่างล้มเหลว" in response.json()["error"]["message"]

    def test_draft_requires_auth(self, client):
        """Unauthenticated request returns 401."""
        async def override_get_db():
            yield AsyncMock()

        app.dependency_overrides[get_db] = override_get_db

        response = client.post(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1/draft",
            json={},
        )
        assert response.status_code == 401

    def test_draft_not_owner(self, client, mock_user, mock_project):
        """Non-owner cannot trigger drafting."""
        mock_project.owner_id = OTHER_USER_ID

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_project
        mock_db.execute = AsyncMock(return_value=mock_result)

        _setup_overrides(mock_user, mock_db)

        response = client.post(
            f"/api/v1/projects/{SAMPLE_PROJECT_ID}/steps/1/draft",
            json={},
        )
        assert response.status_code == 404


# =============================================================================
# Schema validation tests
# =============================================================================


class TestWizardSchemas:
    """Tests for wizard Pydantic schema validation."""

    def test_step_section_map_covers_all_steps(self):
        """STEP_SECTION_MAP should map all 8 steps."""
        from app.schemas.wizard import STEP_SECTION_MAP

        assert set(STEP_SECTION_MAP.keys()) == {1, 2, 3, 4, 5, 6, 7, 8}

    def test_step_section_map_step_8_is_empty(self):
        """Step 8 (export) has no associated sections."""
        from app.schemas.wizard import STEP_SECTION_MAP

        assert STEP_SECTION_MAP[8] == []

    def test_step_data_save_rejects_empty(self):
        """StepDataSave rejects empty data dict."""
        from pydantic import ValidationError as PydanticValidationError

        from app.schemas.wizard import StepDataSave

        with pytest.raises(PydanticValidationError):
            StepDataSave(data={})

    def test_step_data_save_accepts_valid(self):
        """StepDataSave accepts non-empty data."""
        from app.schemas.wizard import StepDataSave

        result = StepDataSave(data={"s1": "content"})
        assert result.data == {"s1": "content"}

    def test_draft_section_request_optional_fields(self):
        """DraftSectionRequest fields are optional."""
        from app.schemas.wizard import DraftSectionRequest

        req = DraftSectionRequest()
        assert req.target_section is None
        assert req.additional_context is None

    def test_valid_steps_set(self):
        """VALID_STEPS contains exactly steps 1-8."""
        from app.schemas.wizard import VALID_STEPS

        assert VALID_STEPS == {1, 2, 3, 4, 5, 6, 7, 8}
