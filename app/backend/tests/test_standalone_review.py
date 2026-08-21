"""Smoke tests for standalone review and admin users routers."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db
from app.main import app
from app.models.user import User


def _user(role="admin"):
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.role = role
    user.email = "admin@example.go.th"
    user.name = "Admin"
    return user


def test_standalone_review_run_with_text():
    user = _user("officer")
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = mock_db
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/v1/review/run",
        json={"text": "1. ความเป็นมา\nโครงการทดสอบระบบจัดซื้อจัดจ้างของหน่วยงาน"},
    )
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "quality_score" in body["data"]


def test_standalone_review_run_requires_text():
    user = _user("officer")
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = mock_db
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post("/api/v1/review/run", json={})
    app.dependency_overrides.clear()
    assert response.status_code == 400


def test_standalone_review_get_not_found():
    user = _user("officer")
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = mock_db
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/api/v1/review/missing-id")
    app.dependency_overrides.clear()
    assert response.status_code == 404


def test_standalone_review_extract_empty_file():
    user = _user("officer")
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = mock_db
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/v1/review/extract",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    app.dependency_overrides.clear()
    assert response.status_code == 400


def test_standalone_review_extract_then_run_with_id():
    from app.api.v1.endpoints.standalone_review import _REVIEW_JOBS

    user = _user("officer")
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = mock_db
    client = TestClient(app, raise_server_exceptions=False)
    job_id = None
    extracted_result = MagicMock()
    extracted_result.text = "1. ความเป็นมา\nโครงการทดสอบระบบจัดซื้อจัดจ้าง"
    try:
        with patch(
            "app.api.v1.endpoints.standalone_review.extract_text",
            return_value=extracted_result,
        ):
            extracted = client.post(
                "/api/v1/review/extract",
                files={"file": ("tor.txt", b"tor body content", "text/plain")},
            )
        assert extracted.status_code == 200
        job_id = extracted.json()["data"]["id"]
        assert extracted.json()["data"]["extracted_text"]
        ran = client.post("/api/v1/review/run", json={"id": job_id})
        assert ran.status_code == 200
        assert "quality_score" in ran.json()["data"]
        assert ran.json()["data"]["status"] == "completed"
    finally:
        if job_id:
            _REVIEW_JOBS.pop(job_id, None)
        app.dependency_overrides.clear()


def test_compare_projects_requires_two_ids():
    user = _user("officer")
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = mock_db
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/v1/review/compare-projects",
        json={"project_ids": [str(uuid.uuid4())]},
    )
    app.dependency_overrides.clear()
    assert response.status_code == 400


def test_compare_projects_jaccard_with_mocked_rows():
    user = _user("officer")
    app.dependency_overrides[get_current_user] = lambda: user

    left = MagicMock()
    left.name = "โครงการ ก"
    right = MagicMock()
    right.name = "โครงการ ข"
    section = MagicMock()
    section.content = "ความเป็นมา ของโครงการ ทดสอบ"

    mock_db = AsyncMock()
    project_result_a = MagicMock()
    project_result_a.scalar_one_or_none.return_value = left
    project_result_b = MagicMock()
    project_result_b.scalar_one_or_none.return_value = right
    sections_a = MagicMock()
    sections_a.scalars.return_value.all.return_value = [section]
    sections_b = MagicMock()
    sections_b.scalars.return_value.all.return_value = [section]
    mock_db.execute = AsyncMock(
        side_effect=[project_result_a, sections_a, project_result_b, sections_b]
    )

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/v1/review/compare-projects",
        json={"project_ids": [str(uuid.uuid4()), str(uuid.uuid4())]},
    )
    app.dependency_overrides.clear()
    assert response.status_code == 200
    comparisons = response.json()["data"]["comparisons"]
    assert comparisons
    assert comparisons[0]["jaccard"] == 1.0
    assert comparisons[0]["left"] == "โครงการ ก"
    assert comparisons[0]["right"] == "โครงการ ข"


def test_jaccard_helpers():
    from app.api.v1.endpoints.standalone_review import _jaccard, _token_set

    assert _token_set("a bb\nccc") == {"bb", "ccc"}
    assert _jaccard("", "") == 0.0
    assert _jaccard("foo bar baz", "foo bar baz") == 1.0
    similar = _jaccard("foo bar baz", "foo bar qux")
    assert 0.0 < similar < 1.0


def test_compare_extract_jobs_jaccard():
    from app.api.v1.endpoints.standalone_review import _REVIEW_JOBS

    user = _user("officer")
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = mock_db
    left_id = str(uuid.uuid4())
    right_id = str(uuid.uuid4())
    shared = "ความเป็นมา ของโครงการ ทดสอบ ระบบ"
    _REVIEW_JOBS[left_id] = {
        "id": left_id,
        "filename": "tor-a.docx",
        "extracted_text": shared,
        "status": "extracted",
        "result": None,
    }
    _REVIEW_JOBS[right_id] = {
        "id": right_id,
        "filename": "tor-b.docx",
        "extracted_text": shared,
        "status": "extracted",
        "result": None,
    }
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = client.post(
            "/api/v1/review/compare-projects",
            json={"extract_ids": [left_id, right_id]},
        )
    finally:
        _REVIEW_JOBS.pop(left_id, None)
        _REVIEW_JOBS.pop(right_id, None)
        app.dependency_overrides.clear()
    assert response.status_code == 200
    comparisons = response.json()["data"]["comparisons"]
    assert len(comparisons) == 1
    assert comparisons[0]["jaccard"] == 1.0
    assert comparisons[0]["left"] == "tor-a.docx"
    assert comparisons[0]["right"] == "tor-b.docx"
    assert comparisons[0]["left_id"] == left_id
    assert comparisons[0]["right_id"] == right_id


def test_compare_mixed_project_and_extract():
    from app.api.v1.endpoints.standalone_review import _REVIEW_JOBS

    user = _user("officer")
    app.dependency_overrides[get_current_user] = lambda: user

    project = MagicMock()
    project.name = "โครงการหลัก"
    section = MagicMock()
    section.content = "ขอบเขต งาน ทดสอบ"

    mock_db = AsyncMock()
    project_result = MagicMock()
    project_result.scalar_one_or_none.return_value = project
    sections_result = MagicMock()
    sections_result.scalars.return_value.all.return_value = [section]
    mock_db.execute = AsyncMock(side_effect=[project_result, sections_result])

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    extract_id = str(uuid.uuid4())
    _REVIEW_JOBS[extract_id] = {
        "id": extract_id,
        "filename": "compare.pdf",
        "extracted_text": "ขอบเขต งาน ทดสอบ",
        "status": "extracted",
        "result": None,
    }
    project_id = str(uuid.uuid4())
    client = TestClient(app, raise_server_exceptions=False)
    try:
        response = client.post(
            "/api/v1/review/compare-projects",
            json={"project_ids": [project_id], "extract_ids": [extract_id]},
        )
    finally:
        _REVIEW_JOBS.pop(extract_id, None)
        app.dependency_overrides.clear()
    assert response.status_code == 200
    comparisons = response.json()["data"]["comparisons"]
    assert comparisons[0]["jaccard"] == 1.0
    assert comparisons[0]["left"] == "โครงการหลัก"
    assert comparisons[0]["right"] == "compare.pdf"


def test_compare_extract_ids_requires_two():
    user = _user("officer")
    app.dependency_overrides[get_current_user] = lambda: user

    async def mock_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = mock_db
    client = TestClient(app, raise_server_exceptions=False)
    response = client.post(
        "/api/v1/review/compare-projects",
        json={"extract_ids": [str(uuid.uuid4())]},
    )
    app.dependency_overrides.clear()
    assert response.status_code == 400
