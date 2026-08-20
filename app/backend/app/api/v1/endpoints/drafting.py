"""AI drafting endpoint: POST /projects/{id}/draft-section.

Drafts a specific TOR section by invoking the LangGraph Orchestrator which:
1. Validates input
2. Retrieves RAG context
3. Generates LLM draft
4. Validates via Rule Engine guardrail
5. Returns best draft with quality metadata

Validates: Requirements 5.1, 6.1
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.constants import PROJECT_NOT_FOUND, PROJECT_UUID_DESC
from app.config import get_settings
from app.deps import get_current_user, get_db
from app.domain.section_text import section_plain_text
from app.domain.tor_sections import SCOPE_SUBSECTIONS
from app.exceptions import NotFoundError, ValidationError
from app.llm_admission import AdmissionTimeoutError, admit
from app.models.project import Project
from app.models.tor_section import TORSection
from app.models.user import User
from app.rate_limiter import rate_limit_ai
from app.rbac import require_project_access
from app.schemas.drafting import DraftSectionRequest, DraftSectionResponse
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.intake_service import slot_content

logger = logging.getLogger("tor_app.drafting")

router = APIRouter()


def _persist_keys_for_section(section_key: str) -> tuple[str, str | None]:
    """Map s4.x / 4.x onto section_key=s4 plus a sub_key."""
    if not section_key.startswith(("s4.", "4.")):
        return section_key, None
    if section_key[0] == "s":
        return "s4", section_key
    return "s4", f"s4.{section_key[2:]}"


def _as_slot_map(analysis: object) -> dict:
    if not isinstance(analysis, dict):
        return {}
    raw = analysis.get("slot_map") or {}
    return raw if isinstance(raw, dict) else {}


def _user_input_for_draft(
    project: Project,
    all_sections: list[TORSection],
    body: DraftSectionRequest,
    slot_map: dict,
    analysis: dict,
) -> dict:
    existing_sections = {
        section.section_key: section_plain_text(section.content) for section in all_sections
    }
    user_input: dict = {
        "project_name": project.name,
        "ministry": project.ministry,
        "budget": project.budget,
        "project_type": project.project_type,
        "existing_sections": existing_sections,
    }
    if body.additional_context:
        user_input.update(body.additional_context)
    user_input["analysis_json"] = analysis
    user_input["slot_map"] = slot_map
    target_slot = slot_map.get(body.section_key) or {}
    if isinstance(target_slot, dict) and target_slot.get("content"):
        user_input["intake_slot_content"] = target_slot.get("content")
        user_input["intake_slot_status"] = target_slot.get("status")
        user_input["intake_slot_sources"] = target_slot.get("sources")
    if body.section_key == "s4":
        user_input["scope_subslots"] = {
            key: slot_map.get(key) for key in slot_map if str(key).startswith("s4.")
        }
    return user_input


def _template_payload(project: Project) -> dict:
    if not project.template_id or not project.template:
        return {}
    return {
        "section_structure": project.template.section_structure or {},
        "placeholder_guidance": project.template.placeholder_guidance or {},
    }


def _draft_from_state(final_state: dict) -> tuple:
    draft_content = final_state.get("draft_content", "")
    quality_score = final_state.get("quality_score")
    validation_findings = final_state.get("validation_findings", [])
    rag_failed = final_state.get("rag_retrieval_failed", False)
    error = final_state.get("error")
    if final_state.get("best_draft_content") and not draft_content:
        return (
            final_state["best_draft_content"],
            final_state.get("best_draft_score"),
            final_state.get("best_draft_findings", []),
            rag_failed,
            error,
        )
    return draft_content, quality_score, validation_findings, rag_failed, error


async def _save_draft_section(
    db: AsyncSession,
    project_id: uuid.UUID,
    persist_key: str,
    persist_sub: str | None,
    draft_content: str,
    quality_score,
    validation_findings,
) -> None:
    findings_json = {"findings": validation_findings} if validation_findings else None
    section_stmt = select(TORSection).where(
        TORSection.project_id == project_id,
        TORSection.section_key == persist_key,
    )
    if persist_sub:
        section_stmt = section_stmt.where(TORSection.sub_key == persist_sub)
    else:
        section_stmt = section_stmt.where(TORSection.sub_key.is_(None))
    section = (await db.execute(section_stmt)).scalar_one_or_none()
    if section:
        section.ai_draft = draft_content
        section.content = draft_content
        section.quality_score = quality_score
        section.validation_findings = findings_json
        return
    db.add(
        TORSection(
            project_id=project_id,
            section_key=persist_key,
            sub_key=persist_sub,
            content=draft_content,
            ai_draft=draft_content,
            quality_score=quality_score,
            validation_findings=findings_json,
            version=1,
        )
    )


async def _fill_empty_s4_subs(
    db: AsyncSession, project_id: uuid.UUID, slot_map: dict
) -> None:
    for sub_key in SCOPE_SUBSECTIONS:
        sub_text = slot_content(slot_map, sub_key)
        if not sub_text.strip():
            continue
        sub_stmt = select(TORSection).where(
            TORSection.project_id == project_id,
            TORSection.section_key == "s4",
            TORSection.sub_key == sub_key,
        )
        sub_row = (await db.execute(sub_stmt)).scalar_one_or_none()
        if not sub_row:
            db.add(
                TORSection(
                    project_id=project_id,
                    section_key="s4",
                    sub_key=sub_key,
                    content=sub_text,
                    version=1,
                )
            )
            continue
        if not (sub_row.content or "").strip():
            sub_row.content = sub_text


# =============================================================================
# POST /projects/{id}/draft-section — Draft a specific TOR section
# =============================================================================


@router.post(
    "/{project_id}/draft-section",
    response_model=SuccessResponse,
    summary="Draft a specific TOR section",
    description=(
        "Invoke the AI Orchestrator to draft a specific TOR section. "
        "Uses RAG context retrieval + LLM + Rule Engine guardrail. "
        "Returns the generated draft with quality score."
    ),
    dependencies=[Depends(rate_limit_ai)],
)
async def draft_section(
    request: Request,
    project_id: Annotated[uuid.UUID, Path(..., description=PROJECT_UUID_DESC)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    body: DraftSectionRequest,
) -> JSONResponse:
    """Draft a specific TOR section via the Orchestrator.

    The orchestrator workflow:
    - validate_input → retrieve_context → llm_draft → rule_guardrail
    - If guardrail passes (score >= 70): returns draft
    - If fails: retries up to 3 times with feedback, then returns best draft

    Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
    """
    # Verify project exists and user has access
    stmt = select(Project).where(Project.id == project_id)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)

    require_project_access(project.owner_id, current_user)

    target_section = body.section_key
    all_sections = (
        await db.execute(select(TORSection).where(TORSection.project_id == project_id))
    ).scalars().all()
    analysis = project.analysis_json if isinstance(project.analysis_json, dict) else {}
    slot_map = _as_slot_map(analysis)
    user_input = _user_input_for_draft(project, list(all_sections), body, slot_map, analysis)
    template_data = _template_payload(project)

    try:
        from app.orchestrator import compile_tor_drafting_graph

        request_id = (
            request.headers.get("X-AI-Request-Id") or str(uuid.uuid4())
        ).strip()
        redis = getattr(request.app.state, "redis", None)
        async with admit(redis, "llm", request_id):
            final_state = await compile_tor_drafting_graph().ainvoke(
                {
                    "project_id": str(project_id),
                    "user_input": user_input,
                    "template": template_data,
                    "target_section": target_section,
                    "max_retries": 3,
                    "agent_timeout_seconds": get_settings().drafting_agent_timeout_seconds(),
                    "human_approved": True,
                }
            )
        draft_content, quality_score, validation_findings, rag_failed, error = _draft_from_state(
            final_state
        )
        if error and not draft_content:
            raise ValidationError(
                message=f"การสร้างร่างล้มเหลว: {error}",
                field="draft",
            )
        persist_key, persist_sub = _persist_keys_for_section(target_section)
        await _save_draft_section(
            db,
            project_id,
            persist_key,
            persist_sub,
            draft_content,
            quality_score,
            validation_findings,
        )
        if persist_key == "s4" and persist_sub is None:
            await _fill_empty_s4_subs(db, project_id, slot_map)
        await db.flush()
        logger.info(
            "Draft generated for project %s, section %s, score=%s",
            project_id,
            target_section,
            quality_score,
        )

    except ValidationError:
        raise
    except AdmissionTimeoutError as exc:
        raise ValidationError(message=str(exc), field="draft") from exc
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
    response_data = DraftSectionResponse(
        project_id=project_id,
        section_key=target_section,
        draft_content=draft_content,
        quality_score=quality_score,
        validation_findings=validation_findings,
        rag_retrieval_failed=rag_failed,
    )

    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    response = SuccessResponse(
        ok=True,
        data=response_data.model_dump(mode="json"),
        meta=MetaInfo(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )

    return JSONResponse(
        status_code=200,
        content=response.model_dump(mode="json"),
    )
