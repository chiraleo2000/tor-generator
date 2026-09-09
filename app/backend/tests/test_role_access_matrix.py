"""Role-access matrix for create-project and intake phase 1–2.

Policy discovered in code (asserted here, not changed):
- POST /projects: any authenticated user (officer / reviewer / admin) may create;
  budget is optional. Unauthenticated → 401.
- Intake analyze / confirm-ready / chat: require_project_access — owner, or
  reviewer/admin (any project). Other officers → 403. Unauthenticated → 401.
"""

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

CREATE_URL = "/api/v1/projects"
ANALYZE_URL = f"/api/v1/projects/{PROJECT_ID}/intake/analyze"
CONFIRM_URL = f"/api/v1/projects/{PROJECT_ID}/intake/confirm-ready"
CHAT_URL = f"/api/v1/projects/{PROJECT_ID}/intake/chat"

CREATE_WITH_BUDGET = {
    "name": "โครงการจัดซื้อระบบคอมพิวเตอร์",
    "ministry": "กระทรวงการพัฒนาสังคมและความมั่นคงของมนุษย์",
    "budget": 5_000_000,
    "project_type": "it",
}
CREATE_WITHOUT_BUDGET = {
    "name": "โครงการทดสอบไม่มีงบ",
    "ministry": "กระทรวงทดสอบ",
    "project_type": "it",
}

ACCESS_CASES = [
    pytest.param("officer", USER_ID, 200, id="owner-officer"),
    pytest.param("officer", OTHER_USER_ID, 403, id="other-officer"),
    pytest.param("reviewer", OTHER_USER_ID, 200, id="reviewer"),
    pytest.param("admin", OTHER_USER_ID, 200, id="admin"),
]


def _make_user(user_id=USER_ID, role="officer"):
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
    budget=5_000_000,
    project_type="it",
    status="draft",
    current_step=1,
    quality_score=None,
    template_id=None,
    current_phase=0,
    analysis=None,
):
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
    project.analysis_json = analysis or {}
    project.extracted_fields = {}
    project.quality_score = quality_score
    project.template_id = template_id
    project.created_at = datetime(2024, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    project.updated_at = datetime(2024, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    return project


def _apply_defaults(project):
    if getattr(project, "id", None) is None:
        project.id = uuid.uuid4()
    if getattr(project, "created_at", None) is None:
        project.created_at = datetime.now(timezone.utc)
    if getattr(project, "updated_at", None) is None:
        project.updated_at = datetime.now(timezone.utc)


def _override_db(mock_db):
    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db


def _project_db(project, extra_results=None):
    mock_db = AsyncMock()
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    results = [project_result, *(extra_results or [])]
    if len(results) == 1:
        mock_db.execute = AsyncMock(return_value=project_result)
    else:
        mock_db.execute = AsyncMock(side_effect=results)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    _override_db(mock_db)
    return mock_db


def _create_db():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.refresh = AsyncMock(side_effect=lambda project: _apply_defaults(project))
    _override_db(mock_db)
    return mock_db


def _filled_fact_slots():
    slots = empty_slot_map()
    for key in FACT_REQUIRED_SLOTS:
        slots[key] = {
            "content": "ข้อมูลข้อเท็จจริงของโครงการทดสอบ",
            "status": "filled",
            "sources": ["ผู้ใช้ตอบในแชท"],
        }
    return slots


def _analyze_project():
    project = _make_project()
    project.extracted_fields = {
        "intake_texts": [{"name": "ข้อความผู้ใช้.txt", "text": "โครงการทดสอบวงเงิน"}],
    }
    return project


def _confirm_project():
    return _make_project(analysis={"slot_map": _filled_fact_slots()}, current_phase=1)


def _chat_project():
    return _make_project(
        analysis={"slot_map": _filled_fact_slots(), "analyzed": True},
        current_phase=2,
    )


def _install_chat_persist(project):
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

    app.state.db_session_factory = lambda: _CM()
    return persist


def _chat_db(project):
    room = MagicMock()
    room.id = uuid.uuid4()
    room_result = MagicMock()
    room_result.scalar_one_or_none.return_value = room
    _project_db(project, extra_results=[room_result])
    _install_chat_persist(project)
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
    user = _make_user(role="officer")

    async def override():
        return user

    app.dependency_overrides[get_current_user] = override
    return user


@pytest.fixture
def mock_reviewer_user():
    user = _make_user(role="reviewer")

    async def override():
        return user

    app.dependency_overrides[get_current_user] = override
    return user


@pytest.fixture
def mock_admin_user():
    user = _make_user(role="admin")

    async def override():
        return user

    app.dependency_overrides[get_current_user] = override
    return user


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _bind_user(role: str, user_id):
    user = _make_user(user_id=user_id, role=role)

    async def override():
        return user

    app.dependency_overrides[get_current_user] = override
    return user


# ---------------------------------------------------------------------------
# POST /projects — create (budget optional)
# ---------------------------------------------------------------------------


class TestCreateProjectRoleMatrix:
    """create_project depends only on get_current_user — any auth role may create."""

    def test_officer_create_with_budget_returns_201(self, client, mock_officer_user):
        mock_db = _create_db()
        response = client.post(CREATE_URL, json=CREATE_WITH_BUDGET)
        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["budget"] == CREATE_WITH_BUDGET["budget"]
        assert mock_db.add.call_args[0][0].budget == CREATE_WITH_BUDGET["budget"]

    def test_officer_create_without_budget_returns_201(self, client, mock_officer_user):
        mock_db = _create_db()
        response = client.post(CREATE_URL, json=CREATE_WITHOUT_BUDGET)
        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["budget"] == 0
        assert mock_db.add.call_args[0][0].budget == 0

    def test_reviewer_create_returns_201(self, client, mock_reviewer_user):
        _create_db()
        response = client.post(CREATE_URL, json=CREATE_WITH_BUDGET)
        assert response.status_code == 201
        assert response.json()["ok"] is True

    def test_admin_create_returns_201(self, client, mock_admin_user):
        _create_db()
        response = client.post(CREATE_URL, json=CREATE_WITHOUT_BUDGET)
        assert response.status_code == 201
        assert response.json()["data"]["budget"] == 0

    def test_unauthenticated_create_returns_401(self, client):
        response = client.post(CREATE_URL, json=CREATE_WITH_BUDGET)
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Intake phase 1–2: analyze / confirm-ready / chat
# ---------------------------------------------------------------------------


class TestIntakeAnalyzeRoleMatrix:
    @pytest.mark.parametrize("role,user_id,expected", ACCESS_CASES)
    @patch("app.api.v1.endpoints.intake.analyze_pack", new_callable=AsyncMock)
    def test_analyze_access(self, analyze_mock, client, role, user_id, expected):
        _bind_user(role, user_id)
        slots = empty_slot_map()
        slots["s1"] = {"content": "โครงการจัดซื้อ", "status": "filled", "sources": []}
        analyze_mock.return_value = {
            "slot_map": slots,
            "gap_questions": ["ขอวงเงิน"],
            "ready_to_compose": False,
            "analyzed": True,
        }
        _project_db(_analyze_project())
        response = client.post(ANALYZE_URL)
        assert response.status_code == expected
        if expected == 200:
            assert response.json()["data"]["analyzed"] is True

    def test_unauthenticated_analyze_returns_401(self, client):
        response = client.post(ANALYZE_URL)
        assert response.status_code == 401


class TestIntakeConfirmReadyRoleMatrix:
    @pytest.mark.parametrize("role,user_id,expected", ACCESS_CASES)
    def test_confirm_ready_access(self, client, role, user_id, expected):
        _bind_user(role, user_id)
        _project_db(_confirm_project())
        response = client.post(CONFIRM_URL, json={"confirm": True})
        assert response.status_code == expected
        if expected == 200:
            assert response.json()["data"]["ready_to_compose"] is True

    def test_unauthenticated_confirm_ready_returns_401(self, client):
        response = client.post(CONFIRM_URL, json={"confirm": True})
        assert response.status_code == 401


class TestIntakeChatRoleMatrix:
    @pytest.mark.parametrize("role,user_id,expected", ACCESS_CASES)
    def test_chat_access(self, client, role, user_id, expected):
        _bind_user(role, user_id)
        project = _chat_project()
        if expected == 200:
            _chat_db(project)
            with client.stream(
                "POST",
                CHAT_URL,
                json={"content": "ข้อมูลโครงการทดสอบ"},
            ) as response:
                body = b"".join(response.iter_bytes()).decode("utf-8")
            assert response.status_code == 200
            assert "event: done" in body
            return
        _project_db(project)
        response = client.post(CHAT_URL, json={"content": "ข้อมูลโครงการทดสอบ"})
        assert response.status_code == 403

    def test_unauthenticated_chat_returns_401(self, client):
        response = client.post(CHAT_URL, json={"content": "ข้อมูลโครงการทดสอบ"})
        assert response.status_code == 401
