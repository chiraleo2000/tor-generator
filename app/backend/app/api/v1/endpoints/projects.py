"""Project CRUD API endpoints.

GET /projects — List user's projects (paginated, filterable by status)
POST /projects — Create a new project
GET /projects/{id} — Get project detail
PUT /projects/{id} — Update project metadata
DELETE /projects/{id} — Archive project (soft-delete)
GET /projects/{id}/versions — List version history
POST /projects/{id}/versions/{version}/restore — Restore project to a specific version

Validates: Requirements 9.4, 9.5, 9.6, 9.9
"""

import logging
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.constants import PROJECT_NOT_FOUND
from app.deps import get_current_user, get_db
from app.domain.extraction_map import (
    extract_nlp_fields,
    infer_wizard_fields,
    map_extracted_text,
    mapping_rows,
    section_preview,
)
from app.domain.file_magic import require_allowed_upload
from app.domain.tor_sections import (
    MANDATORY_HUMAN_REVIEW_SECTIONS,
    SCOPE_SUBSECTIONS,
    TOR_SECTION_LABELS,
    TOR_SECTION_ORDER,
)
from app.exceptions import NotFoundError, ValidationError
from app.io_temp import unlink_path, write_temp_bytes
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.tor_section import TORSection
from app.models.user import User
from app.rag.extraction import ExtractionResult, extract_text
from app.rbac import require_project_access, require_role
from app.schemas.project import (
    AnalysisUpdateRequest,
    PaginationMeta,
    PhaseUpdateRequest,
    ProjectCreateRequest,
    ProjectListItem,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatus,
    ProjectUpdateRequest,
    ProjectVersionListResponse,
    ProjectVersionResponse,
    SectionSaveRequest,
)
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.audit_service import AuditService, get_client_ip
from app.services.intake_service import can_set_phase, clamp_draft_phase

logger = logging.getLogger("tor_app.projects")

router = APIRouter()

# Maximum versions per project (requirement 9.6)
MAX_VERSIONS_PER_PROJECT = 50


def officer_can_submit(
    status: str,
    current_phase: int,
    has_review_score: bool = False,
) -> bool:
    """Draft/rejected always; archived after Phase 4 or a stored Rule Engine score."""
    if status in {"draft", "rejected"}:
        return True
    if status != "archived":
        return False
    return current_phase >= 4 or has_review_score


def _index_tor_sections(
    rows: list[TORSection],
) -> tuple[dict[str, TORSection], dict[str, dict[str, TORSection]]]:
    by_key: dict[str, TORSection] = {}
    subs: dict[str, dict[str, TORSection]] = {}
    for row in rows:
        if row.sub_key:
            subs.setdefault(row.section_key, {})[row.sub_key] = row
        else:
            by_key[row.section_key] = row
    return by_key, subs


def _scope_sub_payload(scope_map: dict[str, TORSection], _slot_map: dict) -> list[dict]:
    items: list[dict] = []
    for sub_key, title in SCOPE_SUBSECTIONS.items():
        sub_row = scope_map.get(sub_key) or scope_map.get(sub_key.replace("s4.", "4."))
        content = (sub_row.content if sub_row else "") or ""
        items.append(
            {
                "key": sub_key,
                "title": title,
                "content": content,
                "filled": bool(str(content).strip()),
            }
        )
    return items


def _normalize_parent_content(section_key: str, content: str, row: TORSection | None) -> str:
    from app.domain.section_fields import SECTION_FIELDS, persist_section_fields

    if section_key not in SECTION_FIELDS:
        return content
    rewritten = persist_section_fields(section_key, content or "")
    if row is not None and rewritten and rewritten != (row.content or ""):
        row.content = rewritten
    return rewritten or content


def _hydrate_scope_subs(
    parent: TORSection | None,
    scope_map: dict[str, TORSection],
    slot_map: dict,
) -> list[dict]:
    items = _scope_sub_payload(scope_map, slot_map)
    if not any(item["filled"] for item in items):
        blob = (parent.content if parent else "") or ""
        if blob.strip():
            from app.export.table_parse import split_scope_subsection_draft

            parts = split_scope_subsection_draft(blob)
            for item in items:
                text = str(parts.get(item["key"]) or "").strip()
                if text:
                    item["content"] = text
                    item["filled"] = True
    return items


def _build_success_response(
    request: Request, data: object, status_code: int = 200
) -> JSONResponse:
    """Build a standard success envelope response."""
    request_id = getattr(request.state, "request_id", "unknown")
    response = SuccessResponse(
        ok=True,
        data=data,
        meta=MetaInfo(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(mode="json"),
    )


# ---------------------------------------------------------------------------
# GET /projects — List projects (paginated, filterable)
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="List projects",
    description="List user's projects with pagination, filterable by status. "
    "Officers see only their own projects. Admins and reviewers see all.",
)
async def list_projects(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
    status_filter: Annotated[
        ProjectStatus | None,
        Query(alias="status", description="Filter by project status"),
    ] = None,
) -> JSONResponse:
    """List projects for the current user.

    Officers see only their own projects.
    Admin and reviewer roles can see all projects.
    Supports pagination (default 20/page) sorted by updated_at descending.
    """
    # Base query
    base_query = select(Project)

    # Officers can only see their own projects
    if current_user.role == "officer":
        base_query = base_query.where(Project.owner_id == current_user.id)

    # Apply status filter
    if status_filter is not None:
        base_query = base_query.where(Project.status == status_filter)

    # Count total items
    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Calculate pagination
    total_pages = max(1, math.ceil(total / per_page))
    offset = (page - 1) * per_page

    # Fetch paginated results sorted by updated_at descending
    items_query = (
        base_query.order_by(Project.updated_at.desc()).offset(offset).limit(per_page)
    )
    result = await db.execute(items_query)
    projects = result.scalars().all()

    pagination = PaginationMeta(
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
    )

    response_data = ProjectListResponse(
        items=[ProjectListItem.model_validate(p) for p in projects],
        pagination=pagination,
    ).model_dump(mode="json")

    return _build_success_response(request, response_data)


# ---------------------------------------------------------------------------
# POST /projects — Create a new project
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=SuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Create a new TOR project. Starts in draft status at Phase 0.",
)
async def create_project(
    request: Request,
    body: ProjectCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Create a new TOR project owned by the current user.

    The project is initialized with status='draft' and current_step=1.
    """
    project = Project(
        owner_id=current_user.id,
        name=body.name,
        ministry=body.ministry,
        budget=body.budget,
        project_type=body.project_type,
        status="draft",
        current_step=1,
        current_phase=0,
        analysis_json={},
        extracted_fields={},
        template_id=body.template_id,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)

    project_data = ProjectResponse.model_validate(project).model_dump(mode="json")

    logger.info(
        "Project created: %s by user %s", project.id, current_user.id
    )

    return _build_success_response(request, project_data, status_code=201)


# ---------------------------------------------------------------------------
# GET /projects/{id} — Get project detail
# ---------------------------------------------------------------------------


@router.get(
    "/{project_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project detail",
    description="Retrieve a single project by ID. Enforces ownership/role access.",
)
async def get_project(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Get project detail by ID. Enforces project ownership or admin/reviewer role."""
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)

    # Check access
    require_project_access(project.owner_id, current_user)

    if clamp_draft_phase(project):
        await db.flush()

    project_data = ProjectResponse.model_validate(project).model_dump(mode="json")
    return _build_success_response(request, project_data)


# ---------------------------------------------------------------------------
# PUT /projects/{id} — Update project metadata
# ---------------------------------------------------------------------------


@router.put(
    "/{project_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Update project",
    description="Update project metadata. Only the owner or admin can update.",
)
async def update_project(
    request: Request,
    project_id: uuid.UUID,
    body: ProjectUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Update project metadata. Enforces ownership or admin role."""
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)

    # Check access
    require_project_access(project.owner_id, current_user)

    # Apply updates (only non-None fields)
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise ValidationError(message="ไม่มีข้อมูลที่ต้องการอัปเดต")

    for field, value in update_data.items():
        setattr(project, field, value)

    await db.flush()
    await db.refresh(project)

    project_data = ProjectResponse.model_validate(project).model_dump(mode="json")

    logger.info("Project updated: %s by user %s", project.id, current_user.id)

    return _build_success_response(request, project_data)


# ---------------------------------------------------------------------------
# DELETE /projects/{id} — Archive project (soft-delete)
# ---------------------------------------------------------------------------


@router.delete(
    "/{project_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Archive project",
    description="Archive a project (soft-delete by setting status to 'archived'). "
    "Only the owner or admin can archive.",
)
async def delete_project(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Archive a project by setting its status to 'archived'.

    This is a soft-delete — the project remains in the database but
    is no longer shown in active project lists unless filtered by status='archived'.
    """
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)

    # Check access
    require_project_access(project.owner_id, current_user)

    if project.status == "archived":
        raise ValidationError(message="โครงการนี้ถูกจัดเก็บแล้ว")

    project.status = "archived"
    await db.flush()
    await db.refresh(project)

    logger.info("Project archived: %s by user %s", project.id, current_user.id)

    return _build_success_response(
        request, {"message": "จัดเก็บโครงการเรียบร้อย", "id": str(project.id)}
    )


# ---------------------------------------------------------------------------
# GET /projects/{id}/versions — List version history
# ---------------------------------------------------------------------------


@router.get(
    "/{project_id}/versions",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="List project versions",
    description="Retrieve version history for a project, sorted by version_number descending.",
)
async def list_versions(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """List all versions of a project sorted by version_number descending."""
    # Verify project exists and user has access
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)

    require_project_access(project.owner_id, current_user)

    # Fetch versions
    versions_stmt = (
        select(ProjectVersion)
        .where(ProjectVersion.project_id == project_id)
        .order_by(ProjectVersion.version_number.desc())
    )
    versions_result = await db.execute(versions_stmt)
    versions = versions_result.scalars().all()

    response_data = ProjectVersionListResponse(
        items=[ProjectVersionResponse.model_validate(v) for v in versions],
        total=len(versions),
    ).model_dump(mode="json")

    return _build_success_response(request, response_data)


# ---------------------------------------------------------------------------
# POST /projects/{id}/versions/{version}/restore — Restore to version
# ---------------------------------------------------------------------------


@router.post(
    "/{project_id}/versions/{version_number}/restore",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Restore project to a specific version",
    description="Restore the project state from a version snapshot. "
    "Creates a new version representing the restored state.",
)
async def restore_version(
    request: Request,
    project_id: uuid.UUID,
    version_number: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Restore a project to a specific version.

    This creates a new version entry with the restored snapshot data,
    preserving the full version history. Enforces max 50 versions per project.
    """
    # Verify project exists and user has access
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)

    require_project_access(project.owner_id, current_user)

    # Find the version to restore
    version_stmt = select(ProjectVersion).where(
        ProjectVersion.project_id == project_id,
        ProjectVersion.version_number == version_number,
    )
    version_result = await db.execute(version_stmt)
    version = version_result.scalar_one_or_none()

    if version is None:
        raise NotFoundError(
            message=f"ไม่พบเวอร์ชัน {version_number} ของโครงการนี้"
        )

    # Check max versions limit
    count_stmt = select(func.count()).where(
        ProjectVersion.project_id == project_id
    )
    count_result = await db.execute(count_stmt)
    current_count = count_result.scalar_one()

    if current_count >= MAX_VERSIONS_PER_PROJECT:
        raise ValidationError(
            message=(
                f"โครงการนี้มีเวอร์ชันครบ {MAX_VERSIONS_PER_PROJECT} เวอร์ชันแล้ว "
                "ไม่สามารถสร้างเวอร์ชันใหม่ได้"
            )
        )

    # Get the latest version number
    max_version_stmt = select(func.max(ProjectVersion.version_number)).where(
        ProjectVersion.project_id == project_id
    )
    max_version_result = await db.execute(max_version_stmt)
    max_version = max_version_result.scalar_one() or 0

    # Create a new version with the restored snapshot
    new_version = ProjectVersion(
        project_id=project_id,
        version_number=max_version + 1,
        snapshot_data=version.snapshot_data,
        step_number=version.step_number,
    )
    db.add(new_version)

    # Update project current_step from the restored snapshot
    project.current_step = version.step_number

    await db.flush()
    await db.refresh(new_version)

    version_data = ProjectVersionResponse.model_validate(new_version).model_dump(
        mode="json"
    )

    logger.info(
        "Project %s restored to version %d (new version %d) by user %s",
        project_id,
        version_number,
        new_version.version_number,
        current_user.id,
    )

    return _build_success_response(request, version_data)


# ---------------------------------------------------------------------------
# Workflow: submit / approve / reject
# ---------------------------------------------------------------------------


@router.post(
    "/{project_id}/submit",
    response_model=SuccessResponse,
    summary="Submit project for review",
)
async def submit_project(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)
    require_project_access(project.owner_id, current_user)
    if not officer_can_submit(
        str(project.status or ""),
        int(project.current_phase or 0),
        project.quality_score is not None,
    ):
        raise ValidationError(message="สามารถส่งตรวจสอบได้เฉพาะโครงการที่เป็นร่างหรือถูกส่งกลับ")
    project.status = "in_review"
    await db.flush()
    await db.refresh(project)
    await AuditService.log(
        db,
        action="review",
        resource_type="project",
        user_id=current_user.id,
        resource_id=project.id,
        ip_address=get_client_ip(request),
        details={"event": "submit"},
    )
    return _build_success_response(
        request, ProjectResponse.model_validate(project).model_dump(mode="json")
    )


@router.post(
    "/{project_id}/approve",
    response_model=SuccessResponse,
    summary="Approve project (reviewer/admin)",
)
async def approve_project(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["reviewer", "admin"]))],
) -> JSONResponse:
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)
    project.status = "approved"
    await db.flush()
    await db.refresh(project)
    return _build_success_response(
        request, ProjectResponse.model_validate(project).model_dump(mode="json")
    )


@router.post(
    "/{project_id}/reject",
    response_model=SuccessResponse,
    summary="Reject project (reviewer/admin)",
)
async def reject_project(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["reviewer", "admin"]))],
) -> JSONResponse:
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)
    project.status = "rejected"
    await db.flush()
    await db.refresh(project)
    return _build_success_response(
        request, ProjectResponse.model_validate(project).model_dump(mode="json")
    )


class ExtractionApplyRequest(BaseModel):
    sections: dict[str, str]
    fields: dict | None = None
    extracted: dict | None = None
    confirm: bool = True


@router.post(
    "/{project_id}/extraction",
    response_model=SuccessResponse,
    summary="Phase 0: extract a reference TOR and propose a field map",
)
async def extract_project_reference(
    request: Request,
    project_id: uuid.UUID,
    file: UploadFile,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    doc_class: Annotated[str, Form()] = "other",
) -> JSONResponse:
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)
    require_project_access(project.owner_id, current_user)

    raw = await file.read()
    if not raw:
        raise ValidationError(message="ไฟล์ว่างเปล่า")
    try:
        mime = require_allowed_upload(raw, file.content_type or "")
    except ValueError as exc:
        raise ValidationError(message=str(exc), field="file") from exc
    suffix = Path(file.filename or "upload.bin").suffix or ".bin"
    tmp_path = await write_temp_bytes(raw, suffix)
    try:
        try:
            extracted = extract_text(tmp_path, mime)
        except (ValueError, OSError, RuntimeError) as exc:
            logger.warning("Phase 0 extraction partial failure: %s", exc)
            extracted = ExtractionResult(
                text="",
                page_count=1,
                method="direct",
                warnings=[str(exc)],
            )
        mapped = map_extracted_text(extracted.text)
        nlp = extract_nlp_fields(extracted.text)
    finally:
        await unlink_path(tmp_path)

    fields = infer_wizard_fields(mapped)
    status_label = "success" if extracted.text.strip() else "partial_failure"
    return _build_success_response(
        request,
        {
            "proposed": mapped,
            "fields": fields,
            "extracted": nlp,
            "mapping": mapping_rows(nlp),
            "preview": section_preview(mapped),
            "filename": file.filename,
            "doc_class": doc_class,
            "char_count": len(extracted.text or ""),
            "extractionStatus": status_label,
            "extractionError": None if extracted.text.strip() else "ไม่พบข้อความในไฟล์",
        },
    )


@router.post(
    "/{project_id}/extraction/apply",
    response_model=SuccessResponse,
    summary="Confirm Phase 0 map and write TOR sections",
)
async def apply_project_extraction(
    request: Request,
    project_id: uuid.UUID,
    body: ExtractionApplyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    if not body.confirm:
        raise ValidationError(message="ต้องยืนยันก่อนเขียนทับข้อมูล")
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)
    require_project_access(project.owner_id, current_user)

    written = 0
    for key, content in body.sections.items():
        if not content:
            continue
        existing = (
            await db.execute(
                select(TORSection).where(
                    TORSection.project_id == project_id,
                    TORSection.section_key == key,
                    TORSection.sub_key.is_(None),
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.content = content
            existing.version += 1
        else:
            db.add(
                TORSection(
                    project_id=project_id,
                    section_key=key,
                    content=content,
                    version=1,
                )
            )
        written += 1

    extracted = dict(project.extracted_fields or {})
    if body.extracted:
        extracted.update(body.extracted)
    project.extracted_fields = extracted
    nlp = body.extracted or {}
    if isinstance(nlp.get("projectName"), str) and nlp["projectName"].strip():
        project.name = nlp["projectName"].strip()[:500]
    if isinstance(nlp.get("ministry"), str) and nlp["ministry"].strip():
        project.ministry = nlp["ministry"].strip()[:255]
    if isinstance(nlp.get("budget"), int) and nlp["budget"] > 0:
        project.budget = nlp["budget"]
    await db.flush()
    await db.refresh(project)
    await AuditService.log(
        db,
        action="update",
        resource_type="project",
        user_id=current_user.id,
        resource_id=project.id,
        ip_address=get_client_ip(request),
        details={"event": "extraction_apply", "written": written},
    )
    return _build_success_response(
        request,
        {
            "written": written,
            "fields": body.fields or {},
            "project": ProjectResponse.model_validate(project).model_dump(mode="json"),
        },
    )


async def _owned_project(
    project_id: uuid.UUID, user: User, db: AsyncSession
) -> Project:
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)
    require_project_access(project.owner_id, user)
    return project


@router.patch(
    "/{project_id}/phase",
    response_model=SuccessResponse,
    summary="Set drafting phase 0-4",
)
async def patch_project_phase(
    request: Request,
    project_id: uuid.UUID,
    body: PhaseUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    project = await _owned_project(project_id, current_user, db)
    if not can_set_phase(project, body.phase):
        raise ValidationError(
            message="ต้องวางข้อความหรืออัปโหลดเอกสารในขั้นที่ ๐ ก่อน จึงจะร่างได้",
            field="phase",
        )
    project.current_phase = body.phase
    await db.flush()
    await db.refresh(project)
    return _build_success_response(
        request, ProjectResponse.model_validate(project).model_dump(mode="json")
    )


@router.put(
    "/{project_id}/analysis",
    response_model=SuccessResponse,
    summary="Save Phase 1 analysis intake",
)
async def put_project_analysis(
    request: Request,
    project_id: uuid.UUID,
    body: AnalysisUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    project = await _owned_project(project_id, current_user, db)
    project.analysis_json = body.analysis
    await db.flush()
    return _build_success_response(request, {"analysis": project.analysis_json})


@router.get(
    "/{project_id}/sections",
    response_model=SuccessResponse,
    summary="List TOR sections with fill and mapping status",
)
async def list_project_sections(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    project = await _owned_project(project_id, current_user, db)
    rows = (
        await db.execute(select(TORSection).where(TORSection.project_id == project_id))
    ).scalars().all()
    by_key, subs = _index_tor_sections(list(rows))
    extracted = project.extracted_fields or {}
    raw_slots = (project.analysis_json or {}).get("slot_map") or {}
    slot_map = raw_slots if isinstance(raw_slots, dict) else {}
    sections = []
    for key in TOR_SECTION_ORDER:
        row = by_key.get(key)
        content = (row.content if row else "") or ""
        if key != "s4":
            content = _normalize_parent_content(key, content, row)
        filled = bool(str(content or "").strip())
        item: dict = {
            "key": key,
            "title": TOR_SECTION_LABELS[key],
            "filled": filled,
            "content": content,
            "ai_draft": row.ai_draft if row else "",
            "human_confirmed": bool(row.is_approved) if row else False,
            "hitl": key in MANDATORY_HUMAN_REVIEW_SECTIONS,
            "matchStatus": "matched" if extracted else "partial",
        }
        if key == "s4":
            item["big"] = True
            item["subs"] = _hydrate_scope_subs(row, subs.get("s4") or {}, slot_map)
            item["filled"] = filled or any(sub["filled"] for sub in item["subs"])
        sections.append(item)
    return _build_success_response(request, {"sections": sections})


@router.put(
    "/{project_id}/sections/{section_key}",
    response_model=SuccessResponse,
    summary="Save one TOR section or scope subsection",
)
async def put_project_section(
    request: Request,
    project_id: uuid.UUID,
    section_key: str,
    body: SectionSaveRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    await _owned_project(project_id, current_user, db)
    key = section_key.strip()
    main_key = key
    sub_key = None
    if key.startswith(("s4.", "4.")):
        main_key = "s4"
        sub_key = key if key.startswith("s4.") else f"s4.{key[2:]}"
    elif key not in TOR_SECTION_ORDER:
        raise ValidationError(message="รหัสหมวดไม่ถูกต้อง", field="section_key")

    content = body.content
    if body.fields:
        content = body.content or str(body.fields)
    if not sub_key:
        from app.domain.section_fields import persist_section_fields

        content = persist_section_fields(main_key, content or "")

    existing_stmt = select(TORSection).where(
        TORSection.project_id == project_id,
        TORSection.section_key == main_key,
    )
    if sub_key:
        existing_stmt = existing_stmt.where(TORSection.sub_key == sub_key)
    else:
        existing_stmt = existing_stmt.where(TORSection.sub_key.is_(None))
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        existing.content = content
        existing.version += 1
        if body.human_confirmed:
            existing.is_approved = True
    else:
        db.add(
            TORSection(
                project_id=project_id,
                section_key=main_key,
                sub_key=sub_key,
                content=content,
                is_approved=body.human_confirmed,
                version=1,
            )
        )
    await db.flush()
    return _build_success_response(
        request,
        {"sectionKey": key, "filled": body.filled, "human_confirmed": body.human_confirmed},
    )
