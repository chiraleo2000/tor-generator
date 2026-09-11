"""Export service for TOR document generation with retry logic.

Orchestrates DOCX and PDF generation, uploads to MinIO, and provides
signed download URLs. Implements retry-once-with-30s-delay on failure
and must complete within 120s total.

Requirements: 8.5, 8.6, 8.7, 8.8
"""

import asyncio
import io
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from minio import Minio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import get_settings
from app.domain.section_profile import STORAGE_TO_SEMANTIC
from app.domain.section_text import section_plain_text
from app.export.docx_generator import DOCXGenerator, TORContent
from app.export.quality_gate import check_export_gates
from app.export.render_plan import AppendixItem, coerce_numbering_scheme
from app.models.project import Project
from app.models.tor_section import TORSection
from app.schemas.export import (
    ExportDownloadResponse,
    ExportFileInfo,
    ExportJobResponse,
    ExportStatus,
)

logger = logging.getLogger("tor_app.export_service")

# Maximum time for the entire export operation
EXPORT_TIMEOUT_SECONDS = 120

# Delay before retry on failure
RETRY_DELAY_SECONDS = 30

# Maximum retry count (retry once)
MAX_RETRIES = 1


def _appendix_pairs(raw: object) -> tuple[tuple[str, str], ...]:
    if not isinstance(raw, list):
        return ()
    pairs: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "")
        body = str(item.get("content") or "")
        if title.strip() or body.strip():
            pairs.append((title, body))
    return tuple(pairs)


@dataclass(frozen=True)
class ProjectExportSnapshot:
    """Scalar project fields copied before the request session closes."""

    id: uuid.UUID
    name: str
    ministry: str
    budget: int
    project_type: str
    appendices: tuple[tuple[str, str], ...] = ()
    phase4_confirmed: bool = False

    @classmethod
    def from_project(cls, project: Project) -> "ProjectExportSnapshot":
        analysis = getattr(project, "analysis_json", None) or {}
        extracted = getattr(project, "extracted_fields", None) or {}
        appendices = _appendix_pairs(analysis.get("appendices")) or _appendix_pairs(
            extracted.get("appendices")
        )
        return cls(
            id=project.id,
            name=project.name or "",
            ministry=project.ministry or "",
            budget=int(project.budget or 0),
            project_type=project.project_type or "general",
            appendices=appendices,
            phase4_confirmed=bool(analysis.get("phase4_confirmed")),
        )


class ExportJob:
    """In-memory representation of an export job.

    In a production system this would be persisted to the database
    or Redis for multi-worker coordination. For this implementation,
    jobs are stored in an in-memory dict keyed by export_id.
    """

    def __init__(
        self,
        export_id: uuid.UUID,
        project_id: uuid.UUID,
        use_thai_numerals: bool = True,
        url_ttl_hours: int = 24,
        numbering_scheme: str = "none",
    ) -> None:
        self.export_id = export_id
        self.project_id = project_id
        self.status: ExportStatus = "pending"
        self.use_thai_numerals = use_thai_numerals
        self.url_ttl_hours = url_ttl_hours
        self.numbering_scheme = numbering_scheme
        self.files: list[ExportFileInfo] = []
        self.started_at: datetime = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.retry_count: int = 0
        self.task: asyncio.Task[None] | None = None

    def to_response(self) -> ExportJobResponse:
        """Convert to response schema."""
        return ExportJobResponse(
            export_id=self.export_id,
            project_id=self.project_id,
            status=self.status,
            files=self.files,
            started_at=self.started_at,
            completed_at=self.completed_at,
            error_message=self.error_message,
            retry_count=self.retry_count,
        )


class ExportService:
    """Service for managing TOR document export operations.

    Handles:
    - DOCX + PDF generation from project TOR content
    - Upload to MinIO with organized paths
    - Signed download URL generation
    - Retry logic (once with 30s delay on failure)
    - 120s total timeout constraint
    """

    # In-memory store for export jobs (project_id → latest job)
    _jobs: dict[uuid.UUID, ExportJob] = {}
    # Also index by export_id for status lookups
    _jobs_by_id: dict[uuid.UUID, ExportJob] = {}

    @classmethod
    def get_job_for_project(cls, project_id: uuid.UUID) -> Optional[ExportJob]:
        """Get the latest export job for a project."""
        return cls._jobs.get(project_id)

    @classmethod
    def get_job_by_id(cls, export_id: uuid.UUID) -> Optional[ExportJob]:
        """Get an export job by its unique identifier."""
        return cls._jobs_by_id.get(export_id)

    @classmethod
    async def trigger_export(
        cls,
        db: AsyncSession,
        minio_client: Minio,
        project: Project,
        use_thai_numerals: bool = True,
        url_ttl_hours: int = 24,
        numbering_scheme: str = "none",
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> ExportJob:
        """Trigger document export for a project.

        Creates an export job, runs generation in background with retry logic.
        If there's already a running export for this project, returns that job.

        Args:
            db: Request-scoped session (used only when session_factory is None).
            minio_client: MinIO client for file storage.
            project: The project to export.
            use_thai_numerals: Whether to use Thai numerals in the document.
            url_ttl_hours: Download URL validity in hours (1-168).
            numbering_scheme: Heading numbering mode (default titles only).
            session_factory: Opens a dedicated session for the background job.

        Returns:
            The ExportJob tracking the generation.
        """
        # Check if there's already a running export for this project
        existing = cls._jobs.get(project.id)
        if existing and existing.status in ("pending", "generating"):
            return existing

        snapshot = ProjectExportSnapshot.from_project(project)

        # Create a new export job
        export_id = uuid.uuid4()
        job = ExportJob(
            export_id=export_id,
            project_id=snapshot.id,
            use_thai_numerals=use_thai_numerals,
            url_ttl_hours=url_ttl_hours,
            numbering_scheme=numbering_scheme,
        )
        cls._jobs[snapshot.id] = job
        cls._jobs_by_id[export_id] = job

        # Run generation in background (fire-and-forget with timeout)
        export_task = asyncio.create_task(
            cls._run_export_with_retry(
                db, minio_client, snapshot, job, session_factory
            )
        )
        job.task = export_task

        return job

    @classmethod
    async def _run_export_with_retry(
        cls,
        db: AsyncSession,
        minio_client: Minio,
        project: ProjectExportSnapshot,
        job: ExportJob,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        """Run the export with retry-once logic and 120s timeout.

        If the first attempt fails, waits 30s then retries once.
        Total operation must complete within 120s.
        Uses a dedicated session when session_factory is provided so the
        request session is not shared after the HTTP handler returns.
        """
        try:
            if session_factory is not None:
                async with session_factory() as bg_db:
                    try:
                        await asyncio.wait_for(
                            cls._attempt_export_with_retry(
                                bg_db, minio_client, project, job
                            ),
                            timeout=EXPORT_TIMEOUT_SECONDS,
                        )
                        await bg_db.commit()
                    except Exception:
                        await bg_db.rollback()
                        raise
            else:
                await asyncio.wait_for(
                    cls._attempt_export_with_retry(db, minio_client, project, job),
                    timeout=EXPORT_TIMEOUT_SECONDS,
                )
        except asyncio.TimeoutError:
            job.status = "failed"
            job.error_message = "การสร้างเอกสารใช้เวลาเกิน 120 วินาที กรุณาลองใหม่อีกครั้ง"
            job.completed_at = datetime.now(timezone.utc)
            logger.exception(
                "Export timed out for project %s (export_id=%s)",
                project.id,
                job.export_id,
            )
        except Exception as exc:
            job.status = "failed"
            job.error_message = f"เกิดข้อผิดพลาดในการสร้างเอกสาร: {str(exc)}"
            job.completed_at = datetime.now(timezone.utc)
            logger.exception(
                "Unexpected error in export for project %s: %s",
                project.id,
                exc,
            )

    @classmethod
    async def _attempt_export_with_retry(
        cls,
        db: AsyncSession,
        minio_client: Minio,
        project: ProjectExportSnapshot,
        job: ExportJob,
    ) -> None:
        """Attempt export generation. On failure, retry once after 30s delay."""
        job.status = "generating"

        # First attempt
        try:
            await cls._generate_and_upload(db, minio_client, project, job)
            return  # Success on first attempt
        except ValueError as exc:
            # Quality-gate / validation failures will not succeed on retry.
            job.status = "failed"
            job.error_message = str(exc)
            job.completed_at = datetime.now(timezone.utc)
            logger.warning(
                "Export blocked by validation for project %s: %s",
                project.id,
                exc,
            )
            return
        except Exception as exc:
            logger.warning(
                "Export first attempt failed for project %s: %s. Retrying in %ds...",
                project.id,
                exc,
                RETRY_DELAY_SECONDS,
            )

        # Wait 30s before retry
        await asyncio.sleep(RETRY_DELAY_SECONDS)
        job.retry_count = 1

        # Second attempt (retry once)
        try:
            await cls._generate_and_upload(db, minio_client, project, job)
        except Exception as exc:
            job.status = "failed"
            job.error_message = (
                f"การสร้างเอกสารล้มเหลวหลังลองใหม่ 1 ครั้ง: {str(exc)}"
            )
            job.completed_at = datetime.now(timezone.utc)
            logger.exception(
                "Export failed after retry for project %s",
                project.id,
            )
            raise

    @classmethod
    async def _generate_and_upload(
        cls,
        db: AsyncSession,
        minio_client: Minio,
        project: ProjectExportSnapshot,
        job: ExportJob,
    ) -> None:
        """Generate DOCX + PDF and upload both to MinIO.

        On success, updates the job with file info and signed URLs.
        """
        settings = get_settings()

        # Build TOR content from project sections
        tor_content, approvals = await cls._build_tor_content(
            db, project, job.use_thai_numerals, job.numbering_scheme
        )
        if project.phase4_confirmed:
            # Re-apply HITL attest for projects confirmed before the storage/semantic fix.
            from app.services.intake_service import hitl_storage_keys

            for key in hitl_storage_keys():
                approvals[key] = True
                semantic = STORAGE_TO_SEMANTIC.get(key)
                if semantic:
                    approvals[semantic] = True
            stmt = select(TORSection).where(
                TORSection.project_id == project.id,
                TORSection.sub_key.is_(None),
            )
            rows = (await db.execute(stmt)).scalars().all()
            from app.services.intake_service import attest_hitl_sections

            attest_hitl_sections(list(rows))
        check_export_gates(
            tor_content,
            approvals,
            officer_attested=project.phase4_confirmed,
        ).raise_if_blocked()

        # Generate DOCX
        docx_generator = DOCXGenerator()
        docx_bytes = await asyncio.to_thread(docx_generator.generate, tor_content)

        # Generate PDF (import dynamically - may not be available yet if task 12.2 is in progress)
        pdf_bytes = await cls._generate_pdf(tor_content)

        # Upload to MinIO
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        base_path = f"exports/{project.id}/{timestamp}"

        docx_path = f"{base_path}/tor_document.docx"
        pdf_path = f"{base_path}/tor_document.pdf"

        # Upload DOCX
        await asyncio.to_thread(
            cls._upload_to_minio,
            minio_client,
            settings.minio_bucket,
            docx_path,
            docx_bytes,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        # Upload PDF
        await asyncio.to_thread(
            cls._upload_to_minio,
            minio_client,
            settings.minio_bucket,
            pdf_path,
            pdf_bytes,
            "application/pdf",
        )

        # Generate signed download URLs
        ttl = timedelta(hours=job.url_ttl_hours)
        docx_url = cls._get_presigned_url(minio_client, settings.minio_bucket, docx_path, ttl)
        pdf_url = cls._get_presigned_url(minio_client, settings.minio_bucket, pdf_path, ttl)

        # Update job with results
        job.files = [
            ExportFileInfo(
                format="docx",
                storage_path=docx_path,
                download_url=docx_url,
                file_size_bytes=len(docx_bytes),
            ),
            ExportFileInfo(
                format="pdf",
                storage_path=pdf_path,
                download_url=pdf_url,
                file_size_bytes=len(pdf_bytes),
            ),
        ]
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)

        logger.info(
            "Export completed for project %s (export_id=%s, docx=%d bytes, pdf=%d bytes)",
            project.id,
            job.export_id,
            len(docx_bytes),
            len(pdf_bytes),
        )

    @classmethod
    async def _build_tor_content(
        cls,
        db: AsyncSession,
        project: ProjectExportSnapshot,
        use_thai_numerals: bool,
        numbering_scheme: str = "none",
    ) -> tuple[TORContent, dict[str, bool]]:
        """Build TORContent from the project's TOR sections in the database."""
        stmt = select(TORSection).where(TORSection.project_id == project.id)
        result = await db.execute(stmt)
        sections = result.scalars().all()

        section_contents: dict[str, str] = {}
        sub_section_contents: dict[str, dict[str, str]] = {}
        approvals: dict[str, bool] = {}
        appendix_items = [
            AppendixItem(title=title, content=body) for title, body in project.appendices
        ]

        for section in sections:
            cls._ingest_export_section(
                section,
                section_contents,
                sub_section_contents,
                approvals,
                appendix_items,
            )

        content = TORContent(
            project_name=project.name,
            ministry=project.ministry,
            budget=project.budget,
            project_type=project.project_type,
            sections=section_contents,
            sub_sections=sub_section_contents,
            use_thai_numerals=use_thai_numerals,
            numbering_scheme=coerce_numbering_scheme(numbering_scheme),
            appendices=appendix_items,
        )
        return content, approvals

    @staticmethod
    def _ingest_export_section(
        section: TORSection,
        section_contents: dict[str, str],
        sub_section_contents: dict[str, dict[str, str]],
        approvals: dict[str, bool],
        appendix_items: list[AppendixItem],
    ) -> None:
        key = section.section_key or ""
        if key in {"appendix", "appendices"}:
            appendix_items.append(
                AppendixItem(title=section.sub_key or "", content=section.content or "")
            )
            return
        if section.sub_key:
            bucket = sub_section_contents.setdefault(key, {})
            bucket[section.sub_key] = section.content or ""
            return
        section_contents[key] = section_plain_text(section.content, key)
        approved = bool(getattr(section, "is_approved", False))
        approvals[key] = approved
        approvals[STORAGE_TO_SEMANTIC.get(key, key)] = approved

    @classmethod
    async def _generate_pdf(cls, tor_content: TORContent) -> bytes:
        """Generate PDF from TOR content.

        Attempts to use the PDF generator if available (task 12.2).
        Falls back to a minimal PDF placeholder if not yet implemented.
        """
        try:
            from app.export.pdf_generator import PDFGenerator
            pdf_generator = PDFGenerator()
            return await asyncio.to_thread(pdf_generator.generate, tor_content)
        except ImportError:
            # PDF generator not yet available (task 12.2 in progress)
            # Generate a minimal placeholder PDF
            logger.warning(
                "PDF generator not available, generating placeholder PDF"
            )
            return cls._generate_placeholder_pdf(tor_content)

    @classmethod
    def _generate_placeholder_pdf(cls, _tor_content: TORContent) -> bytes:
        """Generate a minimal placeholder PDF when WeasyPrint is not available.

        This is a fallback for when task 12.2 (PDF generator) is not yet complete.
        """
        # Minimal valid PDF (static placeholder — no interpolation)
        content = """%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj

2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj

3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << >> >>
endobj

4 0 obj
<< /Length 44 >>
stream
BT /F1 12 Tf 100 700 Td (TOR Export) Tj ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000230 00000 n 

trailer
<< /Size 5 /Root 1 0 R >>
startxref
324
%%EOF"""
        return content.encode("latin-1")

    @classmethod
    def _upload_to_minio(
        cls,
        minio_client: Minio,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str,
    ) -> None:
        """Upload bytes to MinIO. Runs in a thread pool."""
        buffer = io.BytesIO(data)
        minio_client.put_object(
            bucket,
            object_name,
            buffer,
            length=len(data),
            content_type=content_type,
        )

    @classmethod
    def _get_presigned_url(
        cls,
        minio_client: Minio,
        bucket: str,
        object_name: str,
        ttl: timedelta,
    ) -> str:
        """Generate a presigned URL for downloading an object from MinIO."""
        return minio_client.presigned_get_object(
            bucket,
            object_name,
            expires=ttl,
        )

    @classmethod
    def get_download_url(
        cls,
        minio_client: Minio,
        project_id: uuid.UUID,
        format: str,
        ttl_hours: int = 24,
    ) -> Optional[ExportDownloadResponse]:
        """Get a fresh signed download URL for an exported file.

        Looks up the latest completed export for the project and generates
        a new signed URL for the requested format.

        Args:
            minio_client: MinIO client.
            project_id: The project ID.
            format: "docx" or "pdf".
            ttl_hours: URL validity in hours.

        Returns:
            ExportDownloadResponse with the signed URL, or None if no export exists.
        """
        job = cls._jobs.get(project_id)
        if job is None or job.status != "completed":
            return None

        # Find the file for the requested format
        file_info = next((f for f in job.files if f.format == format), None)
        if file_info is None:
            return None

        settings = get_settings()
        ttl = timedelta(hours=ttl_hours)

        # Generate a fresh signed URL
        url = cls._get_presigned_url(
            minio_client, settings.minio_bucket, file_info.storage_path, ttl
        )

        return ExportDownloadResponse(
            download_url=url,
            format=format,  # type: ignore[arg-type]
            expires_in_seconds=int(ttl.total_seconds()),
        )

    @classmethod
    def get_file_object(cls, minio_client: Minio, project_id: uuid.UUID, format: str):
        """Return (MinIO object, storage_path) for an authenticated stream download."""
        job = cls._jobs.get(project_id)
        if job is None or job.status != "completed":
            return None, None
        file_info = next((f for f in job.files if f.format == format), None)
        if file_info is None:
            return None, None
        settings = get_settings()
        obj = minio_client.get_object(settings.minio_bucket, file_info.storage_path)
        return obj, file_info.storage_path

    @classmethod
    def clear_project_export(cls, project_id: uuid.UUID) -> None:
        """Clear export cache for a project (used when content is updated for re-export)."""
        job = cls._jobs.pop(project_id, None)
        if job:
            cls._jobs_by_id.pop(job.export_id, None)
