"""Wizard step API endpoints.

PUT /projects/{id}/steps/{step} — Save step data (validate, persist, create version snapshot)
GET /projects/{id}/steps/{step} — Retrieve step data with AI draft content
POST /projects/{id}/steps/{step}/draft — Trigger AI drafting via Orchestrator

Requirements: 4.2, 4.3, 5.1
"""

from __future__ import annotations

from typing import Annotated

import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.constants import PROJECT_UUID_DESC, WIZARD_STEP_DESC
from app.config import get_settings
from app.deps import get_current_user, get_db
from app.domain.tor_sections import STEP_SECTION_MAP, TOR_SECTION_ORDER, VALID_STEPS
from app.domain.wizard_payload import normalize_step_payload, sections_to_step_data
from app.exceptions import NotFoundError, ValidationError
from app.models.project import Project
from app.models.project_version import ProjectVersion
from app.models.tor_section import TORSection
from app.models.user import User
from app.schemas.responses import MetaInfo, SuccessResponse
from app.schemas.wizard import (
    DraftResponse,
    DraftSectionRequest,
    SectionData,
    StepDataResponse,
    StepDataSave,
    StepSaveResponse,
)

logger = logging.getLogger("tor_app.wizard")

router = APIRouter()


# =============================================================================
# Helpers
# =============================================================================


async def _get_owned_project(
    project_id: uuid.UUID,
    user: User,
    db: AsyncSession,
) -> Project:
    """Fetch a project and verify ownership.

    Args:
        project_id: UUID of the project.
        user: Current authenticated user.
        db: Async database session.

    Returns:
        The project instance.

    Raises:
        NotFoundError: If the project does not exist.
        ValidationError: If the user does not own the project.
    """
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if project is None:
        raise NotFoundError(message="ไม่พบโครงการที่ระบุ")

    if project.owner_id != user.id:
        raise NotFoundError(message="ไม่พบโครงการที่ระบุ")

    return project


def _validate_step(step: int) -> None:
    """Validate that the step number is between 1 and 8."""
    if step not in VALID_STEPS:
        raise ValidationError(
            message=f"ขั้นตอนต้องอยู่ระหว่าง 1-8 (ได้รับ: {step})",
            field="step",
        )


async def _get_next_version_number(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> int:
    """Get the next version number for a project.

    Returns the next sequential version number (max + 1, or 1 if no versions exist).
    Enforces maximum 50 versions per project (Requirement 9.6).
    """
    stmt = (
        select(func.max(ProjectVersion.version_number))
        .where(ProjectVersion.project_id == project_id)
    )
    result = await db.execute(stmt)
    max_version = result.scalar_one_or_none()

    next_version = (max_version or 0) + 1

    # Enforce max 50 versions (Requirement 9.6)
    if next_version > 50:
        # Overwrite the oldest version by wrapping around
        next_version = 50

    return next_version


async def _build_snapshot_data(
    project_id: uuid.UUID,
    db: AsyncSession,
) -> dict:
    """Build a snapshot of all current TOR sections for versioning."""
    stmt = select(TORSection).where(TORSection.project_id == project_id)
    result = await db.execute(stmt)
    sections = result.scalars().all()

    snapshot: dict = {}
    for section in sections:
        key = section.section_key
        if section.sub_key:
            key = f"{section.section_key}.{section.sub_key}"
        snapshot[key] = {
            "content": section.content,
            "ai_draft": section.ai_draft,
            "quality_score": section.quality_score,
            "is_approved": section.is_approved,
            "version": section.version,
        }
    return snapshot


# =============================================================================
# PUT /projects/{id}/steps/{step} — Save step data
# =============================================================================


@router.put(
    "/{project_id}/steps/{step}",
    response_model=SuccessResponse,
    summary="Save wizard step data",
    description=(
        "Persist form data for a specific wizard step. "
        "Creates/updates TOR sections and generates a version snapshot."
    ),
)
async def save_step_data(
    project_id: Annotated[uuid.UUID, Path(..., description=PROJECT_UUID_DESC)],
    step: Annotated[int, Path(..., ge=1, le=8, description=WIZARD_STEP_DESC)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: StepDataSave,
) -> JSONResponse:
    """Save wizard step data.

    Validates the step data, persists it to TOR sections in the database,
    updates the project's current_step, and creates a version snapshot.

    Requirements: 4.2, 4.3
    """
    _validate_step(step)

    project = await _get_owned_project(project_id, current_user, db)

    payload = normalize_step_payload(step, body.data)

    if step == 1:
        if payload.get("project_name"):
            project.name = str(payload["project_name"])
        if payload.get("ministry"):
            project.ministry = str(payload["ministry"])
        if payload.get("budget"):
            try:
                project.budget = int(payload["budget"])
            except (TypeError, ValueError):
                pass
        if payload.get("project_type"):
            project.project_type = str(payload["project_type"])
        if payload.get("template_id"):
            try:
                project.template_id = uuid.UUID(str(payload["template_id"]))
            except (TypeError, ValueError):
                pass

    section_keys = STEP_SECTION_MAP.get(step, [])
    persist_keys = [
        key for key in payload
        if key in section_keys or key.startswith("s") and (
            key in TOR_SECTION_ORDER or key.startswith("s4.")
        )
    ]

    sections_updated = 0

    for section_key in persist_keys:
        if "." in section_key:
            continue
        stmt = select(TORSection).where(
            TORSection.project_id == project_id,
            TORSection.section_key == section_key,
            TORSection.sub_key.is_(None),
        )
        result = await db.execute(stmt)
        existing_section = result.scalar_one_or_none()

        section_content = payload.get(section_key, "")
        if isinstance(section_content, dict):
            section_content = json.dumps(section_content, ensure_ascii=False)
        elif not isinstance(section_content, str):
            section_content = str(section_content) if section_content else ""

        if not section_content:
            continue

        if existing_section:
            existing_section.content = section_content
            existing_section.version += 1
            sections_updated += 1
        else:
            new_section = TORSection(
                project_id=project_id,
                section_key=section_key,
                content=section_content,
                version=1,
            )
            db.add(new_section)
            sections_updated += 1

    for key, value in payload.items():
        if "." not in key:
            continue
        parts = key.split(".", 1)
        parent_key = f"s{parts[0]}" if not parts[0].startswith("s") else parts[0]
        sub_key = parts[1] if len(parts) > 1 else None

        if not sub_key:
            continue

        stmt = select(TORSection).where(
            TORSection.project_id == project_id,
            TORSection.section_key == parent_key,
            TORSection.sub_key == sub_key,
        )
        result = await db.execute(stmt)
        existing_sub = result.scalar_one_or_none()

        sub_content = value
        if isinstance(sub_content, dict):
            sub_content = json.dumps(sub_content, ensure_ascii=False)
        elif not isinstance(sub_content, str):
            sub_content = str(sub_content) if sub_content else ""

        if existing_sub:
            existing_sub.content = sub_content
            existing_sub.version += 1
        else:
            new_sub = TORSection(
                project_id=project_id,
                section_key=parent_key,
                sub_key=sub_key,
                content=sub_content,
                version=1,
            )
            db.add(new_sub)
        sections_updated += 1

    # Update project's current_step (advance to the next step or stay at current)
    if step >= project.current_step:
        project.current_step = min(step + 1, 8)

    # Create a version snapshot
    snapshot_data = await _build_snapshot_data(project_id, db)
    # Include the current body.data in the snapshot too
    snapshot_data["_step_data"] = body.data

    version_number = await _get_next_version_number(project_id, db)
    version = ProjectVersion(
        project_id=project_id,
        version_number=version_number,
        snapshot_data=snapshot_data,
        step_number=step,
    )
    db.add(version)

    # Flush to ensure all changes are in the session
    await db.flush()

    logger.info(
        "Step %d saved for project %s by user %s: %d sections updated, version %d",
        step,
        project_id,
        current_user.id,
        sections_updated,
        version_number,
    )

    # Build response
    response_data = StepSaveResponse(
        step=step,
        project_id=project_id,
        sections_updated=sections_updated,
        version_number=version_number,
    )

    response = SuccessResponse(
        ok=True,
        data=response_data.model_dump(mode="json"),
        meta=MetaInfo(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )

    return JSONResponse(
        status_code=200,
        content=response.model_dump(mode="json"),
    )


# =============================================================================
# GET /projects/{id}/steps/{step} — Retrieve step data
# =============================================================================


@router.get(
    "/{project_id}/steps/{step}",
    response_model=SuccessResponse,
    summary="Get wizard step data",
    description="Retrieve persisted form data and AI drafts for a specific wizard step.",
)
async def get_step_data(
    project_id: Annotated[uuid.UUID, Path(..., description=PROJECT_UUID_DESC)],
    step: Annotated[int, Path(..., ge=1, le=8, description=WIZARD_STEP_DESC)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """Retrieve step data including any AI-generated draft content.

    Returns all TOR sections associated with the given wizard step,
    including content, AI drafts, quality scores, and validation findings.

    Requirements: 4.3, 4.6
    """
    _validate_step(step)

    project = await _get_owned_project(project_id, current_user, db)

    section_keys = STEP_SECTION_MAP.get(step, [])
    sections: list[SectionData] = []
    raw_sections: list[dict] = []

    if section_keys:
        stmt = select(TORSection).where(
            TORSection.project_id == project_id,
            TORSection.section_key.in_(section_keys),
        )
        result = await db.execute(stmt)
        db_sections = result.scalars().all()

        for s in db_sections:
            sections.append(SectionData.model_validate(s))
            raw_sections.append({
                "section_key": s.section_key,
                "sub_key": s.sub_key,
                "content": s.content,
            })

    form_data = sections_to_step_data(
        step,
        raw_sections,
        {
            "name": project.name,
            "ministry": project.ministry,
            "budget": project.budget,
            "project_type": project.project_type,
            "template_id": str(project.template_id) if project.template_id else None,
        },
    )

    response_data = StepDataResponse(
        step=step,
        project_id=project_id,
        project_name=project.name,
        current_step=project.current_step,
        sections=sections,
        form_data=form_data,
    )

    response = SuccessResponse(
        ok=True,
        data=response_data.model_dump(mode="json"),
        meta=MetaInfo(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )

    return JSONResponse(
        status_code=200,
        content=response.model_dump(mode="json"),
    )


# =============================================================================
# POST /projects/{id}/steps/{step}/draft — Trigger AI drafting
# =============================================================================


@router.post(
    "/{project_id}/steps/{step}/draft",
    response_model=SuccessResponse,
    summary="Trigger AI drafting for a wizard step",
    description=(
        "Invoke the AI Orchestrator to generate a draft for the specified "
        "wizard step's TOR section. Returns the generated draft content."
    ),
)
async def trigger_draft(
    project_id: Annotated[uuid.UUID, Path(..., description=PROJECT_UUID_DESC)],
    step: Annotated[int, Path(..., ge=1, le=8, description=WIZARD_STEP_DESC)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: DraftSectionRequest | None = None,
) -> JSONResponse:
    """Trigger AI drafting via the Orchestrator.

    Invokes the LangGraph orchestrator to generate a draft for the
    specified TOR section. The orchestrator performs:
    1. Input validation
    2. RAG context retrieval
    3. LLM draft generation
    4. Rule Engine guardrail validation
    5. Returns best draft with quality metadata

    Requirements: 5.1
    """
    _validate_step(step)

    project = await _get_owned_project(project_id, current_user, db)

    # Determine the target section
    section_keys = STEP_SECTION_MAP.get(step, [])
    if not section_keys:
        raise ValidationError(
            message="ขั้นตอนนี้ไม่มีส่วน TOR ที่สามารถร่างได้",
            field="step",
        )

    # Use the specified target_section or default to the first section for this step
    target_section = (
        body.target_section if body and body.target_section else section_keys[0]
    )

    # Validate target_section belongs to this step
    if target_section not in section_keys:
        raise ValidationError(
            message=f"ส่วน '{target_section}' ไม่อยู่ในขั้นตอนที่ {step}",
            field="target_section",
        )

    # Gather existing user input for this step (from TOR sections)
    user_input: dict = {}

    # Fetch existing section content as context
    stmt = select(TORSection).where(TORSection.project_id == project_id)
    result = await db.execute(stmt)
    all_sections = result.scalars().all()

    existing_sections: dict = {}
    for s in all_sections:
        existing_sections[s.section_key] = s.content

    # Build user_input from project metadata and existing sections
    user_input = {
        "project_name": project.name,
        "ministry": project.ministry,
        "budget": project.budget,
        "project_type": project.project_type,
        "existing_sections": existing_sections,
    }

    # Merge additional context from the request body
    if body and body.additional_context:
        user_input.update(body.additional_context)

    # Get template data if project has a template
    template_data: dict = {}
    if project.template:
        template_data = {
            "section_structure": project.template.section_structure or {},
            "placeholder_guidance": project.template.placeholder_guidance or {},
        }

    # Invoke the orchestrator
    try:
        from app.orchestrator import compile_tor_drafting_graph

        graph = compile_tor_drafting_graph()

        initial_state = {
            "project_id": str(project_id),
            "user_input": user_input,
            "template": template_data,
            "target_section": target_section,
            "max_retries": 3,
            "agent_timeout_seconds": get_settings().drafting_agent_timeout_seconds(),
        }

        # Run the graph
        final_state = await graph.ainvoke(initial_state)

        # Extract results
        draft_content = final_state.get("draft_content", "")
        quality_score = final_state.get("quality_score")
        validation_findings = final_state.get("validation_findings", [])
        rag_failed = final_state.get("rag_retrieval_failed", False)
        error = final_state.get("error")

        # Use best draft if available and current draft failed
        if final_state.get("best_draft_content") and not draft_content:
            draft_content = final_state["best_draft_content"]
            quality_score = final_state.get("best_draft_score")
            validation_findings = final_state.get("best_draft_findings", [])

        if error and not draft_content:
            raise ValidationError(
                message=f"การสร้างร่างล้มเหลว: {error}",
                field="draft",
            )

        # Persist the AI draft to the TOR section
        stmt = select(TORSection).where(
            TORSection.project_id == project_id,
            TORSection.section_key == target_section,
            TORSection.sub_key.is_(None),
        )
        result = await db.execute(stmt)
        section = result.scalar_one_or_none()

        if section:
            section.ai_draft = draft_content
            section.quality_score = quality_score
            section.validation_findings = (
                {"findings": validation_findings} if validation_findings else None
            )
        else:
            # Create section with the AI draft
            new_section = TORSection(
                project_id=project_id,
                section_key=target_section,
                content="",
                ai_draft=draft_content,
                quality_score=quality_score,
                validation_findings=(
                    {"findings": validation_findings} if validation_findings else None
                ),
                version=1,
            )
            db.add(new_section)

        await db.flush()

        logger.info(
            "Draft generated for project %s, section %s, score=%s",
            project_id,
            target_section,
            quality_score,
        )

    except ValidationError:
        raise
    except ImportError:
        logger.exception("Orchestrator not available")
        raise ValidationError(
            message="ระบบ AI ไม่พร้อมใช้งาน กรุณาลองใหม่ภายหลัง",
            field="draft",
        )
    except Exception as exc:
        logger.exception(
            "Draft generation failed for project %s, section %s",
            project_id,
            target_section,
        )
        raise ValidationError(
            message="การสร้างร่างล้มเหลว กรุณาลองใหม่อีกครั้ง",
            field="draft",
            details=str(exc),
        )

    # Build response
    response_data = DraftResponse(
        step=step,
        project_id=project_id,
        target_section=target_section,
        draft_content=draft_content,
        quality_score=quality_score,
        validation_findings=validation_findings,
        rag_retrieval_failed=rag_failed,
    )

    response = SuccessResponse(
        ok=True,
        data=response_data.model_dump(mode="json"),
        meta=MetaInfo(
            request_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )

    return JSONResponse(
        status_code=200,
        content=response.model_dump(mode="json"),
    )
