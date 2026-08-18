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

from typing import Annotated

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.constants import PROJECT_NOT_FOUND, PROJECT_UUID_DESC
from app.domain.section_text import section_plain_text
from app.config import get_settings
from app.deps import get_current_user, get_db
from app.exceptions import NotFoundError, ValidationError
from app.models.project import Project
from app.models.tor_section import TORSection
from app.models.user import User
from app.rbac import require_project_access
from app.schemas.drafting import DraftSectionRequest, DraftSectionResponse
from app.schemas.responses import MetaInfo, SuccessResponse

logger = logging.getLogger("tor_app.drafting")

router = APIRouter()


def _persist_keys_for_section(section_key: str) -> tuple[str, str | None]:
    """Map s4.x / 4.x onto section_key=s4 plus a sub_key."""
    if not section_key.startswith(("s4.", "4.")):
        return section_key, None
    if section_key[0] == "s":
        return "s4", section_key
    return "s4", f"s4.{section_key[2:]}"


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

    # Gather existing section content for cross-section context
    sections_stmt = select(TORSection).where(TORSection.project_id == project_id)
    sections_result = await db.execute(sections_stmt)
    all_sections = sections_result.scalars().all()

    existing_sections: dict[str, str] = {}
    for s in all_sections:
        existing_sections[s.section_key] = section_plain_text(s.content)

    # Build user_input from project metadata and existing sections
    user_input: dict = {
        "project_name": project.name,
        "ministry": project.ministry,
        "budget": project.budget,
        "project_type": project.project_type,
        "existing_sections": existing_sections,
    }

    # Merge additional context from the request body
    if body.additional_context:
        user_input.update(body.additional_context)

    analysis = project.analysis_json or {}
    slot_map = analysis.get("slot_map") or {}
    user_input["analysis_json"] = analysis
    user_input["slot_map"] = slot_map
    target_slot = slot_map.get(target_section) or {}
    if target_slot.get("content"):
        user_input["intake_slot_content"] = target_slot.get("content")
        user_input["intake_slot_status"] = target_slot.get("status")
        user_input["intake_slot_sources"] = target_slot.get("sources")
    if target_section == "s4":
        user_input["scope_subslots"] = {
            key: slot_map.get(key)
            for key in slot_map
            if str(key).startswith("s4.")
        }

    # Get template data if project has a template
    template_data: dict = {}
    if project.template_id:
        # Template is eagerly loaded via relationship
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
            # Auto-approve for API-driven drafting (non-interactive mode)
            "human_approved": True,
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

        persist_key, persist_sub = _persist_keys_for_section(target_section)

        section_stmt = select(TORSection).where(
            TORSection.project_id == project_id,
            TORSection.section_key == persist_key,
        )
        if persist_sub:
            section_stmt = section_stmt.where(TORSection.sub_key == persist_sub)
        else:
            section_stmt = section_stmt.where(TORSection.sub_key.is_(None))
        section_result = await db.execute(section_stmt)
        section = section_result.scalar_one_or_none()

        if section:
            section.ai_draft = draft_content
            section.content = draft_content
            section.quality_score = quality_score
            section.validation_findings = (
                {"findings": validation_findings} if validation_findings else None
            )
        else:
            new_section = TORSection(
                project_id=project_id,
                section_key=persist_key,
                sub_key=persist_sub,
                content=draft_content,
                ai_draft=draft_content,
                quality_score=quality_score,
                validation_findings=(
                    {"findings": validation_findings} if validation_findings else None
                ),
                version=1,
            )
            db.add(new_section)

        if persist_key == "s4" and persist_sub is None:
            from app.domain.tor_sections import SCOPE_SUBSECTIONS

            for sub_key in SCOPE_SUBSECTIONS:
                sub_text = (slot_map.get(sub_key) or {}).get("content") or ""
                if not sub_text.strip():
                    continue
                sub_stmt = select(TORSection).where(
                    TORSection.project_id == project_id,
                    TORSection.section_key == "s4",
                    TORSection.sub_key == sub_key,
                )
                sub_row = (await db.execute(sub_stmt)).scalar_one_or_none()
                if sub_row:
                    if not (sub_row.content or "").strip():
                        sub_row.content = str(sub_text)
                else:
                    db.add(
                        TORSection(
                            project_id=project_id,
                            section_key="s4",
                            sub_key=sub_key,
                            content=str(sub_text),
                            version=1,
                        )
                    )

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
