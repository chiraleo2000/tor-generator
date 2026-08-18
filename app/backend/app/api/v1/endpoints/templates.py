"""Template management API endpoints.

GET /templates — List templates (officers see published only, admin sees all)
POST /templates — Create a new template (admin only)
PUT /templates/{id} — Update template (admin only)
DELETE /templates/{id} — Delete template with affected project warning (admin only)
PUT /templates/{id}/publish — Publish template (admin only, draft → published)
PUT /templates/{id}/unpublish — Unpublish template with affected project warning (admin only)

Validates: Requirements 7.1, 7.2, 7.4, 7.5, 7.6, 7.8
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.constants import TEMPLATE_NOT_FOUND
from app.deps import get_current_user, get_db
from app.exceptions import NotFoundError, ValidationError
from app.models.project import Project
from app.models.template import Template
from app.models.template_version import TemplateVersion
from app.models.user import User
from app.rbac import Role, require_role
from app.schemas.responses import MetaInfo, SuccessResponse
from app.schemas.template import (
    AffectedProjectInfo,
    TemplateCreateRequest,
    TemplateDeleteResponse,
    TemplateListItem,
    TemplateListResponse,
    TemplateResponse,
    TemplateUpdateRequest,
    TemplateWarningResponse,
)

logger = logging.getLogger("tor_app.templates")

router = APIRouter()


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


async def _get_affected_projects(
    db: AsyncSession, template_id: uuid.UUID
) -> list[AffectedProjectInfo]:
    """Find active projects referencing a template.

    Active = status in (draft, in_review) — projects that are still being worked on.
    """
    stmt = select(Project).where(
        Project.template_id == template_id,
        Project.status.in_(["draft", "in_review"]),
    )
    result = await db.execute(stmt)
    projects = result.scalars().all()

    return [
        AffectedProjectInfo(
            id=p.id,
            name=p.name,
            status=p.status,
            owner_id=p.owner_id,
        )
        for p in projects
    ]


# ---------------------------------------------------------------------------
# GET /templates — List templates
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=SuccessResponse,
    summary="List templates",
    description="List templates. Officers see only published templates. "
    "Admins see all templates (draft and published).",
)
async def list_templates(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    industry: Annotated[
        str | None,
        Query(description="Filter by industry (it, construction, consulting, general)"),
    ] = None,
    status_filter: Annotated[
        str | None,
        Query(alias="status", description="Filter by status (draft, published) — admin only"),
    ] = None,
) -> JSONResponse:
    """List templates based on user role.

    Officers can only see published templates.
    Admins can see all templates and filter by status.
    """
    base_query = select(Template)

    # Officers see only published templates
    if current_user.role != Role.ADMIN:
        base_query = base_query.where(Template.status == "published")
    elif status_filter is not None:
        # Admin can filter by status
        if status_filter not in ("draft", "published"):
            raise ValidationError(
                message="สถานะต้องเป็น 'draft' หรือ 'published'",
                field="status",
            )
        base_query = base_query.where(Template.status == status_filter)

    # Filter by industry if specified
    if industry is not None:
        if industry not in ("it", "construction", "consulting", "general"):
            raise ValidationError(
                message="ประเภทอุตสาหกรรมต้องเป็น it, construction, consulting, หรือ general",
                field="industry",
            )
        base_query = base_query.where(Template.industry == industry)

    # Order by created_at descending
    base_query = base_query.order_by(Template.created_at.desc())

    result = await db.execute(base_query)
    templates = result.scalars().all()

    response_data = TemplateListResponse(
        items=[TemplateListItem.model_validate(t) for t in templates],
        total=len(templates),
    ).model_dump(mode="json")

    return _build_success_response(request, response_data)


# ---------------------------------------------------------------------------
# POST /templates — Create template (admin only)
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=SuccessResponse,
    status_code=201,
    summary="Create a new template",
    description="Create a new TOR template. Admin only. Starts in 'draft' status.",
)
async def create_template(
    request: Request,
    body: TemplateCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
) -> JSONResponse:
    """Create a new template in draft status.

    Only administrators can create templates.
    Templates start in 'draft' status and must be explicitly published.
    A version snapshot is also created (version 1).
    """
    template = Template(
        name=body.name,
        industry=body.industry,
        status="draft",
        section_structure=body.section_structure,
        placeholder_guidance=body.placeholder_guidance,
        created_by=current_user.id,
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)

    # Create initial version snapshot
    version = TemplateVersion(
        template_id=template.id,
        version_number=1,
        section_structure=body.section_structure,
        placeholder_guidance=body.placeholder_guidance,
    )
    db.add(version)
    await db.flush()

    template_data = TemplateResponse.model_validate(template).model_dump(mode="json")

    logger.info("Template created: %s by admin %s", template.id, current_user.id)

    return _build_success_response(request, template_data, status_code=201)


# ---------------------------------------------------------------------------
# GET /templates/{id} — Get template detail
# ---------------------------------------------------------------------------


@router.get(
    "/{template_id}",
    response_model=SuccessResponse,
    summary="Get template detail",
    description="Retrieve a single template by ID. Officers can only access published templates.",
)
async def get_template(
    request: Request,
    template_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Get template detail by ID.

    Officers can only see published templates.
    Admins can see all templates regardless of status.
    """
    stmt = select(Template).where(Template.id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if template is None:
        raise NotFoundError(message=TEMPLATE_NOT_FOUND)

    # Officers can only access published templates
    if current_user.role != Role.ADMIN and template.status != "published":
        raise NotFoundError(message=TEMPLATE_NOT_FOUND)

    template_data = TemplateResponse.model_validate(template).model_dump(mode="json")
    return _build_success_response(request, template_data)


# ---------------------------------------------------------------------------
# PUT /templates/{id} — Update template (admin only)
# ---------------------------------------------------------------------------


@router.put(
    "/{template_id}",
    response_model=SuccessResponse,
    summary="Update template",
    description="Update template metadata and content. Admin only. "
    "Creates a new version snapshot on content changes.",
)
async def update_template(
    request: Request,
    template_id: uuid.UUID,
    body: TemplateUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
) -> JSONResponse:
    """Update template. Admin only.

    If section_structure or placeholder_guidance changes, a new version is created.
    This ensures existing TOR projects referencing older versions are unaffected.
    """
    stmt = select(Template).where(Template.id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if template is None:
        raise NotFoundError(message=TEMPLATE_NOT_FOUND)

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise ValidationError(message="ไม่มีข้อมูลที่ต้องการอัปเดต")

    # Track if content changed (needs new version)
    content_changed = (
        "section_structure" in update_data or "placeholder_guidance" in update_data
    )

    # Apply updates
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.flush()

    # Create new version if content changed
    if content_changed:
        # Get latest version number
        max_version_stmt = select(
            func.max(TemplateVersion.version_number)
        ).where(TemplateVersion.template_id == template_id)
        max_version_result = await db.execute(max_version_stmt)
        max_version = max_version_result.scalar_one() or 0

        new_version = TemplateVersion(
            template_id=template.id,
            version_number=max_version + 1,
            section_structure=template.section_structure,
            placeholder_guidance=template.placeholder_guidance,
        )
        db.add(new_version)
        await db.flush()

    await db.refresh(template)

    template_data = TemplateResponse.model_validate(template).model_dump(mode="json")

    logger.info("Template updated: %s by admin %s", template.id, current_user.id)

    return _build_success_response(request, template_data)


# ---------------------------------------------------------------------------
# PUT /templates/{id}/publish — Publish template (admin only)
# ---------------------------------------------------------------------------


@router.put(
    "/{template_id}/publish",
    response_model=SuccessResponse,
    summary="Publish template",
    description="Publish a draft template, making it visible to officers. "
    "Only draft templates can be published.",
)
async def publish_template(
    request: Request,
    template_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
) -> JSONResponse:
    """Publish a template (draft → published).

    Only templates in 'draft' status can be published.
    Once published, the template is visible to officers for use in new projects.
    """
    stmt = select(Template).where(Template.id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if template is None:
        raise NotFoundError(message=TEMPLATE_NOT_FOUND)

    if template.status == "published":
        raise ValidationError(message="เทมเพลตนี้เผยแพร่อยู่แล้ว")

    template.status = "published"
    await db.flush()
    await db.refresh(template)

    template_data = TemplateResponse.model_validate(template).model_dump(mode="json")

    logger.info("Template published: %s by admin %s", template.id, current_user.id)

    return _build_success_response(request, template_data)


# ---------------------------------------------------------------------------
# PUT /templates/{id}/unpublish — Unpublish template (admin only)
# ---------------------------------------------------------------------------


@router.put(
    "/{template_id}/unpublish",
    response_model=SuccessResponse,
    summary="Unpublish template",
    description="Unpublish a published template back to draft. "
    "Returns warning about affected projects if any exist.",
)
async def unpublish_template(
    request: Request,
    template_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
    confirm: Annotated[
        bool,
        Query(description="Set to true to confirm unpublishing despite affected projects"),
    ] = False,
) -> JSONResponse:
    """Unpublish a template (published → draft).

    If active projects reference this template, returns a warning listing them.
    Use ?confirm=true to proceed despite affected projects.
    """
    stmt = select(Template).where(Template.id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if template is None:
        raise NotFoundError(message=TEMPLATE_NOT_FOUND)

    if template.status == "draft":
        raise ValidationError(message="เทมเพลตนี้อยู่ในสถานะร่างอยู่แล้ว")

    # Check for affected projects
    affected = await _get_affected_projects(db, template_id)

    if affected and not confirm:
        warning_data = TemplateWarningResponse(
            warning="มีโครงการที่กำลังใช้เทมเพลตนี้อยู่ กรุณายืนยันการยกเลิกเผยแพร่",
            affected_projects=affected,
            affected_count=len(affected),
        ).model_dump(mode="json")
        return _build_success_response(request, warning_data)

    template.status = "draft"
    await db.flush()
    await db.refresh(template)

    template_data = TemplateResponse.model_validate(template).model_dump(mode="json")

    logger.info(
        "Template unpublished: %s by admin %s (affected projects: %d)",
        template.id,
        current_user.id,
        len(affected),
    )

    return _build_success_response(request, template_data)


# ---------------------------------------------------------------------------
# DELETE /templates/{id} — Delete template (admin only)
# ---------------------------------------------------------------------------


@router.delete(
    "/{template_id}",
    response_model=SuccessResponse,
    summary="Delete template",
    description="Delete a template. Returns warning about affected projects. "
    "Use ?confirm=true to proceed despite affected projects.",
)
async def delete_template(
    request: Request,
    template_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role([Role.ADMIN]))],
    confirm: Annotated[
        bool,
        Query(description="Set to true to confirm deletion despite affected projects"),
    ] = False,
) -> JSONResponse:
    """Delete a template.

    If active projects reference this template, returns a warning listing them.
    Use ?confirm=true to force deletion. Affected projects will have their
    template_id preserved (the reference becomes stale but data is retained).
    """
    stmt = select(Template).where(Template.id == template_id)
    result = await db.execute(stmt)
    template = result.scalar_one_or_none()

    if template is None:
        raise NotFoundError(message=TEMPLATE_NOT_FOUND)

    # Check for affected projects
    affected = await _get_affected_projects(db, template_id)

    if affected and not confirm:
        warning_data = TemplateWarningResponse(
            warning="มีโครงการที่กำลังใช้เทมเพลตนี้อยู่ กรุณายืนยันการลบ",
            affected_projects=affected,
            affected_count=len(affected),
        ).model_dump(mode="json")
        return _build_success_response(request, warning_data)

    # Nullify template_id on affected projects to avoid FK violations
    if affected:
        for proj_info in affected:
            proj_stmt = select(Project).where(Project.id == proj_info.id)
            proj_result = await db.execute(proj_stmt)
            proj = proj_result.scalar_one_or_none()
            if proj:
                proj.template_id = None

    # Delete template versions first
    versions_stmt = select(TemplateVersion).where(
        TemplateVersion.template_id == template_id
    )
    versions_result = await db.execute(versions_stmt)
    versions = versions_result.scalars().all()
    for v in versions:
        await db.delete(v)

    # Delete the template
    await db.delete(template)
    await db.flush()

    delete_data = TemplateDeleteResponse(
        message="ลบเทมเพลตเรียบร้อย",
        id=str(template_id),
        had_affected_projects=len(affected) > 0,
        affected_project_count=len(affected),
    ).model_dump(mode="json")

    logger.info(
        "Template deleted: %s by admin %s (affected projects: %d)",
        template_id,
        current_user.id,
        len(affected),
    )

    return _build_success_response(request, delete_data)
