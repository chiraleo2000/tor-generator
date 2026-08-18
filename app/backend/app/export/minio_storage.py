"""MinIO storage service for exported TOR documents.

Handles uploading generated DOCX and PDF files to MinIO object storage
and generating presigned (signed) download URLs with configurable TTL.

Requirements: 8.5
"""

import io
import logging
from datetime import timedelta
from typing import Optional

from minio import Minio

from app.config import get_settings

logger = logging.getLogger("tor_app.export.minio_storage")

# Default TTL for download URLs in hours
DEFAULT_DOWNLOAD_TTL_HOURS: int = 24

# Min/max TTL constraints (per requirement 8.5: 1–168 hours)
MIN_TTL_HOURS: int = 1
MAX_TTL_HOURS: int = 168

# Content types for exported files
CONTENT_TYPE_DOCX = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
CONTENT_TYPE_PDF = "application/pdf"


class MinIOStorageService:
    """Service for uploading export files to MinIO and generating signed download URLs.

    Usage:
        service = MinIOStorageService(minio_client)
        # Upload a file
        object_name = service.upload_file(
            file_bytes=pdf_bytes,
            project_id="abc-123",
            filename="tor_export.pdf",
            content_type="application/pdf",
        )
        # Generate download URL
        url = service.generate_download_url(object_name, ttl_hours=24)
    """

    def __init__(self, minio_client: Minio, bucket: Optional[str] = None) -> None:
        """Initialize the MinIO storage service.

        Args:
            minio_client: An initialized minio.Minio client instance.
            bucket: Bucket name to use. Defaults to settings.minio_bucket.
        """
        self._client = minio_client
        self._bucket = bucket or get_settings().minio_bucket

    def upload_file(
        self,
        file_bytes: bytes,
        project_id: str,
        filename: str,
        content_type: str,
    ) -> str:
        """Upload a file to MinIO object storage.

        Files are stored under the path: exports/{project_id}/{filename}

        Args:
            file_bytes: The file content as bytes.
            project_id: The project identifier (used as path prefix).
            filename: The filename to store (e.g. "tor_export.pdf").
            content_type: MIME type of the file.

        Returns:
            The full object name (path) in MinIO.

        Raises:
            Exception: If the upload to MinIO fails.
        """
        object_name = f"exports/{project_id}/{filename}"
        data = io.BytesIO(file_bytes)
        data_length = len(file_bytes)

        self._client.put_object(
            bucket_name=self._bucket,
            object_name=object_name,
            data=data,
            length=data_length,
            content_type=content_type,
        )

        logger.info(
            "Uploaded file to MinIO: bucket=%s, object=%s, size=%d bytes",
            self._bucket,
            object_name,
            data_length,
        )

        return object_name

    def generate_download_url(
        self,
        object_name: str,
        ttl_hours: int = DEFAULT_DOWNLOAD_TTL_HOURS,
    ) -> str:
        """Generate a presigned (signed) download URL for an object.

        Args:
            object_name: The full object path in MinIO.
            ttl_hours: URL validity duration in hours (1–168, default 24).

        Returns:
            A presigned URL string for downloading the object.

        Raises:
            ValueError: If ttl_hours is outside the allowed range (1–168).
            Exception: If URL generation fails.
        """
        # Validate TTL range
        if ttl_hours < MIN_TTL_HOURS or ttl_hours > MAX_TTL_HOURS:
            raise ValueError(
                f"ttl_hours must be between {MIN_TTL_HOURS} and {MAX_TTL_HOURS}, "
                f"got {ttl_hours}"
            )

        expiry = timedelta(hours=ttl_hours)

        url = self._client.presigned_get_object(
            bucket_name=self._bucket,
            object_name=object_name,
            expires=expiry,
        )

        logger.info(
            "Generated download URL: object=%s, ttl=%dh",
            object_name,
            ttl_hours,
        )

        return url

    def upload_docx(self, file_bytes: bytes, project_id: str, filename: str) -> str:
        """Upload a DOCX file to MinIO.

        Convenience method that sets the correct content type for DOCX files.

        Args:
            file_bytes: DOCX file content.
            project_id: Project identifier.
            filename: Filename (e.g. "tor_export.docx").

        Returns:
            Object name in MinIO.
        """
        return self.upload_file(
            file_bytes=file_bytes,
            project_id=project_id,
            filename=filename,
            content_type=CONTENT_TYPE_DOCX,
        )

    def upload_pdf(self, file_bytes: bytes, project_id: str, filename: str) -> str:
        """Upload a PDF file to MinIO.

        Convenience method that sets the correct content type for PDF files.

        Args:
            file_bytes: PDF file content.
            project_id: Project identifier.
            filename: Filename (e.g. "tor_export.pdf").

        Returns:
            Object name in MinIO.
        """
        return self.upload_file(
            file_bytes=file_bytes,
            project_id=project_id,
            filename=filename,
            content_type=CONTENT_TYPE_PDF,
        )

    def upload_and_get_url(
        self,
        file_bytes: bytes,
        project_id: str,
        filename: str,
        content_type: str,
        ttl_hours: int = DEFAULT_DOWNLOAD_TTL_HOURS,
    ) -> tuple[str, str]:
        """Upload a file and immediately generate a signed download URL.

        Combines upload_file and generate_download_url in a single call.

        Args:
            file_bytes: The file content.
            project_id: Project identifier.
            filename: Filename to store.
            content_type: MIME content type.
            ttl_hours: URL validity in hours (1–168, default 24).

        Returns:
            A tuple of (object_name, download_url).
        """
        object_name = self.upload_file(
            file_bytes=file_bytes,
            project_id=project_id,
            filename=filename,
            content_type=content_type,
        )
        download_url = self.generate_download_url(object_name, ttl_hours=ttl_hours)
        return object_name, download_url
