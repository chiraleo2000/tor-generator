"""Unit tests for export API endpoints.

Tests cover:
- POST /api/v1/projects/{id}/export (trigger export)
- GET /api/v1/projects/{id}/export/status (check status)
- GET /api/v1/projects/{id}/export/download/{format} (download redirect)
- Retry logic (retry once on failure)
- Re-export support (clear old export and re-generate)
- Access control (project ownership)

Validates: Requirements 8.5, 8.6, 8.7, 8.8
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db, get_minio
from app.main import app
from app.models.project import Project
from app.models.tor_section import TORSection
from app.models.user import User
from app.schemas.export import ExportFileInfo
from app.services.export_service import ExportJob, ExportService, ProjectExportSnapshot


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
OTHER_USER_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")
PROJECT_ID = uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")
EXPORT_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    project.current_step = 8
    project.created_at = datetime(2024, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    project.updated_at = datetime(2024, 8, 15, 12, 0, 0, tzinfo=timezone.utc)
    return project


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def setup_app_state():
    """Setup app state and override get_db to prevent lifespan connections."""
    app.state.db_session_factory = None
    app.state.db_engine = None
    app.state.redis = None
    app.state.minio = None

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_export_jobs():
    """Clear the in-memory export job store before each test."""
    ExportService._jobs.clear()
    ExportService._jobs_by_id.clear()
    yield
    ExportService._jobs.clear()
    ExportService._jobs_by_id.clear()


@pytest.fixture
def mock_minio():
    """Create and register a mock MinIO client."""
    minio = MagicMock()
    minio.put_object.return_value = None
    minio.presigned_get_object.return_value = (
        "http://minio:9000/tor-documents/exports/test/file.docx?X-Amz-Signature=abc"
    )
    fake_obj = MagicMock()
    fake_obj.stream.return_value = [b"fake-docx"]
    fake_obj.read.return_value = b"fake-docx"
    fake_obj.close.return_value = None
    fake_obj.release_conn.return_value = None
    minio.get_object.return_value = fake_obj
    app.dependency_overrides[get_minio] = lambda: minio
    return minio


@pytest.fixture
def mock_officer_user():
    """Override get_current_user to return an officer user."""
    user = _make_user(role="officer")
    app.dependency_overrides[get_current_user] = lambda: user
    return user


@pytest.fixture
def mock_other_user():
    """Override get_current_user to return a different officer (not owner)."""
    user = _make_user(user_id=OTHER_USER_ID, role="officer")
    app.dependency_overrides[get_current_user] = lambda: user
    return user


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


def _setup_db_with_project(project):
    """Override get_db to return a mock session that finds the given project."""
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    async def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    return mock_db


# ---------------------------------------------------------------------------
# POST /projects/{id}/export
# ---------------------------------------------------------------------------


class TestTriggerExport:
    """Tests for POST /api/v1/projects/{id}/export."""

    @patch("app.services.export_service.asyncio.create_task")
    def test_trigger_export_returns_202(
        self, mock_create_task, client, mock_officer_user, mock_minio
    ):
        """Triggering export returns HTTP 202 with job info."""
        mock_create_task.return_value = MagicMock()
        _setup_db_with_project(_make_project())

        response = client.post(
            f"/api/v1/projects/{PROJECT_ID}/export",
            json={"use_thai_numerals": False, "url_ttl_hours": 24},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["project_id"] == str(PROJECT_ID)
        assert data["data"]["status"] in ("pending", "generating")
        assert "export_id" in data["data"]

    @patch("app.services.export_service.asyncio.create_task")
    def test_trigger_export_default_params(
        self, mock_create_task, client, mock_officer_user, mock_minio
    ):
        """Triggering export with no body uses defaults."""
        mock_create_task.return_value = MagicMock()
        _setup_db_with_project(_make_project())

        response = client.post(f"/api/v1/projects/{PROJECT_ID}/export")
        assert response.status_code == 202

    @patch("app.services.export_service.asyncio.create_task")
    def test_trigger_export_custom_ttl(
        self, mock_create_task, client, mock_officer_user, mock_minio
    ):
        """Triggering export with custom TTL is accepted."""
        mock_create_task.return_value = MagicMock()
        _setup_db_with_project(_make_project())

        response = client.post(
            f"/api/v1/projects/{PROJECT_ID}/export",
            json={"url_ttl_hours": 48},
        )
        assert response.status_code == 202

    @patch("app.services.export_service.asyncio.create_task")
    def test_trigger_export_invalid_ttl_too_low(
        self, mock_create_task, client, mock_officer_user, mock_minio
    ):
        """TTL below 1 hour is rejected with 422."""
        mock_create_task.return_value = MagicMock()
        _setup_db_with_project(_make_project())

        response = client.post(
            f"/api/v1/projects/{PROJECT_ID}/export",
            json={"url_ttl_hours": 0},
        )
        assert response.status_code == 422

    @patch("app.services.export_service.asyncio.create_task")
    def test_trigger_export_invalid_ttl_too_high(
        self, mock_create_task, client, mock_officer_user, mock_minio
    ):
        """TTL above 168 hours is rejected with 422."""
        mock_create_task.return_value = MagicMock()
        _setup_db_with_project(_make_project())

        response = client.post(
            f"/api/v1/projects/{PROJECT_ID}/export",
            json={"url_ttl_hours": 200},
        )
        assert response.status_code == 422

    @patch("app.services.export_service.asyncio.create_task")
    def test_trigger_export_project_not_found(
        self, mock_create_task, client, mock_officer_user, mock_minio
    ):
        """Export for non-existent project returns 404."""
        mock_create_task.return_value = MagicMock()
        _setup_db_with_project(None)

        response = client.post(f"/api/v1/projects/{uuid.uuid4()}/export")
        assert response.status_code == 404

    @patch("app.services.export_service.asyncio.create_task")
    def test_trigger_export_forbidden_for_other_user(
        self, mock_create_task, client, mock_other_user, mock_minio
    ):
        """Other officer cannot export a project they don't own."""
        mock_create_task.return_value = MagicMock()
        _setup_db_with_project(_make_project())  # Owned by USER_ID, not OTHER_USER_ID

        response = client.post(f"/api/v1/projects/{PROJECT_ID}/export")
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /projects/{id}/export/status
# ---------------------------------------------------------------------------


class TestExportStatus:
    """Tests for GET /api/v1/projects/{id}/export/status."""

    def test_status_no_export_returns_404(self, client, mock_officer_user, mock_minio):
        """Status for project with no export returns 404."""
        _setup_db_with_project(_make_project())

        response = client.get(f"/api/v1/projects/{PROJECT_ID}/export/status")
        assert response.status_code == 404

    def test_status_generating_export(self, client, mock_officer_user, mock_minio):
        """Status returns current job state while generating."""
        _setup_db_with_project(_make_project())

        job = ExportJob(
            export_id=EXPORT_ID,
            project_id=PROJECT_ID,
            use_thai_numerals=False,
            url_ttl_hours=24,
        )
        job.status = "generating"
        ExportService._jobs[PROJECT_ID] = job
        ExportService._jobs_by_id[EXPORT_ID] = job

        response = client.get(f"/api/v1/projects/{PROJECT_ID}/export/status")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["status"] == "generating"
        assert data["data"]["export_id"] == str(EXPORT_ID)

    def test_status_completed_export(self, client, mock_officer_user, mock_minio):
        """Status shows completed with file info after generation."""
        _setup_db_with_project(_make_project())

        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        job.files = [
            ExportFileInfo(
                format="docx",
                storage_path="exports/test/tor.docx",
                download_url="http://minio:9000/signed-url-docx",
                file_size_bytes=12345,
            ),
            ExportFileInfo(
                format="pdf",
                storage_path="exports/test/tor.pdf",
                download_url="http://minio:9000/signed-url-pdf",
                file_size_bytes=67890,
            ),
        ]
        ExportService._jobs[PROJECT_ID] = job
        ExportService._jobs_by_id[EXPORT_ID] = job

        response = client.get(f"/api/v1/projects/{PROJECT_ID}/export/status")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "completed"
        assert len(data["data"]["files"]) == 2
        assert data["data"]["files"][0]["format"] == "docx"
        assert data["data"]["files"][1]["format"] == "pdf"

    def test_status_failed_export(self, client, mock_officer_user, mock_minio):
        """Status shows failure message after export fails."""
        _setup_db_with_project(_make_project())

        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        job.status = "failed"
        job.error_message = "การสร้างเอกสารล้มเหลว"
        job.retry_count = 1
        job.completed_at = datetime.now(timezone.utc)
        ExportService._jobs[PROJECT_ID] = job
        ExportService._jobs_by_id[EXPORT_ID] = job

        response = client.get(f"/api/v1/projects/{PROJECT_ID}/export/status")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "failed"
        assert data["data"]["error_message"] == "การสร้างเอกสารล้มเหลว"
        assert data["data"]["retry_count"] == 1


# ---------------------------------------------------------------------------
# GET /projects/{id}/export/download/{format}
# ---------------------------------------------------------------------------


class TestDownloadExport:
    """Tests for GET /api/v1/projects/{id}/export/download/{format}."""

    def test_download_no_export_returns_404(self, client, mock_officer_user, mock_minio):
        """Download without prior export returns 404."""
        _setup_db_with_project(_make_project())

        response = client.get(
            f"/api/v1/projects/{PROJECT_ID}/export/download/docx",
            follow_redirects=False,
        )
        assert response.status_code == 404

    def test_download_docx_streams(self, client, mock_officer_user, mock_minio):
        """Download DOCX streams file bytes with auth (not a bare MinIO redirect)."""
        _setup_db_with_project(_make_project())

        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        job.status = "completed"
        job.files = [
            ExportFileInfo(
                format="docx",
                storage_path="exports/test/tor.docx",
                download_url="http://minio:9000/signed-url-docx",
                file_size_bytes=12345,
            ),
            ExportFileInfo(
                format="pdf",
                storage_path="exports/test/tor.pdf",
                download_url="http://minio:9000/signed-url-pdf",
                file_size_bytes=67890,
            ),
        ]
        ExportService._jobs[PROJECT_ID] = job
        ExportService._jobs_by_id[EXPORT_ID] = job

        response = client.get(
            f"/api/v1/projects/{PROJECT_ID}/export/download/docx",
        )
        assert response.status_code == 200
        assert "attachment" in response.headers.get("content-disposition", "")
        assert response.content == b"fake-docx"

    def test_download_pdf_streams(self, client, mock_officer_user, mock_minio):
        """Download PDF streams file bytes."""
        _setup_db_with_project(_make_project())

        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        job.status = "completed"
        job.files = [
            ExportFileInfo(
                format="docx",
                storage_path="exports/test/tor.docx",
                download_url="http://minio:9000/signed-url-docx",
                file_size_bytes=12345,
            ),
            ExportFileInfo(
                format="pdf",
                storage_path="exports/test/tor.pdf",
                download_url="http://minio:9000/signed-url-pdf",
                file_size_bytes=67890,
            ),
        ]
        ExportService._jobs[PROJECT_ID] = job
        ExportService._jobs_by_id[EXPORT_ID] = job

        response = client.get(
            f"/api/v1/projects/{PROJECT_ID}/export/download/pdf",
        )
        assert response.status_code == 200
        assert "TOR.pdf" in response.headers.get("content-disposition", "")

    def test_download_invalid_format_returns_422(
        self, client, mock_officer_user, mock_minio
    ):
        """Invalid format returns 422."""
        _setup_db_with_project(_make_project())

        response = client.get(
            f"/api/v1/projects/{PROJECT_ID}/export/download/xlsx",
            follow_redirects=False,
        )
        assert response.status_code == 422

    def test_download_not_completed_returns_404(
        self, client, mock_officer_user, mock_minio
    ):
        """Download while still generating returns 404."""
        _setup_db_with_project(_make_project())

        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        job.status = "generating"
        ExportService._jobs[PROJECT_ID] = job
        ExportService._jobs_by_id[EXPORT_ID] = job

        response = client.get(
            f"/api/v1/projects/{PROJECT_ID}/export/download/docx",
            follow_redirects=False,
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Export Service - Unit Tests (no HTTP)
# ---------------------------------------------------------------------------


class TestExportServiceLogic:
    """Tests for ExportService business logic."""

    def test_export_job_starts_as_pending(self):
        """A new export job starts with pending status."""
        job = ExportJob(export_id=uuid.uuid4(), project_id=PROJECT_ID)
        assert job.status == "pending"
        assert job.retry_count == 0
        assert job.error_message is None
        assert job.files == []

    def test_clear_project_export_removes_job(self):
        """Clearing project export removes job from both indexes."""
        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        ExportService._jobs[PROJECT_ID] = job
        ExportService._jobs_by_id[EXPORT_ID] = job

        ExportService.clear_project_export(PROJECT_ID)

        assert ExportService._jobs.get(PROJECT_ID) is None
        assert ExportService._jobs_by_id.get(EXPORT_ID) is None

    def test_clear_nonexistent_project_no_error(self):
        """Clearing a non-existent project doesn't raise."""
        ExportService.clear_project_export(uuid.uuid4())

    def test_get_job_for_project_returns_none_when_empty(self):
        """get_job_for_project returns None with no jobs."""
        assert ExportService.get_job_for_project(PROJECT_ID) is None

    def test_get_job_for_project_returns_job(self):
        """get_job_for_project returns the stored job."""
        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        ExportService._jobs[PROJECT_ID] = job
        assert ExportService.get_job_for_project(PROJECT_ID) is job

    def test_get_job_by_id_returns_job(self):
        """get_job_by_id returns the stored job."""
        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        ExportService._jobs_by_id[EXPORT_ID] = job
        assert ExportService.get_job_by_id(EXPORT_ID) is job

    def test_get_download_url_returns_none_when_no_job(self):
        """get_download_url returns None when there is no export job."""
        minio = MagicMock()
        result = ExportService.get_download_url(minio, PROJECT_ID, "docx")
        assert result is None

    def test_get_download_url_returns_none_when_not_completed(self):
        """get_download_url returns None for non-completed jobs."""
        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        job.status = "generating"
        ExportService._jobs[PROJECT_ID] = job

        minio = MagicMock()
        result = ExportService.get_download_url(minio, PROJECT_ID, "docx")
        assert result is None

    def test_get_download_url_returns_none_for_wrong_format(self):
        """get_download_url returns None if format not in files."""
        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        job.status = "completed"
        job.files = [
            ExportFileInfo(
                format="docx",
                storage_path="exports/test/tor.docx",
                download_url="http://old-url",
                file_size_bytes=12345,
            ),
        ]
        ExportService._jobs[PROJECT_ID] = job

        minio = MagicMock()
        result = ExportService.get_download_url(minio, PROJECT_ID, "pdf")
        assert result is None

    @patch("app.services.export_service.get_settings")
    def test_get_download_url_generates_fresh_url(self, mock_settings):
        """get_download_url generates a fresh signed URL for completed jobs."""
        mock_settings.return_value.minio_bucket = "tor-documents"

        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        job.status = "completed"
        job.files = [
            ExportFileInfo(
                format="docx",
                storage_path="exports/test/tor.docx",
                download_url="http://old-url",
                file_size_bytes=12345,
            ),
        ]
        ExportService._jobs[PROJECT_ID] = job

        minio = MagicMock()
        minio.presigned_get_object.return_value = "http://fresh-signed-url"

        result = ExportService.get_download_url(minio, PROJECT_ID, "docx")
        assert result is not None
        assert result.download_url == "http://fresh-signed-url"
        assert result.format == "docx"
        assert result.expires_in_seconds == 24 * 3600

    def test_re_export_clears_old_job(self):
        """Re-export clears previous job so a new one can be created."""
        old_job = ExportJob(export_id=uuid.uuid4(), project_id=PROJECT_ID)
        old_job.status = "completed"
        ExportService._jobs[PROJECT_ID] = old_job
        ExportService._jobs_by_id[old_job.export_id] = old_job

        ExportService.clear_project_export(PROJECT_ID)
        assert ExportService.get_job_for_project(PROJECT_ID) is None


# ---------------------------------------------------------------------------
# Export Job to_response
# ---------------------------------------------------------------------------


class TestExportJobResponse:
    """Tests for ExportJob serialization."""

    def test_to_response_pending(self):
        """Pending job serializes correctly."""
        job = ExportJob(
            export_id=EXPORT_ID,
            project_id=PROJECT_ID,
            use_thai_numerals=True,
            url_ttl_hours=48,
        )
        resp = job.to_response()
        assert resp.export_id == EXPORT_ID
        assert resp.project_id == PROJECT_ID
        assert resp.status == "pending"
        assert resp.retry_count == 0
        assert resp.files == []
        assert resp.error_message is None

    def test_to_response_completed_with_files(self):
        """Completed job with files serializes correctly."""
        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        job.status = "completed"
        job.completed_at = datetime(2024, 8, 15, 14, 0, 0, tzinfo=timezone.utc)
        job.files = [
            ExportFileInfo(
                format="docx",
                storage_path="exports/test/tor.docx",
                download_url="http://minio/url",
                file_size_bytes=5000,
            ),
        ]
        resp = job.to_response()
        assert resp.status == "completed"
        assert len(resp.files) == 1
        assert resp.files[0].format == "docx"
        assert resp.completed_at is not None

    def test_to_response_failed(self):
        """Failed job serializes error message and retry count."""
        job = ExportJob(export_id=EXPORT_ID, project_id=PROJECT_ID)
        job.status = "failed"
        job.error_message = "ล้มเหลว"
        job.retry_count = 1
        job.completed_at = datetime.now(timezone.utc)
        resp = job.to_response()
        assert resp.status == "failed"
        assert resp.error_message == "ล้มเหลว"
        assert resp.retry_count == 1


class TestProjectExportSnapshot:
    """Background export must not keep the request-scoped ORM instance."""

    def test_from_project_copies_scalars(self):
        project = _make_project()
        snapshot = ProjectExportSnapshot.from_project(project)
        assert snapshot.id == PROJECT_ID
        assert snapshot.name == "โครงการทดสอบ"
        assert snapshot.ministry == "กระทรวงทดสอบ"
        assert snapshot.budget == 5000000
        assert snapshot.project_type == "it"
