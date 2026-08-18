"""Export API endpoints.

POST /projects/{id}/export — Trigger DOCX + PDF generation, return download URLs.
GET /projects/{id}/export/status — Check export generation progress.
GET /projects/{id}/export/download/{format} — Authenticated stream of the exported file.

Implements:
- Retry once with 30s delay on failure
- Complete within 120s total
- Support re-export when content updated
- Download endpoint redirects to signed MinIO URL

Requirements: 8.5, 8.6, 8.7, 8.8
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from minio import Minio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.constants import PROJECT_NOT_FOUND
from app.deps import get_current_user, get_db, get_minio
from app.models.project import Project
from app.models.user import User
from app.schemas.export import ExportRequest
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.export_service import ExportService

logger = logging.getLogger("tor_app.export")

router = APIRouter()


async def _get_project_for_user(
    project_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Project:
    """Fetch a project and verify ownership/access."""
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PROJECT_NOT_FOUND,
        )

    # Check ownership (officers can only export their own projects)
    if current_user.role == "officer" and project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="คุณไม่มีสิทธิ์เข้าถึงโครงการนี้",
        )

    return project


@router.post(
    "/{project_id}/export",
    response_model=SuccessResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger TOR document export",
    description=(
        "Generate DOCX and PDF files for the project's TOR. "
        "Returns immediately with an export job ID. "
        "Generation runs in the background with retry-once on failure."
    ),
)
async def trigger_export(
    request: Request,
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    minio_client: Annotated[Minio, Depends(get_minio)],
    body: ExportRequest = ExportRequest(),
) -> JSONResponse:
    """Trigger export of TOR documents (DOCX + PDF).

    Clears any previous export for re-export support.
    Starts background generation with retry logic.
    """
    project = await _get_project_for_user(project_id, current_user, db)

    # Clear previous export to support re-export
    ExportService.clear_project_export(project.id)

    # Trigger export
    job = await ExportService.trigger_export(
        db=db,
        minio_client=minio_client,
        project=project,
        use_thai_numerals=body.use_thai_numerals,
        url_ttl_hours=body.url_ttl_hours,
        session_factory=getattr(request.app.state, "db_session_factory", None),
    )

    request_id = getattr(request.state, "request_id", "unknown")
    response = SuccessResponse(
        ok=True,
        data=job.to_response().model_dump(mode="json"),
        meta=MetaInfo(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )

    logger.info(
        "Export triggered for project %s by user %s (export_id=%s)",
        project_id,
        current_user.id,
        job.export_id,
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=response.model_dump(mode="json"),
    )


@router.get(
    "/{project_id}/export/status",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Check export generation status",
    description="Get the current status of the most recent export job for a project.",
)
async def get_export_status(
    request: Request,
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """Get the current export status for a project."""
    # Verify project access
    await _get_project_for_user(project_id, current_user, db)

    # Get the latest export job
    job = ExportService.get_job_for_project(project_id)

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบการส่งออกเอกสารสำหรับโครงการนี้",
        )

    request_id = getattr(request.state, "request_id", "unknown")
    response = SuccessResponse(
        ok=True,
        data=job.to_response().model_dump(mode="json"),
        meta=MetaInfo(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response.model_dump(mode="json"),
    )


@router.get(
    "/{project_id}/export/download/{format}",
    summary="Download exported file",
    description=(
        "Stream the exported file through the API so the browser can download "
        "with the user's JWT. Format must be 'docx' or 'pdf'."
    ),
)
async def download_export(
    request: Request,
    project_id: uuid.UUID,
    format: Literal["docx", "pdf"],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    minio_client: Annotated[Minio, Depends(get_minio)],
) -> StreamingResponse:
    """Stream the exported file with the caller's Authorization header."""
    await _get_project_for_user(project_id, current_user, db)

    obj, storage_path = ExportService.get_file_object(
        minio_client=minio_client,
        project_id=project_id,
        format=format,
    )
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ไม่พบไฟล์ {format.upper()} สำหรับโครงการนี้ กรุณาสร้างเอกสารก่อน",
        )

    media = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if format == "docx"
        else "application/pdf"
    )

    def iterfile():
        try:
            if hasattr(obj, "stream"):
                yield from obj.stream(32 * 1024)
            else:
                yield obj.read()
        finally:
            close = getattr(obj, "close", None)
            if close:
                close()
            release = getattr(obj, "release_conn", None)
            if release:
                release()

    logger.info(
        "Download stream for project %s format=%s path=%s by user %s",
        project_id,
        format,
        storage_path,
        current_user.id,
    )
    return StreamingResponse(
        iterfile(),
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="TOR.{format}"'},
    )
