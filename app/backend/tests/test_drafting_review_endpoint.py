"""Unit tests for AI drafting and review endpoints.

Tests cover:
- POST /api/v1/projects/{id}/draft-section: Draft a specific TOR section
- POST /api/v1/projects/{id}/review: Run full Rule Engine review
- GET /api/v1/projects/{id}/suggestions: Get AI suggestions
- PUT /api/v1/projects/{id}/suggestions/{sid}: Accept/dismiss suggestion
- POST /api/v1/projects/{id}/validate: Real-time validation

Validates: Requirements 5.1, 6.1, 10.1, 10.3, 10.5
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db
from app.main import app
from app.models.project import Project
from app.models.suggestion import Suggestion
from app.models.tor_section import TORSection
from app.models.user import User


# ---------------------------------------------------------------------------
# Constants and helpers
# ---------------------------------------------------------------------------

USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
PROJECT_ID = uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")
SUGGESTION_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")


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
    budget=5000000,
    project_type="it",
    quality_score=None,
):
    """Create a mock Project object."""
    project = MagicMock(spec=Project)
    project.id = project_id
    project.owner_id = owner_id
    project.name = name
    project.ministry = "กระทรวงทดสอบ"
    project.budget = budget
    project.project_type = project_type
    project.status = "draft"
    project.current_step = 7
    project.quality_score = quality_score
    project.template_id = None
    project.template = None
    project.created_at = datetime(2024, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    project.updated_at = datetime(2024, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    return project


def _make_section(section_key="s1", content="เนื้อหาทดสอบ", project_id=PROJECT_ID):
    """Create a mock TORSection object."""
    section = MagicMock(spec=TORSection)
    section.id = uuid.uuid4()
    section.project_id = project_id
    section.section_key = section_key
    section.sub_key = None
    section.content = content
    section.ai_draft = None
    section.quality_score = None
    section.validation_findings = None
    section.is_approved = False
    section.version = 1
    section.updated_at = datetime(2024, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    return section


def _make_suggestion(
    suggestion_id=SUGGESTION_ID,
    project_id=PROJECT_ID,
    status="pending",
    category="compliance",
):
    """Create a mock Suggestion object."""
    suggestion = MagicMock(spec=Suggestion)
    suggestion.id = suggestion_id
    suggestion.project_id = project_id
    suggestion.section_key = "s3"
    suggestion.category = category
    suggestion.current_text = "ข้อความเดิม"
    suggestion.suggested_text = "ข้อความที่แนะนำ"
    suggestion.predicted_score_improvement = 3.5
    suggestion.status = status
    suggestion.created_at = datetime(2024, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    return suggestion


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /projects/{id}/draft-section
# ---------------------------------------------------------------------------


class TestDraftSection:
    """Tests for POST /api/v1/projects/{id}/draft-section."""

    def test_draft_section_project_not_found(self, client, mock_officer_user):
        """Returns 404 when project does not exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.post(
            f"/api/v1/projects/{PROJECT_ID}/draft-section",
            json={"section_key": "s1"},
        )

        assert response.status_code == 404
        data = response.json()
        assert data["ok"] is False

    def test_draft_section_invalid_section_key(self, client, mock_officer_user):
        """Returns 422 for invalid section key format."""
        response = client.post(
            f"/api/v1/projects/{PROJECT_ID}/draft-section",
            json={"section_key": "invalid"},
        )

        assert response.status_code == 422

    def test_draft_section_success(self, client, mock_officer_user):
        """Successfully drafts a section via the orchestrator."""
        project = _make_project()
        section = _make_section("s1")

        mock_db = AsyncMock()

        # First call: select project
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project

        # Second call: select all sections
        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = [section]

        # Third call: select target section for persistence
        mock_section_result = MagicMock()
        mock_section_result.scalar_one_or_none.return_value = section

        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_sections_result, mock_section_result]
        )
        mock_db.flush = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        # Mock the orchestrator (imported lazily inside the endpoint function)
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            "draft_content": "ร่างเนื้อหาที่สร้างขึ้น",
            "quality_score": 85,
            "validation_findings": [],
            "rag_retrieval_failed": False,
            "error": None,
            "best_draft_content": None,
            "best_draft_score": -1,
        })

        with patch(
            "app.orchestrator.compile_tor_drafting_graph",
            return_value=mock_graph,
        ):
            response = client.post(
                f"/api/v1/projects/{PROJECT_ID}/draft-section",
                json={"section_key": "s1"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["section_key"] == "s1"
        assert data["data"]["draft_content"] == "ร่างเนื้อหาที่สร้างขึ้น"
        assert data["data"]["quality_score"] == 85


# ---------------------------------------------------------------------------
# POST /projects/{id}/review
# ---------------------------------------------------------------------------


class TestRunReview:
    """Tests for POST /api/v1/projects/{id}/review."""

    def test_review_project_not_found(self, client, mock_officer_user):
        """Returns 404 when project does not exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.post(f"/api/v1/projects/{PROJECT_ID}/review")

        assert response.status_code == 404

    def test_review_success(self, client, mock_officer_user):
        """Successfully runs Rule Engine review."""
        project = _make_project()
        section_s1 = _make_section("s1", "ความเป็นมาของโครงการ")
        section_s2 = _make_section("s2", "วัตถุประสงค์ของโครงการ")

        mock_db = AsyncMock()

        # First call: select project
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project

        # Second call: select all sections
        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = [section_s1, section_s2]

        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_sections_result]
        )
        mock_db.flush = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        # Mock the Rule Engine
        from app.rule_engine.engine import CategoryScore, Finding, Severity, ValidationResult

        mock_validation_result = ValidationResult(
            quality_score=75,
            categories=[
                CategoryScore(category="legal", score=80.0, weight=0.4),
                CategoryScore(category="completeness", score=70.0, weight=0.3),
                CategoryScore(category="consistency", score=75.0, weight=0.2),
                CategoryScore(category="format", score=80.0, weight=0.1),
            ],
            findings=[
                Finding(
                    severity=Severity.WARNING,
                    rule_violated="MISSING_LEGAL_REF",
                    affected_section="s1",
                    message="ขาดการอ้างอิงกฎหมาย",
                    recommended_correction="ควรอ้างอิง พ.ร.บ. 2560",
                ),
            ],
            is_valid=True,
        )

        mock_engine = MagicMock()
        mock_engine.validate.return_value = mock_validation_result

        async def fake_suggestions(*_args, **_kwargs):
            return 3, "ต้องแก้ให้สอดคล้องกฎหมายและความต้องการโครงการ"

        async def fake_law():
            return "พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560 มาตรา 8"

        with patch(
            "app.orchestrator.graph._create_rule_engine",
            return_value=mock_engine,
        ), patch(
            "app.api.v1.endpoints.review._generate_suggestions",
            new=fake_suggestions,
        ), patch(
            "app.api.v1.endpoints.review._law_review_context",
            new=fake_law,
        ):
            response = client.post(f"/api/v1/projects/{PROJECT_ID}/review")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["quality_score"] == 75
        assert data["data"]["is_valid"] is True
        assert len(data["data"]["findings"]) == 1
        assert data["data"]["findings"][0]["severity"] == "warning"
        assert data["data"]["findings"][0]["finding_kind"] == "legal_violation"
        assert "มาตรา 8" in (data["data"]["findings"][0].get("legal_basis") or "")
        assert data["data"]["suggestions_generated"] == 3

    def test_review_rule_engine_failure_returns_validation_error(
        self, client, mock_officer_user
    ):
        """Rule Engine exceptions become a Thai validation error, not a 500."""
        project = _make_project()
        section_s1 = _make_section("s1", "ความเป็นมาของโครงการ")

        mock_db = AsyncMock()
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project
        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = [section_s1]
        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_sections_result]
        )

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        with patch(
            "app.orchestrator.graph._create_rule_engine",
            side_effect=RuntimeError("engine boom"),
        ):
            response = client.post(f"/api/v1/projects/{PROJECT_ID}/review")

        assert response.status_code == 400
        body = response.json()
        assert body["ok"] is False
        assert "การตรวจสอบล้มเหลว" in body["error"]["message"]
        assert "engine boom" in str(body["error"].get("details", ""))


# ---------------------------------------------------------------------------
# GET /projects/{id}/suggestions
# ---------------------------------------------------------------------------


class TestGetSuggestions:
    """Tests for GET /api/v1/projects/{id}/suggestions."""

    def test_suggestions_project_not_found(self, client, mock_officer_user):
        """Returns 404 when project does not exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/projects/{PROJECT_ID}/suggestions")

        assert response.status_code == 404

    def test_suggestions_success(self, client, mock_officer_user):
        """Returns list of suggestions for a project."""
        project = _make_project(quality_score=78)
        suggestion1 = _make_suggestion(category="compliance")
        suggestion2 = _make_suggestion(
            suggestion_id=uuid.uuid4(), category="clarity"
        )

        mock_db = AsyncMock()

        # First call: select project
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project

        # Second call: select suggestions
        mock_suggestions_result = MagicMock()
        mock_suggestions_result.scalars.return_value.all.return_value = [
            suggestion1, suggestion2
        ]

        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_suggestions_result]
        )

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/projects/{PROJECT_ID}/suggestions")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["total"] == 2
        assert len(data["data"]["items"]) == 2
        assert data["data"]["quality_score"] == 78

    def test_suggestions_invalid_category_filter(self, client, mock_officer_user):
        """Returns 400 for invalid category filter."""
        project = _make_project()

        mock_db = AsyncMock()
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project
        mock_db.execute = AsyncMock(return_value=mock_project_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(
            f"/api/v1/projects/{PROJECT_ID}/suggestions?category=invalid"
        )

        assert response.status_code == 400


# ---------------------------------------------------------------------------
# PUT /projects/{id}/suggestions/{sid}
# ---------------------------------------------------------------------------


class TestUpdateSuggestion:
    """Tests for PUT /api/v1/projects/{id}/suggestions/{sid}."""

    def test_update_suggestion_not_found(self, client, mock_officer_user):
        """Returns 404 when suggestion does not exist."""
        project = _make_project()
        mock_db = AsyncMock()

        # First call: select project
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project

        # Second call: select suggestion (not found)
        mock_suggestion_result = MagicMock()
        mock_suggestion_result.scalar_one_or_none.return_value = None

        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_suggestion_result]
        )

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.put(
            f"/api/v1/projects/{PROJECT_ID}/suggestions/{SUGGESTION_ID}",
            json={"status": "accepted"},
        )

        assert response.status_code == 404

    def test_update_suggestion_accept(self, client, mock_officer_user):
        """Successfully accepts a suggestion."""
        project = _make_project()
        suggestion = _make_suggestion(status="pending")
        section = _make_section("s3", "ข้อความเดิมและอื่นๆ")

        mock_db = AsyncMock()

        # First call: select project
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project

        # Second call: select suggestion
        mock_suggestion_result = MagicMock()
        mock_suggestion_result.scalar_one_or_none.return_value = suggestion

        # Third call: select section for applying suggestion
        mock_section_result = MagicMock()
        mock_section_result.scalar_one_or_none.return_value = section

        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_suggestion_result, mock_section_result]
        )
        mock_db.flush = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.put(
            f"/api/v1/projects/{PROJECT_ID}/suggestions/{SUGGESTION_ID}",
            json={"status": "accepted"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["status"] == "accepted"

    def test_update_suggestion_dismiss(self, client, mock_officer_user):
        """Successfully dismisses a suggestion."""
        project = _make_project()
        suggestion = _make_suggestion(status="pending")

        mock_db = AsyncMock()

        # First call: select project
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project

        # Second call: select suggestion
        mock_suggestion_result = MagicMock()
        mock_suggestion_result.scalar_one_or_none.return_value = suggestion

        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_suggestion_result]
        )
        mock_db.flush = AsyncMock()

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.put(
            f"/api/v1/projects/{PROJECT_ID}/suggestions/{SUGGESTION_ID}",
            json={"status": "dismissed"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["status"] == "dismissed"

    def test_update_suggestion_invalid_status_pending(self, client, mock_officer_user):
        """Returns 422 when trying to set status back to 'pending'."""
        response = client.put(
            f"/api/v1/projects/{PROJECT_ID}/suggestions/{SUGGESTION_ID}",
            json={"status": "pending"},
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /projects/{id}/validate
# ---------------------------------------------------------------------------


class TestValidate:
    """Tests for POST /api/v1/projects/{id}/validate."""

    def test_validate_project_not_found(self, client, mock_officer_user):
        """Returns 404 when project does not exist."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.post(f"/api/v1/projects/{PROJECT_ID}/validate")

        assert response.status_code == 404

    def test_validate_success(self, client, mock_officer_user):
        """Successfully validates the TOR document."""
        project = _make_project()
        section = _make_section("s1", "เนื้อหาส่วนที่ 1")

        mock_db = AsyncMock()

        # First call: select project
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project

        # Second call: select sections
        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = [section]

        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_sections_result]
        )

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        # Mock the Rule Engine
        from app.rule_engine.engine import ValidationResult

        mock_validation_result = ValidationResult(
            quality_score=82,
            categories=[],
            findings=[],
            is_valid=True,
        )

        mock_engine = MagicMock()
        mock_engine.validate.return_value = mock_validation_result

        async def fake_law():
            return ""

        with patch(
            "app.orchestrator.graph._create_rule_engine",
            return_value=mock_engine,
        ), patch(
            "app.api.v1.endpoints.review._law_review_context",
            new=fake_law,
        ):
            response = client.post(f"/api/v1/projects/{PROJECT_ID}/validate")

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["quality_score"] == 82
        assert data["data"]["is_valid"] is True

    def test_validate_with_content(self, client, mock_officer_user):
        """Validates specific content for a section (real-time editing)."""
        project = _make_project()
        section = _make_section("s1", "เนื้อหาเดิม")

        mock_db = AsyncMock()

        # First call: select project
        mock_project_result = MagicMock()
        mock_project_result.scalar_one_or_none.return_value = project

        # Second call: select sections
        mock_sections_result = MagicMock()
        mock_sections_result.scalars.return_value.all.return_value = [section]

        mock_db.execute = AsyncMock(
            side_effect=[mock_project_result, mock_sections_result]
        )

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        # Mock the Rule Engine
        from app.rule_engine.engine import ValidationResult

        mock_validation_result = ValidationResult(
            quality_score=70,
            categories=[],
            findings=[],
            is_valid=True,
        )

        mock_engine = MagicMock()
        mock_engine.validate.return_value = mock_validation_result

        async def fake_law():
            return ""

        with patch(
            "app.orchestrator.graph._create_rule_engine",
            return_value=mock_engine,
        ), patch(
            "app.api.v1.endpoints.review._law_review_context",
            new=fake_law,
        ):
            response = client.post(
                f"/api/v1/projects/{PROJECT_ID}/validate",
                json={
                    "section_key": "s1",
                    "content": "เนื้อหาใหม่ที่กำลังแก้ไข",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["quality_score"] == 70
