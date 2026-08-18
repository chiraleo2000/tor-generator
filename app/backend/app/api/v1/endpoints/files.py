"""File upload and text extraction API endpoints.

POST /files/upload — Multipart upload (max 20MB), store in MinIO, trigger text extraction/OCR.
GET /files/{id}/extracted-text — Return extracted text content.

Rate limited: 10 uploads per minute per user.
Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6
"""

import io
import logging
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import JSONResponse
from minio import Minio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.deps import get_current_user, get_db, get_minio
from app.domain.file_magic import ALLOWED_DOCUMENT_MIMES, require_allowed_upload
from app.exceptions import NotFoundError, ValidationError
from app.io_temp import unlink_path, write_temp_bytes
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.rate_limiter import rate_limit_upload
from app.schemas.files import ExtractedTextResponse, UploadedFileResponse
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.audit_service import AuditService, get_client_ip

logger = logging.getLogger("tor_app.files")

router = APIRouter()

# Maximum file size: 20 MB
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024

# Allowed MIME types for upload (documents + scanned images)
ALLOWED_MIME_TYPES = set(ALLOWED_DOCUMENT_MIMES) | {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
}

# Thread pool for synchronous text extraction (to not block the event loop)
_extraction_executor = ThreadPoolExecutor(max_workers=2)


@router.post(
    "/upload",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a file",
    description="Upload PDF, Word, or scanned images (max 20MB). Stored in MinIO.",
    dependencies=[Depends(rate_limit_upload)],
)
async def upload_file(
    request: Request,
    file: Annotated[UploadFile, File(..., description="PDF or DOCX file to upload (max 20MB)")],
    db: Annotated[AsyncSession, Depends(get_db)],
    minio_client: Annotated[Minio, Depends(get_minio)],
    current_user: Annotated[User, Depends(get_current_user)],
    project_id: Annotated[
        uuid.UUID | None, Form(description="Optional project ID to associate")
    ] = None,
) -> JSONResponse:
    """Upload a file to MinIO and trigger text extraction.

    Validates file size (max 20MB) and MIME type (PDF/DOCX only).
    Stores the file in MinIO with a UUID-based path.
    Triggers synchronous text extraction with OCR fallback for scanned PDFs.
    OCR timeout: 30s with partial result return.

    Args:
        request: The incoming HTTP request.
        file: Uploaded file (multipart).
        project_id: Optional project ID to link the file to.
        db: Async database session.
        minio_client: MinIO client for object storage.
        current_user: Authenticated user.

    Returns:
        SuccessResponse with UploadedFileResponse data.

    Raises:
        ValidationError: If file size exceeds 20MB or MIME type is not supported.
    """
    # Read file content and validate size + magic bytes
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            message=f"ขนาดไฟล์เกินกำหนด สูงสุด {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
            field="file",
            details={
                "max_size_bytes": MAX_FILE_SIZE_BYTES,
                "received_size_bytes": file_size,
            },
        )

    if file_size == 0:
        raise ValidationError(
            message="ไฟล์ว่างเปล่า กรุณาอัปโหลดไฟล์ที่มีเนื้อหา",
            field="file",
        )

    try:
        content_type = require_allowed_upload(file_content, file.content_type or "")
    except ValueError as exc:
        raise ValidationError(
            message=str(exc),
            field="file",
            details={
                "allowed_types": list(ALLOWED_MIME_TYPES),
                "received_type": file.content_type,
            },
        ) from exc

    # Generate storage path: uploads/{uuid}{ext} — never use the original filename
    file_id = uuid.uuid4()
    original_name = file.filename or "unnamed_file"
    mime_ext = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "application/msword": ".doc",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    storage_path = f"uploads/{file_id}{mime_ext.get(content_type, '')}"

    # Upload to MinIO
    settings = get_settings()
    try:
        minio_client.put_object(
            settings.minio_bucket,
            storage_path,
            io.BytesIO(file_content),
            length=file_size,
            content_type=content_type,
        )
        logger.info(
            "File uploaded to MinIO: %s (size=%d, user=%s)",
            storage_path,
            file_size,
            current_user.id,
        )
    except Exception as exc:
        logger.exception("MinIO upload failed for %s", original_name)
        raise ValidationError(
            message="การอัปโหลดไฟล์ล้มเหลว กรุณาลองใหม่อีกครั้ง",
            field="file",
            details=str(exc),
        )

    # Create database record
    uploaded_file = UploadedFile(
        id=file_id,
        project_id=project_id,
        uploaded_by=current_user.id,
        original_name=original_name,
        storage_path=storage_path,
        mime_type=content_type,
        file_size_bytes=file_size,
        ocr_status="pending",
    )
    db.add(uploaded_file)
    await db.flush()  # Flush to get the ID persisted before extraction
    await AuditService.log(
        db,
        action="create",
        resource_type="uploaded_file",
        user_id=current_user.id,
        resource_id=uploaded_file.id,
        ip_address=get_client_ip(request),
        details={"event": "file_upload", "mime": content_type},
    )

    # Trigger text extraction (sync operation run in thread pool)
    extracted_text, ocr_status, extract_warnings = await _extract_text_from_content(
        file_content, content_type, original_name
    )
    for warning in extract_warnings:
        logger.warning("Extraction warning (%s): %s", original_name, warning)

    # Update file record with extraction results
    uploaded_file.extracted_text = extracted_text
    uploaded_file.ocr_status = ocr_status

    # Build response
    response_data = UploadedFileResponse(
        id=uploaded_file.id,
        project_id=uploaded_file.project_id,
        original_name=uploaded_file.original_name,
        mime_type=uploaded_file.mime_type,
        file_size_bytes=uploaded_file.file_size_bytes,
        ocr_status=uploaded_file.ocr_status,
        uploaded_at=uploaded_file.uploaded_at or datetime.now(timezone.utc),
    )

    meta = MetaInfo(
        request_id=getattr(request.state, "request_id", "unknown"),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=SuccessResponse(
            ok=True,
            data=response_data.model_dump(mode="json"),
            meta=meta,
        ).model_dump(mode="json"),
    )


@router.get(
    "/{file_id}/extracted-text",
    response_model=SuccessResponse,
    summary="Get extracted text",
    description="Return the extracted text content for an uploaded file.",
)
async def get_extracted_text(
    request: Request,
    file_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Get the extracted text content for a previously uploaded file.

    Only the file owner can access the extracted text.

    Args:
        request: The incoming HTTP request.
        file_id: UUID of the uploaded file.
        db: Async database session.
        current_user: Authenticated user.

    Returns:
        SuccessResponse with ExtractedTextResponse data.

    Raises:
        NotFoundError: If the file doesn't exist or user doesn't own it.
    """
    stmt = select(UploadedFile).where(
        UploadedFile.id == file_id,
        UploadedFile.uploaded_by == current_user.id,
    )
    result = await db.execute(stmt)
    uploaded_file = result.scalar_one_or_none()

    if uploaded_file is None:
        raise NotFoundError(
            message="ไม่พบไฟล์ที่ต้องการ",
            details={"file_id": str(file_id)},
        )

    # Build warnings list based on OCR status
    warnings: list[str] = []
    if uploaded_file.ocr_status == "timeout":
        warnings.append("การประมวลผล OCR หมดเวลา อาจได้ผลลัพธ์เพียงบางส่วน")
    elif uploaded_file.ocr_status == "failed":
        warnings.append("การดึงข้อความล้มเหลว กรุณาอัปโหลดไฟล์ใหม่หรือกรอกข้อความด้วยตนเอง")
    elif uploaded_file.ocr_status == "pending":
        warnings.append("กำลังประมวลผลไฟล์ กรุณารอสักครู่")

    response_data = ExtractedTextResponse(
        id=uploaded_file.id,
        original_name=uploaded_file.original_name,
        extracted_text=uploaded_file.extracted_text,
        ocr_status=uploaded_file.ocr_status,
        warnings=warnings,
    )

    meta = MetaInfo(
        request_id=getattr(request.state, "request_id", "unknown"),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=SuccessResponse(
            ok=True,
            data=response_data.model_dump(mode="json"),
            meta=meta,
        ).model_dump(mode="json"),
    )


async def _extract_text_from_content(
    file_content: bytes,
    mime_type: str,
    filename: str,
) -> tuple[str | None, str, list[str]]:
    """Extract text from file content using the RAG extraction module.

    Writes content to a temp file, runs extraction (which may invoke OCR),
    and returns the results. OCR timeout is 30s with partial result return.

    Args:
        file_content: Raw file bytes.
        mime_type: MIME type of the file.
        filename: Original filename (for extension detection).

    Returns:
        Tuple of (extracted_text, ocr_status, warnings).
        - extracted_text: The extracted text or None on failure.
        - ocr_status: One of "completed", "failed", "timeout".
        - warnings: List of warning messages.
    """
    import asyncio

    try:
        # Write to temp file for extraction (extraction module works with file paths)
        suffix = Path(filename).suffix or ".pdf"
        tmp_path = await write_temp_bytes(file_content, suffix)

        try:
            # Run synchronous extraction in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            from app.rag.extraction import extract_text as _extract

            result = await loop.run_in_executor(
                _extraction_executor,
                _extract,
                tmp_path,
                mime_type,
            )

            extracted_text = result.text if result.text else None
            warnings = result.warnings

            # Determine status based on extraction result
            if result.warnings and any("timed out" in w.lower() for w in result.warnings):
                ocr_status = "timeout"
            elif extracted_text:
                ocr_status = "completed"
            else:
                ocr_status = "failed"

            return extracted_text, ocr_status, warnings

        finally:
            await unlink_path(tmp_path)

    except subprocess.TimeoutExpired:
        logger.warning("Text extraction timed out for file: %s", filename)
        return None, "timeout", ["การประมวลผลหมดเวลา"]
    except Exception as exc:
        logger.exception("Text extraction failed for %s", filename)
        return None, "failed", [f"การดึงข้อความล้มเหลว: {type(exc).__name__}"]
