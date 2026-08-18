"""Unit tests for MinIO storage service.

Tests cover:
- File upload to MinIO with correct path structure
- Download URL generation with TTL validation
- TTL boundary enforcement (1–168 hours)
- Convenience methods for DOCX and PDF upload
- Combined upload-and-get-url operation
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.export.minio_storage import (
    CONTENT_TYPE_DOCX,
    CONTENT_TYPE_PDF,
    DEFAULT_DOWNLOAD_TTL_HOURS,
    MAX_TTL_HOURS,
    MIN_TTL_HOURS,
    MinIOStorageService,
)


@pytest.fixture
def mock_minio_client():
    """Create a mock MinIO client."""
    client = MagicMock()
    client.put_object = MagicMock()
    client.presigned_get_object = MagicMock(
        return_value="http://localhost:9000/tor-documents/exports/proj-1/file.pdf?token=abc"
    )
    return client


@pytest.fixture
def storage_service(mock_minio_client):
    """Create a MinIOStorageService with a mock client."""
    with patch("app.export.minio_storage.get_settings") as mock_settings:
        mock_settings.return_value.minio_bucket = "tor-documents"
        service = MinIOStorageService(mock_minio_client, bucket="tor-documents")
    return service


# =============================================================================
# Upload Tests
# =============================================================================


class TestUploadFile:
    """Tests for the upload_file method."""

    def test_upload_file_calls_put_object(self, storage_service, mock_minio_client):
        """upload_file should call minio client put_object."""
        file_bytes = b"test pdf content"
        result = storage_service.upload_file(
            file_bytes=file_bytes,
            project_id="proj-123",
            filename="tor_export.pdf",
            content_type="application/pdf",
        )
        mock_minio_client.put_object.assert_called_once()
        assert result == "exports/proj-123/tor_export.pdf"

    def test_upload_file_path_structure(self, storage_service, mock_minio_client):
        """Uploaded files follow exports/{project_id}/{filename} structure."""
        storage_service.upload_file(
            file_bytes=b"content",
            project_id="my-project",
            filename="document.docx",
            content_type=CONTENT_TYPE_DOCX,
        )
        call_kwargs = mock_minio_client.put_object.call_args
        assert call_kwargs[1]["bucket_name"] == "tor-documents"
        assert call_kwargs[1]["object_name"] == "exports/my-project/document.docx"

    def test_upload_file_sets_content_type(self, storage_service, mock_minio_client):
        """Content type is passed correctly to MinIO."""
        storage_service.upload_file(
            file_bytes=b"content",
            project_id="proj-1",
            filename="file.pdf",
            content_type=CONTENT_TYPE_PDF,
        )
        call_kwargs = mock_minio_client.put_object.call_args
        assert call_kwargs[1]["content_type"] == CONTENT_TYPE_PDF

    def test_upload_file_sets_correct_length(self, storage_service, mock_minio_client):
        """Length passed to put_object matches actual file size."""
        file_bytes = b"x" * 1024
        storage_service.upload_file(
            file_bytes=file_bytes,
            project_id="proj-1",
            filename="file.pdf",
            content_type=CONTENT_TYPE_PDF,
        )
        call_kwargs = mock_minio_client.put_object.call_args
        assert call_kwargs[1]["length"] == 1024


class TestUploadConvenienceMethods:
    """Tests for upload_docx and upload_pdf convenience methods."""

    def test_upload_docx_uses_correct_content_type(self, storage_service, mock_minio_client):
        """upload_docx sets the DOCX content type."""
        storage_service.upload_docx(
            file_bytes=b"docx bytes",
            project_id="proj-1",
            filename="tor.docx",
        )
        call_kwargs = mock_minio_client.put_object.call_args
        assert call_kwargs[1]["content_type"] == CONTENT_TYPE_DOCX

    def test_upload_pdf_uses_correct_content_type(self, storage_service, mock_minio_client):
        """upload_pdf sets the PDF content type."""
        storage_service.upload_pdf(
            file_bytes=b"pdf bytes",
            project_id="proj-1",
            filename="tor.pdf",
        )
        call_kwargs = mock_minio_client.put_object.call_args
        assert call_kwargs[1]["content_type"] == CONTENT_TYPE_PDF


# =============================================================================
# Download URL Tests
# =============================================================================


class TestGenerateDownloadUrl:
    """Tests for the generate_download_url method."""

    def test_generates_presigned_url(self, storage_service, mock_minio_client):
        """generate_download_url returns the presigned URL from MinIO client."""
        url = storage_service.generate_download_url("exports/proj-1/file.pdf")
        assert "http://localhost:9000" in url
        mock_minio_client.presigned_get_object.assert_called_once()

    def test_default_ttl_is_24_hours(self, storage_service, mock_minio_client):
        """Default TTL is 24 hours."""
        storage_service.generate_download_url("exports/proj-1/file.pdf")
        call_kwargs = mock_minio_client.presigned_get_object.call_args
        assert call_kwargs[1]["expires"] == timedelta(hours=24)

    def test_custom_ttl(self, storage_service, mock_minio_client):
        """Custom TTL is passed correctly."""
        storage_service.generate_download_url("exports/proj-1/file.pdf", ttl_hours=48)
        call_kwargs = mock_minio_client.presigned_get_object.call_args
        assert call_kwargs[1]["expires"] == timedelta(hours=48)

    def test_ttl_minimum_boundary(self, storage_service, mock_minio_client):
        """TTL of 1 hour (minimum) is accepted."""
        storage_service.generate_download_url("exports/proj-1/file.pdf", ttl_hours=1)
        call_kwargs = mock_minio_client.presigned_get_object.call_args
        assert call_kwargs[1]["expires"] == timedelta(hours=1)

    def test_ttl_maximum_boundary(self, storage_service, mock_minio_client):
        """TTL of 168 hours (maximum) is accepted."""
        storage_service.generate_download_url("exports/proj-1/file.pdf", ttl_hours=168)
        call_kwargs = mock_minio_client.presigned_get_object.call_args
        assert call_kwargs[1]["expires"] == timedelta(hours=168)

    def test_ttl_below_minimum_raises(self, storage_service):
        """TTL below 1 hour raises ValueError."""
        with pytest.raises(ValueError, match="ttl_hours must be between 1 and 168"):
            storage_service.generate_download_url("exports/proj-1/file.pdf", ttl_hours=0)

    def test_ttl_above_maximum_raises(self, storage_service):
        """TTL above 168 hours raises ValueError."""
        with pytest.raises(ValueError, match="ttl_hours must be between 1 and 168"):
            storage_service.generate_download_url("exports/proj-1/file.pdf", ttl_hours=169)

    def test_negative_ttl_raises(self, storage_service):
        """Negative TTL raises ValueError."""
        with pytest.raises(ValueError):
            storage_service.generate_download_url("exports/proj-1/file.pdf", ttl_hours=-1)


# =============================================================================
# Combined Upload + URL Generation Tests
# =============================================================================


class TestUploadAndGetUrl:
    """Tests for the upload_and_get_url method."""

    def test_returns_object_name_and_url(self, storage_service, mock_minio_client):
        """upload_and_get_url returns (object_name, download_url) tuple."""
        object_name, url = storage_service.upload_and_get_url(
            file_bytes=b"content",
            project_id="proj-1",
            filename="tor.pdf",
            content_type=CONTENT_TYPE_PDF,
        )
        assert object_name == "exports/proj-1/tor.pdf"
        assert "http://localhost:9000" in url

    def test_calls_both_put_and_presign(self, storage_service, mock_minio_client):
        """upload_and_get_url calls both put_object and presigned_get_object."""
        storage_service.upload_and_get_url(
            file_bytes=b"content",
            project_id="proj-1",
            filename="tor.pdf",
            content_type=CONTENT_TYPE_PDF,
        )
        mock_minio_client.put_object.assert_called_once()
        mock_minio_client.presigned_get_object.assert_called_once()

    def test_custom_ttl_in_combined_method(self, storage_service, mock_minio_client):
        """Custom TTL is respected in the combined method."""
        storage_service.upload_and_get_url(
            file_bytes=b"content",
            project_id="proj-1",
            filename="tor.pdf",
            content_type=CONTENT_TYPE_PDF,
            ttl_hours=72,
        )
        call_kwargs = mock_minio_client.presigned_get_object.call_args
        assert call_kwargs[1]["expires"] == timedelta(hours=72)


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests for module-level constants."""

    def test_default_ttl_is_24(self):
        assert DEFAULT_DOWNLOAD_TTL_HOURS == 24

    def test_min_ttl_is_1(self):
        assert MIN_TTL_HOURS == 1

    def test_max_ttl_is_168(self):
        assert MAX_TTL_HOURS == 168

    def test_content_type_docx(self):
        assert "openxmlformats" in CONTENT_TYPE_DOCX

    def test_content_type_pdf(self):
        assert CONTENT_TYPE_PDF == "application/pdf"
