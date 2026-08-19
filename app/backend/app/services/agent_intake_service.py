"""Bulk document ingestion for the agent TOR workflow."""

from __future__ import annotations

import asyncio
import io
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.io_temp import unlink_path, write_temp_bytes
from app.models.uploaded_file import UploadedFile
from app.rag.extraction import extract_text
from app.services.session_cache import SessionCacheService, content_hash

logger = logging.getLogger("tor_app.agent_intake")

MAX_FILES_PER_REQUEST = 20
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
MAX_CONTENT_CHARS = 200_000
INGESTION_TIMEOUT = 600
MIME_PDF = "application/pdf"
MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
MIME_PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
MIME_TXT = "text/plain"
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt"}
EXT_TO_MIME = {
    ".pdf": MIME_PDF,
    ".docx": MIME_DOCX,
    ".pptx": MIME_PPTX,
    ".txt": MIME_TXT,
}


class BatchTooLargeError(ValueError):
    """Raised when more than MAX_FILES_PER_REQUEST files are submitted."""


@dataclass
class FileStatus:
    name: str
    size: int
    content_hash: str
    status: str
    chars: int = 0
    error: str | None = None
    text: str = ""


@dataclass
class IngestionResult:
    project_id: UUID
    files: list[FileStatus] = field(default_factory=list)
    texts: list[dict[str, str]] = field(default_factory=list)
    total_chars: int = 0
    concatenated: str = ""
    timed_out: bool = False


def guess_mime(filename: str, claimed: str | None) -> str | None:
    suffix = Path(filename or "").suffix.lower()
    if suffix in EXT_TO_MIME:
        return EXT_TO_MIME[suffix]
    claimed_l = (claimed or "").lower()
    if claimed_l in EXT_TO_MIME.values() or claimed_l.startswith("text/"):
        return claimed_l
    return None


def validate_file_count(count: int) -> None:
    if count > MAX_FILES_PER_REQUEST:
        raise BatchTooLargeError(
            f"รับได้สูงสุด {MAX_FILES_PER_REQUEST} ไฟล์ต่อครั้ง (ได้รับ {count})"
        )


class IntakeIngestionService:
    """Extract and store bulk intake documents for an agent session."""

    def __init__(
        self,
        cache: SessionCacheService | None = None,
        storage: Any | None = None,
    ) -> None:
        self._cache = cache or SessionCacheService()
        self._storage = storage

    async def process_batch(
        self,
        project_id: UUID,
        files: list[Any],
        free_text: str | None,
        storage_backend: str = "minio",
        db: AsyncSession | None = None,
        uploaded_by: UUID | None = None,
        minio_client: Any | None = None,
    ) -> IngestionResult:
        file_list = list(files or [])
        validate_file_count(len(file_list))
        deadline = time.monotonic() + INGESTION_TIMEOUT
        result = IngestionResult(project_id=project_id)
        remaining = MAX_CONTENT_CHARS

        for upload in file_list:
            if time.monotonic() >= deadline:
                result.timed_out = True
                result.files.append(
                    FileStatus(
                        name=getattr(upload, "filename", None) or "unnamed",
                        size=0,
                        content_hash="",
                        status="error",
                        error="ingestion_timeout",
                    )
                )
                continue
            status = await self._process_one(
                project_id,
                upload,
                storage_backend,
                db,
                uploaded_by,
                minio_client or self._storage,
            )
            result.files.append(status)
            if status.status != "ok" or not status.text:
                continue
            chunk = status.text[:remaining]
            if chunk:
                result.texts.append({"name": status.name, "text": chunk})
                remaining -= len(chunk)
                result.total_chars += len(chunk)

        if free_text and remaining > 0:
            text = free_text.strip()[:remaining]
            if text:
                result.texts.append({"name": "ข้อความผู้ใช้.txt", "text": text})
                result.total_chars += len(text)

        parts: list[str] = []
        for item in result.texts:
            parts.append(f"=== {item['name']} ===\n{item['text']}")
        result.concatenated = "\n\n".join(parts)
        return result

    async def _process_one(
        self,
        project_id: UUID,
        upload: Any,
        storage_backend: str,
        db: AsyncSession | None,
        uploaded_by: UUID | None,
        minio_client: Any | None,
    ) -> FileStatus:
        name = getattr(upload, "filename", None) or "unnamed"
        content: bytes
        if hasattr(upload, "read"):
            raw = upload.read()
            content = await raw if asyncio.iscoroutine(raw) else raw
        else:
            content = b""
        if not isinstance(content, (bytes, bytearray)):
            content = bytes(content or b"")
        size = len(content)
        if size > MAX_FILE_SIZE_BYTES:
            return FileStatus(
                name=name,
                size=size,
                content_hash="",
                status="error",
                error="file_too_large",
            )
        mime = guess_mime(name, getattr(upload, "content_type", None))
        if mime is None:
            return FileStatus(
                name=name,
                size=size,
                content_hash="",
                status="error",
                error="unsupported_format",
            )
        digest = content_hash(bytes(content))
        cached = await self._cache.get_extraction(project_id, digest)
        if isinstance(cached, dict) and cached.get("text") is not None:
            return FileStatus(
                name=name,
                size=size,
                content_hash=digest,
                status="ok",
                chars=len(str(cached.get("text") or "")),
                text=str(cached.get("text") or ""),
            )
        try:
            text = await self._extract_bytes(content, mime, name)
        except Exception as exc:
            logger.warning("Extraction failed for %s: %s", name, exc)
            return FileStatus(
                name=name,
                size=size,
                content_hash=digest,
                status="error",
                error="extraction_failed",
            )
        await self._store_raw(
            project_id, name, content, mime, storage_backend, minio_client
        )
        if db is not None and uploaded_by is not None:
            db.add(
                UploadedFile(
                    project_id=project_id,
                    uploaded_by=uploaded_by,
                    original_name=name,
                    storage_path=f"agent/{project_id}/{digest}",
                    mime_type=mime,
                    file_size_bytes=size,
                    extracted_text=text[:20000] if text else None,
                    ocr_status="completed",
                )
            )
        await self._cache.set_extraction(
            project_id, digest, {"text": text, "name": name, "chars": len(text)}
        )
        return FileStatus(
            name=name,
            size=size,
            content_hash=digest,
            status="ok",
            chars=len(text),
            text=text,
        )

    async def _extract_bytes(self, content: bytes, mime: str, name: str) -> str:
        suffix = Path(name).suffix or ".bin"
        tmp = await write_temp_bytes(content, suffix)
        try:
            result = await asyncio.to_thread(extract_text, tmp, mime)
            return result.text or ""
        finally:
            await unlink_path(tmp)

    async def _store_raw(
        self,
        project_id: UUID,
        name: str,
        content: bytes,
        mime: str,
        storage_backend: str,
        minio_client: Any | None,
    ) -> None:
        object_name = f"agent/{project_id}/{uuid4()}{Path(name).suffix}"
        if storage_backend == "local" or minio_client is None:
            settings = get_settings()
            root = settings.agent_local_storage_dir or str(
                Path.cwd() / "agent-uploads"
            )
            path = Path(root) / object_name
            path.parent.mkdir(parents=True, exist_ok=True)
            await asyncio.to_thread(path.write_bytes, content)
            return
        settings = get_settings()
        try:
            minio_client.put_object(
                settings.minio_bucket,
                object_name,
                io.BytesIO(content),
                length=len(content),
                content_type=mime,
            )
        except Exception as exc:
            logger.warning("MinIO store failed for %s: %s", name, exc)
