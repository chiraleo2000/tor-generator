"""AI review, suggestions, and validation endpoints.

POST /projects/{id}/review — Run full Rule Engine review on assembled TOR
GET /projects/{id}/suggestions — Get AI suggestions (3-20 items, categorized)
PUT /projects/{id}/suggestions/{sid} — Accept/dismiss a suggestion
POST /projects/{id}/validate — Real-time validation (debounced server-side)

Validates: Requirements 5.1, 6.1, 10.1, 10.3, 10.5
"""

from __future__ import annotations

from typing import Annotated

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Path, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.constants import PROJECT_NOT_FOUND, PROJECT_UUID_DESC
from app.domain.section_text import section_plain_text
from app.deps import get_current_user, get_db
from app.exceptions import NotFoundError, ValidationError
from app.llm_admission import admit
from app.models.project import Project
from app.models.suggestion import Suggestion
from app.models.tor_section import TORSection
from app.models.user import User
from app.rate_limiter import rate_limit_ai
from app.rbac import require_project_access
from app.schemas.drafting import (
    CategoryScoreResponse,
    FindingResponse,
    ReviewRequest,
    ReviewResponse,
    SuggestionListResponse,
    SuggestionResponse,
    SuggestionStatus,
    SuggestionUpdateRequest,
    SuggestionUpdateResponse,
    ValidateRequest,
    ValidateResponse,
)
from app.schemas.responses import MetaInfo, SuccessResponse

logger = logging.getLogger("tor_app.review")

router = APIRouter()


def persist_analysis_json(project: Project, analysis: dict) -> None:
    """JSONB assignment + flag_modified; no-op on unit-test mocks (spec=Project)."""
    project.analysis_json = analysis
    try:
        flag_modified(project, "analysis_json")
    except AttributeError:
        return


def _build_response(request: Request, data: object, status_code: int = 200) -> JSONResponse:
    """Build a standard success envelope response."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
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


async def _get_project_with_access(
    project_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Project:
    """Fetch a project and verify user access."""
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)

    require_project_access(project.owner_id, current_user)
    return project


# =============================================================================
# POST /projects/{id}/review — Run full Rule Engine review
# =============================================================================


@router.post(
    "/{project_id}/review",
    response_model=SuccessResponse,
    summary="Run full Rule Engine review",
    description=(
        "Run the Rule Engine on the full assembled TOR document. "
        "Also invokes the ReviewAgent to generate categorized suggestions. "
        "Returns quality score, findings, and generates suggestions."
    ),
    dependencies=[Depends(rate_limit_ai)],
)
async def run_review(
    request: Request,
    project_id: Annotated[uuid.UUID, Path(..., description=PROJECT_UUID_DESC)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: ReviewRequest | None = None,
) -> JSONResponse:
    """Run full Rule Engine review on the assembled TOR.

    1. Collects all TOR sections for the project
    2. Runs Rule Engine validation (deterministic, within 30s per Req 6.1)
    3. Invokes ReviewAgent for cross-section analysis
    4. Persists generated suggestions to the database
    5. Updates project quality_score

    Requirements: 6.1, 10.1, 10.2
    """
    project = await _get_project_with_access(project_id, current_user, db)

    # Collect all TOR sections
    sections_stmt = select(TORSection).where(TORSection.project_id == project_id)
    sections_result = await db.execute(sections_stmt)
    all_sections = sections_result.scalars().all()

    # Build tor_document dict for the Rule Engine
    tor_document: dict = {}
    sections_map: dict[str, str] = {}

    for section in all_sections:
        content = section_plain_text(section.content or "")
        if section.sub_key:
            key = f"{section.section_key}.{section.sub_key}"
        else:
            key = section.section_key
        tor_document[key] = content
        sections_map[section.section_key] = content

    # Add project metadata needed for validation rules
    tor_document["budget"] = project.budget
    tor_document["project_type"] = project.project_type

    # Run the Rule Engine
    try:
        from app.orchestrator.graph import _create_rule_engine

        engine = _create_rule_engine()
        validation_result = engine.validate(tor_document)
    except Exception as exc:
        logger.exception(
            "Rule Engine validation failed for project %s",
            project_id,
        )
        raise ValidationError(
            message="การตรวจสอบล้มเหลว กรุณาลองใหม่อีกครั้ง",
            field="review",
            details=str(exc),
        ) from exc

    # Build findings response
    findings_response = [
        FindingResponse(
            severity=f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            rule_violated=f.rule_violated,
            affected_section=f.affected_section,
            message=f.message,
            recommended_correction=f.recommended_correction,
        )
        for f in validation_result.findings
    ]

    # Build category scores response
    category_labels = {
        "legal": "ความถูกต้องตามกฎหมาย",
        "completeness": "ความครบถ้วน",
        "consistency": "ความสอดคล้อง",
        "format": "รูปแบบเอกสาร",
    }
    categories_response = [
        CategoryScoreResponse(
            category=cs.category,
            label=category_labels.get(cs.category, cs.category),
            score=cs.score,
            weight=cs.weight if cs.weight > 1 else cs.weight * 100,
        )
        for cs in validation_result.categories
    ]

    # Update project quality_score and persist findings for refresh
    project.quality_score = validation_result.quality_score
    analysis = dict(project.analysis_json or {})
    analysis["review_score"] = validation_result.quality_score
    analysis["review_is_valid"] = validation_result.is_valid
    analysis["review_findings"] = [
        item.model_dump(mode="json") for item in findings_response
    ]
    persist_analysis_json(project, analysis)
    await db.flush()

    # Invoke ReviewAgent to generate suggestions (async, best-effort)
    suggestions_generated = 0
    try:
        request_id = (
            request.headers.get("X-AI-Request-Id") or str(uuid.uuid4())
        ).strip()
        redis = getattr(request.app.state, "redis", None)
        suggestions_generated = await _generate_suggestions(
            project_id=project_id,
            sections_map=sections_map,
            project_metadata={
                "budget": project.budget,
                "project_type": project.project_type,
            },
            db=db,
            custom_requirements=project.custom_requirements_text,
            redis=redis,
            request_id=request_id,
        )
    except Exception as exc:
        logger.warning(
            "ReviewAgent suggestion generation failed for project %s: %s. "
            "Continuing with Rule Engine results only.",
            project_id,
            exc,
        )

    # Build response
    response_data = ReviewResponse(
        project_id=project_id,
        quality_score=validation_result.quality_score,
        is_valid=validation_result.is_valid,
        halted=validation_result.halted,
        missing_sections=validation_result.missing_sections,
        categories=categories_response,
        findings=findings_response,
        suggestions_generated=suggestions_generated,
    )

    logger.info(
        "Review completed for project %s: score=%d, valid=%s, findings=%d, suggestions=%d",
        project_id,
        validation_result.quality_score,
        validation_result.is_valid,
        len(validation_result.findings),
        suggestions_generated,
    )

    return _build_response(request, response_data.model_dump(mode="json"))


async def _generate_suggestions(
    project_id: uuid.UUID,
    sections_map: dict[str, str],
    project_metadata: dict,
    db: AsyncSession,
    custom_requirements: str | None = None,
    redis=None,
    request_id: str | None = None,
) -> int:
    """Generate AI suggestions via the ReviewAgent and persist them.

    Removes existing pending suggestions before generating new ones.
    Returns the number of suggestions generated.
    """
    from app.orchestrator.agents.review_agent import ReviewAgent
    from app.providers.factory import ProviderFactory

    # Delete existing pending suggestions for this project (regenerate fresh)
    delete_stmt = select(Suggestion).where(
        Suggestion.project_id == project_id,
        Suggestion.status == "pending",
    )
    existing_result = await db.execute(delete_stmt)
    existing_pending = existing_result.scalars().all()
    for s in existing_pending:
        await db.delete(s)
    await db.flush()

    # Get LLM provider
    factory = ProviderFactory()
    llm = factory.get_llm("structured")

    # Run the ReviewAgent under admission control
    agent = ReviewAgent()
    rid = (request_id or str(uuid.uuid4())).strip()
    async with admit(redis, "llm", rid):
        review_result = await agent.review(
            llm=llm,
            sections=sections_map,
            project_metadata=project_metadata,
            custom_requirements=custom_requirements,
        )

    # Persist suggestions
    for suggestion in review_result.suggestions:
        db_suggestion = Suggestion(
            project_id=project_id,
            section_key=suggestion.section_key,
            category=suggestion.category,
            current_text=suggestion.current_text,
            suggested_text=suggestion.suggested_text,
            predicted_score_improvement=suggestion.predicted_score_improvement,
            status="pending",
        )
        db.add(db_suggestion)

    await db.flush()

    return len(review_result.suggestions)


# =============================================================================
# GET /projects/{id}/suggestions — Get AI suggestions
# =============================================================================


@router.get(
    "/{project_id}/suggestions",
    response_model=SuccessResponse,
    summary="Get AI suggestions for a project",
    description=(
        "Retrieve AI-generated improvement suggestions for the project. "
        "Returns 3-20 items categorized by type. "
        "Suggestions with status 'dismissed' are excluded unless explicitly requested."
    ),
)
async def get_suggestions(
    request: Request,
    project_id: Annotated[uuid.UUID, Path(..., description=PROJECT_UUID_DESC)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    include_dismissed: Annotated[
        bool,
        Query(description="Include dismissed suggestions in the results"),
    ] = False,
    category: Annotated[
        str | None,
        Query(description="Filter by category (compliance|clarity|completeness|consistency)"),
    ] = None,
) -> JSONResponse:
    """Get AI suggestions for a project.

    Returns categorized suggestions (3-20 items) with:
    - Category (compliance, clarity, completeness, consistency)
    - Affected section
    - Current text and suggested replacement
    - Predicted score improvement

    Requirements: 10.1, 10.7
    """
    project = await _get_project_with_access(project_id, current_user, db)

    # Query suggestions
    suggestions_stmt = select(Suggestion).where(
        Suggestion.project_id == project_id
    )

    # Filter out dismissed unless requested
    if not include_dismissed:
        suggestions_stmt = suggestions_stmt.where(
            Suggestion.status != "dismissed"
        )

    # Apply category filter
    if category:
        valid_categories = {"compliance", "clarity", "completeness", "consistency"}
        if category not in valid_categories:
            raise ValidationError(
                message=f"ประเภทต้องเป็น: {', '.join(valid_categories)}",
                field="category",
            )
        suggestions_stmt = suggestions_stmt.where(Suggestion.category == category)

    # Order by predicted_score_improvement descending (most impactful first)
    suggestions_stmt = suggestions_stmt.order_by(
        Suggestion.predicted_score_improvement.desc()
    )

    result = await db.execute(suggestions_stmt)
    suggestions = result.scalars().all()

    # Build response
    items = [SuggestionResponse.model_validate(s) for s in suggestions]

    response_data = SuggestionListResponse(
        items=items,
        total=len(items),
        quality_score=project.quality_score,
    )

    return _build_response(request, response_data.model_dump(mode="json"))


# =============================================================================
# PUT /projects/{id}/suggestions/{sid} — Accept/dismiss a suggestion
# =============================================================================


@router.put(
    "/{project_id}/suggestions/{suggestion_id}",
    response_model=SuccessResponse,
    summary="Accept or dismiss a suggestion",
    description=(
        "Update the status of a specific suggestion to 'accepted' or 'dismissed'. "
        "When accepted, the suggested text can be applied to the relevant section."
    ),
)
async def update_suggestion(
    request: Request,
    project_id: Annotated[uuid.UUID, Path(..., description=PROJECT_UUID_DESC)],
    suggestion_id: Annotated[uuid.UUID, Path(..., description="Suggestion UUID")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: SuggestionUpdateRequest,
) -> JSONResponse:
    """Accept or dismiss an AI suggestion.

    When a suggestion is accepted:
    - The status is set to 'accepted'
    - The frontend applies the suggested text to the relevant section
    - Re-validation of the affected area should follow (Req 10.3)

    When dismissed:
    - The status is set to 'dismissed'
    - The suggestion is not re-shown unless content changes (Req 10.5)

    Requirements: 10.3, 10.5
    """
    await _get_project_with_access(project_id, current_user, db)

    # Fetch the suggestion
    suggestion_stmt = select(Suggestion).where(
        Suggestion.id == suggestion_id,
        Suggestion.project_id == project_id,
    )
    result = await db.execute(suggestion_stmt)
    suggestion = result.scalar_one_or_none()

    if suggestion is None:
        raise NotFoundError(message="ไม่พบข้อเสนอแนะที่ต้องการ")

    # Update status
    old_status = suggestion.status
    suggestion.status = body.status.value

    # If accepted, optionally apply the suggested text to the TOR section
    if body.status == SuggestionStatus.ACCEPTED:
        # Find the target TOR section
        section_stmt = select(TORSection).where(
            TORSection.project_id == project_id,
            TORSection.section_key == suggestion.section_key,
            TORSection.sub_key.is_(None),
        )
        section_result = await db.execute(section_stmt)
        section = section_result.scalar_one_or_none()

        if section:
            # Apply the suggested text by replacing current_text with suggested_text
            if suggestion.current_text and suggestion.current_text in (section.content or ""):
                section.content = section.content.replace(
                    suggestion.current_text, suggestion.suggested_text, 1
                )
            else:
                section.content = suggestion.suggested_text
            section.version += 1
            logger.info(
                "Applied suggestion %s to section %s of project %s",
                suggestion_id,
                suggestion.section_key,
                project_id,
            )

    await db.flush()

    logger.info(
        "Suggestion %s updated: %s → %s for project %s",
        suggestion_id,
        old_status,
        body.status.value,
        project_id,
    )

    response_data = SuggestionUpdateResponse(
        id=suggestion_id,
        status=body.status.value,
    )

    return _build_response(request, response_data.model_dump(mode="json"))


# =============================================================================
# POST /projects/{id}/validate — Real-time validation
# =============================================================================


@router.post(
    "/{project_id}/validate",
    response_model=SuccessResponse,
    summary="Real-time TOR validation",
    description=(
        "Run quick validation on specific sections or the full TOR. "
        "Designed for real-time feedback while editing (debounced server-side). "
        "Returns findings within 3 seconds."
    ),
)
async def validate_tor(
    request: Request,
    project_id: Annotated[uuid.UUID, Path(..., description=PROJECT_UUID_DESC)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: ValidateRequest | None = None,
) -> JSONResponse:
    """Real-time TOR validation for editing feedback.

    This endpoint is designed to be called with a debounced 3-second delay
    after the user stops typing. It provides quick Rule Engine validation
    feedback on the current content.

    If body.content is provided, it validates that content directly without
    requiring a database persist first. Otherwise, it validates the persisted
    content for the specified section or full document.

    Requirements: 10.6 (3-second debounce handled client-side, server returns within 3s)
    """
    project = await _get_project_with_access(project_id, current_user, db)

    # Build tor_document for validation
    tor_document: dict = {}

    if body and body.content and body.section_key:
        # Validate specific content (real-time, not yet persisted)
        # Still load other sections for cross-section validation
        sections_stmt = select(TORSection).where(
            TORSection.project_id == project_id
        )
        sections_result = await db.execute(sections_stmt)
        all_sections = sections_result.scalars().all()

        for section in all_sections:
            if not section.sub_key:
                tor_document[section.section_key] = section.content or ""

        # Override with the provided content for the target section
        tor_document[body.section_key] = body.content
    else:
        # Validate persisted content
        sections_stmt = select(TORSection).where(
            TORSection.project_id == project_id
        )
        sections_result = await db.execute(sections_stmt)
        all_sections = sections_result.scalars().all()

        for section in all_sections:
            if not section.sub_key:
                tor_document[section.section_key] = section.content or ""

    # Add project metadata
    tor_document["budget"] = project.budget
    tor_document["project_type"] = project.project_type

    # Run the Rule Engine
    try:
        from app.orchestrator.graph import _create_rule_engine

        engine = _create_rule_engine()
        validation_result = engine.validate(tor_document)
    except Exception as exc:
        logger.exception("Validation failed for project %s", project_id)
        raise ValidationError(
            message="การตรวจสอบล้มเหลว",
            field="validate",
            details=str(exc),
        )

    # Filter findings to the specific section if requested
    findings = validation_result.findings
    if body and body.section_key:
        findings = [
            f for f in findings
            if f.affected_section == body.section_key
        ]

    findings_response = [
        FindingResponse(
            severity=f.severity.value if hasattr(f.severity, "value") else str(f.severity),
            rule_violated=f.rule_violated,
            affected_section=f.affected_section,
            message=f.message,
            recommended_correction=f.recommended_correction,
        )
        for f in findings
    ]

    response_data = ValidateResponse(
        project_id=project_id,
        quality_score=validation_result.quality_score,
        is_valid=validation_result.is_valid,
        findings=findings_response,
    )

    return _build_response(request, response_data.model_dump(mode="json"))



# =============================================================================
# POST /projects/{id}/review/requirements — Upload custom requirements file
# =============================================================================


@router.post(
    "/{project_id}/review/requirements",
    response_model=SuccessResponse,
    summary="Upload custom requirements for review",
)
async def upload_requirements(
    request: Request,
    project_id: Annotated[uuid.UUID, Path(..., description=PROJECT_UUID_DESC)],
    file: UploadFile,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """Upload a requirements file for project-specific TOR review.

    Extracts text from the uploaded file and stores it in the project's
    custom_requirements_text field. The ReviewAgent uses this text to
    check the TOR against project-specific requirements in addition to
    standard legal compliance rules.
    """
    from pathlib import Path as FilePath

    from app.io_temp import unlink_path, write_temp_bytes
    from app.rag.extraction import extract_text

    project = await _get_project_with_access(project_id, current_user, db)

    raw = await file.read()
    if not raw:
        raise ValidationError(message="ไฟล์ว่างเปล่า", field="file")
    if len(raw) > 20 * 1024 * 1024:
        raise ValidationError(message="ไฟล์ต้องมีขนาดไม่เกิน 20 MB", field="file")

    suffix = FilePath(file.filename or "upload.bin").suffix or ".bin"
    mime = file.content_type or "application/octet-stream"
    tmp_path = await write_temp_bytes(raw, suffix)
    try:
        result = extract_text(tmp_path, mime)
        text = result.text
    except Exception as exc:
        logger.warning("Requirements extraction failed: %s", exc)
        raise ValidationError(
            message="ไม่สามารถแกะข้อความจากไฟล์ได้", field="file"
        ) from exc
    finally:
        await unlink_path(tmp_path)

    if not text or len(text.strip()) < 10:
        raise ValidationError(
            message="ไม่พบข้อความที่มีความหมายในไฟล์", field="file"
        )

    project.custom_requirements_text = text.strip()
    await db.flush()

    logger.info(
        "Custom requirements uploaded for project %s: %d chars",
        project_id,
        len(project.custom_requirements_text),
    )

    return _build_response(request, {
        "filename": file.filename,
        "chars_extracted": len(project.custom_requirements_text),
        "status": "ok",
    })


# =============================================================================
# GET /projects/{id}/review/requirements — Get current requirements info
# =============================================================================


@router.get(
    "/{project_id}/review/requirements",
    response_model=SuccessResponse,
    summary="Get uploaded requirements info",
)
async def get_requirements(
    request: Request,
    project_id: Annotated[uuid.UUID, Path(..., description=PROJECT_UUID_DESC)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """Return information about the custom requirements for this project."""
    project = await _get_project_with_access(project_id, current_user, db)

    if not project.custom_requirements_text:
        return _build_response(request, {
            "has_requirements": False,
            "chars": 0,
            "preview": None,
        })

    return _build_response(request, {
        "has_requirements": True,
        "chars": len(project.custom_requirements_text),
        "preview": project.custom_requirements_text[:500],
    })


# =============================================================================
# DELETE /projects/{id}/review/requirements — Clear custom requirements
# =============================================================================


@router.delete(
    "/{project_id}/review/requirements",
    response_model=SuccessResponse,
    summary="Clear custom requirements",
)
async def delete_requirements(
    request: Request,
    project_id: Annotated[uuid.UUID, Path(..., description=PROJECT_UUID_DESC)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JSONResponse:
    """Remove custom requirements text from the project."""
    project = await _get_project_with_access(project_id, current_user, db)
    project.custom_requirements_text = None
    await db.flush()

    return _build_response(request, {"status": "cleared"})
