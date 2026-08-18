"""Unit tests for file upload endpoints.

Tests cover:
- POST /api/v1/files/upload (multipart upload with rate limiting)
- GET /api/v1/files/{id}/extracted-text (get extracted text)

Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5, 14.6
"""

import io
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.deps import get_current_user, get_db, get_minio
from app.main import app
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.rate_limiter import rate_limit_upload


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
FILE_ID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _make_user(user_id=USER_ID, role="officer"):
    """Create a mock User object."""
    user = MagicMock(spec=User)
    user.id = user_id
    user.role = role
    user.email = "test@example.go.th"
    user.name = "Test User"
    return user


def _make_uploaded_file(
    file_id=FILE_ID,
    user_id=USER_ID,
    original_name="document.pdf",
    mime_type="application/pdf",
    file_size_bytes=1024,
    ocr_status="completed",
    extracted_text="ข้อความที่ดึงจากไฟล์",
    project_id=None,
):
    """Create a mock UploadedFile object."""
    f = MagicMock(spec=UploadedFile)
    f.id = file_id
    f.project_id = project_id
    f.uploaded_by = user_id
    f.original_name = original_name
    f.storage_path = f"uploads/{user_id}/{file_id}.pdf"
    f.mime_type = mime_type
    f.file_size_bytes = file_size_bytes
    f.ocr_status = ocr_status
    f.extracted_text = extracted_text
    f.uploaded_at = datetime(2024, 8, 15, 10, 0, 0, tzinfo=timezone.utc)
    return f


@pytest.fixture(autouse=True)
def setup_app_state():
    """Setup app state and override dependencies for tests."""
    app.state.db_session_factory = None
    app.state.db_engine = None
    app.state.redis = None
    app.state.minio = MagicMock()

    # Override rate limiting to always allow (tested separately in test_rate_limiter.py)
    async def mock_rate_limit(request: Request):
        return None

    app.dependency_overrides[rate_limit_upload] = mock_rate_limit

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
def mock_minio():
    """Override get_minio to return a mock MinIO client."""
    minio_client = MagicMock()
    minio_client.put_object = MagicMock()

    async def override(request: Request):
        return minio_client

    app.dependency_overrides[get_minio] = override
    return minio_client


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app, raise_server_exceptions=False)


def _create_upload_file(content: bytes = b"fake pdf content", filename: str = "test.pdf", content_type: str = "application/pdf"):
    """Helper to create a file-like object for upload."""
    return ("file", (filename, io.BytesIO(content), content_type))


# ---------------------------------------------------------------------------
# POST /files/upload — Upload file
# ---------------------------------------------------------------------------


class TestUploadFile:
    """Tests for POST /api/v1/files/upload."""

    def test_upload_pdf_success(self, client, mock_officer_user, mock_minio):
        """Successfully uploads a PDF file and returns 201."""
        file_content = b"%PDF-1.4 fake pdf content for testing"

        with patch("app.api.v1.endpoints.files._extract_text_from_content", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = ("ข้อความทดสอบ", "completed", [])

            mock_db = AsyncMock()
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()

            async def override_db():
                yield mock_db

            app.dependency_overrides[get_db] = override_db

            response = client.post(
                "/api/v1/files/upload",
                files=[_create_upload_file(file_content, "document.pdf", "application/pdf")],
            )

        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["original_name"] == "document.pdf"
        assert data["data"]["mime_type"] == "application/pdf"
        assert data["data"]["ocr_status"] == "completed"

    def test_upload_docx_success(self, client, mock_officer_user, mock_minio):
        """Successfully uploads a DOCX file."""
        file_content = b"PK\x03\x04word/document.xml fake docx content"
        docx_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        with patch("app.api.v1.endpoints.files._extract_text_from_content", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = ("ข้อความจากเอกสาร Word", "completed", [])

            mock_db = AsyncMock()
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()

            async def override_db():
                yield mock_db

            app.dependency_overrides[get_db] = override_db

            response = client.post(
                "/api/v1/files/upload",
                files=[_create_upload_file(file_content, "report.docx", docx_mime)],
            )

        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["original_name"] == "report.docx"
        assert data["data"]["mime_type"] == docx_mime

    def test_upload_with_project_id(self, client, mock_officer_user, mock_minio):
        """Upload file associated with a project."""
        file_content = b"%PDF-1.4 test"
        project_id = str(uuid.uuid4())

        with patch("app.api.v1.endpoints.files._extract_text_from_content", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = ("text", "completed", [])

            mock_db = AsyncMock()
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()

            async def override_db():
                yield mock_db

            app.dependency_overrides[get_db] = override_db

            response = client.post(
                "/api/v1/files/upload",
                files=[_create_upload_file(file_content)],
                data={"project_id": project_id},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["project_id"] == project_id

    def test_upload_unsupported_mime_type_returns_400(self, client, mock_officer_user, mock_minio):
        """Uploading an executable is rejected even if the client claims a document type."""
        response = client.post(
            "/api/v1/files/upload",
            files=[_create_upload_file(b"MZ\x90\x00not-a-pdf", "malware.exe", "application/pdf")],
        )

        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_upload_exceeds_max_size_returns_400(self, client, mock_officer_user, mock_minio):
        """File exceeding 20MB returns 400."""
        # 21 MB file
        large_content = b"x" * (21 * 1024 * 1024)

        response = client.post(
            "/api/v1/files/upload",
            files=[_create_upload_file(large_content, "big.pdf", "application/pdf")],
        )

        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_upload_empty_file_returns_400(self, client, mock_officer_user, mock_minio):
        """Empty file returns 400."""
        response = client.post(
            "/api/v1/files/upload",
            files=[_create_upload_file(b"", "empty.pdf", "application/pdf")],
        )

        assert response.status_code == 400
        data = response.json()
        assert data["ok"] is False

    def test_upload_unauthenticated_returns_401(self, client, mock_minio):
        """Request without authentication returns 401."""
        # No get_current_user override
        response = client.post(
            "/api/v1/files/upload",
            files=[_create_upload_file(b"content", "test.pdf", "application/pdf")],
        )

        assert response.status_code == 401

    def test_upload_ocr_timeout_returns_timeout_status(self, client, mock_officer_user, mock_minio):
        """When OCR times out, file is still created with timeout status."""
        file_content = b"%PDF-1.4 scanned document"

        with patch("app.api.v1.endpoints.files._extract_text_from_content", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = (None, "timeout", ["OCR timed out after 30s"])

            mock_db = AsyncMock()
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()

            async def override_db():
                yield mock_db

            app.dependency_overrides[get_db] = override_db

            response = client.post(
                "/api/v1/files/upload",
                files=[_create_upload_file(file_content, "scanned.pdf", "application/pdf")],
            )

        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["ocr_status"] == "timeout"

    def test_upload_extraction_failed_returns_failed_status(self, client, mock_officer_user, mock_minio):
        """When text extraction fails, file is still created with failed status."""
        file_content = b"%PDF-1.4 corrupted"

        with patch("app.api.v1.endpoints.files._extract_text_from_content", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = (None, "failed", ["Extraction failed"])

            mock_db = AsyncMock()
            mock_db.add = MagicMock()
            mock_db.flush = AsyncMock()

            async def override_db():
                yield mock_db

            app.dependency_overrides[get_db] = override_db

            response = client.post(
                "/api/v1/files/upload",
                files=[_create_upload_file(file_content, "corrupt.pdf", "application/pdf")],
            )

        assert response.status_code == 201
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["ocr_status"] == "failed"


# ---------------------------------------------------------------------------
# GET /files/{id}/extracted-text — Get extracted text
# ---------------------------------------------------------------------------


class TestGetExtractedText:
    """Tests for GET /api/v1/files/{id}/extracted-text."""

    def test_get_extracted_text_success(self, client, mock_officer_user):
        """Successfully returns extracted text for a file."""
        uploaded_file = _make_uploaded_file()

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = uploaded_file
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/files/{FILE_ID}/extracted-text")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["extracted_text"] == "ข้อความที่ดึงจากไฟล์"
        assert data["data"]["ocr_status"] == "completed"
        assert data["data"]["warnings"] == []

    def test_get_extracted_text_with_timeout_status(self, client, mock_officer_user):
        """Returns timeout warning when OCR timed out."""
        uploaded_file = _make_uploaded_file(ocr_status="timeout", extracted_text=None)

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = uploaded_file
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/files/{FILE_ID}/extracted-text")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["data"]["ocr_status"] == "timeout"
        assert len(data["data"]["warnings"]) == 1

    def test_get_extracted_text_with_failed_status(self, client, mock_officer_user):
        """Returns failure warning when extraction failed."""
        uploaded_file = _make_uploaded_file(ocr_status="failed", extracted_text=None)

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = uploaded_file
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/files/{FILE_ID}/extracted-text")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["ocr_status"] == "failed"
        assert len(data["data"]["warnings"]) == 1

    def test_get_extracted_text_pending_status(self, client, mock_officer_user):
        """Returns pending warning when file is still processing."""
        uploaded_file = _make_uploaded_file(ocr_status="pending", extracted_text=None)

        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = uploaded_file
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        response = client.get(f"/api/v1/files/{FILE_ID}/extracted-text")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["ocr_status"] == "pending"
        assert len(data["data"]["warnings"]) == 1

    def test_get_extracted_text_not_found(self, client, mock_officer_user):
        """Returns 404 for non-existent file."""
        mock_db = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=result)

        async def override_db():
            yield mock_db

        app.dependency_overrides[get_db] = override_db

        non_existent_id = uuid.uuid4()
        response = client.get(f"/api/v1/files/{non_existent_id}/extracted-text")
        assert response.status_code == 404
        data = response.json()
        assert data["ok"] is False
        assert data["error"]["code"] == "NOT_FOUND"

    def test_get_extracted_text_unauthenticated_returns_401(self, client):
        """Unauthenticated request returns 401."""
        response = client.get(f"/api/v1/files/{FILE_ID}/extracted-text")
        assert response.status_code == 401
