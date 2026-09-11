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
from app.export.table_parse import split_scope_subsection_draft
from app.llm_admission import AdmissionTimeoutError, admit
from app.models.project import Project
from app.models.tor_section import TORSection
from app.models.user import User
from app.rate_limiter import rate_limit_ai
from app.rbac import require_project_access
from app.schemas.drafting import DraftSectionRequest, DraftSectionResponse
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.thai_draft import scope_overview_from_subs

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
        section.section_key: section_plain_text(section.content, section.section_key)
        for section in all_sections
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
    feedback = str(
        user_input.get("user_feedback") or user_input.get("human_feedback") or ""
    ).strip()
    if feedback:
        user_input["user_feedback"] = feedback
        user_input["human_feedback"] = feedback
        user_input["redraft"] = True
        prior_rev = str(user_input.get("revision_instruction") or "").strip()
        guided = (
            "แก้ไขเฉพาะหมวด/หัวข้อนี้เท่านั้นตามความคิดเห็นผู้ใช้ "
            "ส่งร่างใหม่ทั้งก้อนของหมวดนี้ ห้ามแก้หมวดอื่น "
            f"ความคิดเห็น: {feedback}"
        )
        user_input["revision_instruction"] = (
            f"{guided}\n{prior_rev}".strip() if prior_rev else guided
        )
    elif user_input.get("redraft"):
        force = (
            "ต้องเขียนร่างใหม่ให้ต่างจากร่างเดิมอย่างมีสาระ "
            "ห้ามคืนข้อความเดิมทั้งก้อนหรือแก้เพียงเล็กน้อย "
            "คงสาระที่ผู้ใช้แก้แล้วไว้ และเติมส่วนที่ยังว่างจากเอกสารขั้นที่ ๐"
        )
        prior = str(user_input.get("revision_instruction") or "").strip()
        user_input["revision_instruction"] = f"{force}\n{prior}".strip() if prior else force
    user_input["analysis_json"] = analysis
    user_input["slot_map"] = slot_map
    target_slot = slot_map.get(body.section_key) or {}
    if isinstance(target_slot, dict) and target_slot.get("content"):
        user_input["intake_slot_content"] = target_slot.get("content")
        user_input["intake_slot_status"] = target_slot.get("status")
        user_input["intake_slot_sources"] = target_slot.get("sources")
    if body.section_key == "s4":
        from app.domain.section_profile import profile_for_project

        keys = profile_for_project(project.project_type).scope_storage_keys()
        user_input["scope_subslots"] = {
            key: slot_map.get(key) for key in keys if slot_map.get(key)
        }
        user_input["scope_subslots"].update(
            {
                key: slot_map.get(key)
                for key in slot_map
                if str(key).startswith("s4.")
            }
        )
    return user_input


def _template_payload(project: Project) -> dict:
    if not project.template_id:
        return {}
    # Must not lazy-load here — async sessions raise MissingGreenlet.
    template = project.__dict__.get("template")
    if template is None:
        return {}
    return {
        "section_structure": template.section_structure or {},
        "placeholder_guidance": template.placeholder_guidance or {},
    }


async def _load_project_for_draft(
    db: AsyncSession, project_id: uuid.UUID, current_user: User
) -> Project:
    from sqlalchemy.orm import selectinload

    project = (
        await db.execute(
            select(Project)
            .options(selectinload(Project.template))
            .where(Project.id == project_id)
        )
    ).scalar_one_or_none()
    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)
    require_project_access(project.owner_id, current_user)
    return project


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
        from app.domain.section_fields import persist_section_fields

        draft_content = persist_section_fields(persist_key, draft_content)
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


async def _persist_s4_from_draft(
    db: AsyncSession,
    project_id: uuid.UUID,
    draft_content: str,
    quality_score,
    validation_findings,
    _slot_map: dict,
) -> str:
    """Split AI s4 blob into subsections; keep short overview at top level."""
    parts = split_scope_subsection_draft(draft_content)
    if not parts:
        await _save_draft_section(
            db,
            project_id,
            "s4",
            None,
            draft_content,
            quality_score,
            validation_findings,
        )
        return draft_content
    for sub_key, body in parts.items():
        if sub_key not in SCOPE_SUBSECTIONS:
            continue
        text = (body or "").strip()
        if text:
            await _save_draft_section(
                db,
                project_id,
                "s4",
                sub_key,
                text,
                quality_score,
                validation_findings,
            )
    overview = scope_overview_from_subs(parts)
    await _save_draft_section(
        db,
        project_id,
        "s4",
        None,
        overview,
        quality_score,
        validation_findings,
    )
    return overview


async def _invoke_draft_graph(
    request: Request,
    project_id: uuid.UUID,
    user_input: dict,
    template_data: dict,
    target_section: str,
) -> dict:
    from app.orchestrator import compile_tor_drafting_graph

    request_id = (request.headers.get("X-AI-Request-Id") or str(uuid.uuid4())).strip()
    redis = getattr(request.app.state, "redis", None)
    feedback = str(
        user_input.get("user_feedback")
        or user_input.get("human_feedback")
        or ""
    ).strip()
    async with admit(redis, "llm", request_id):
        return await compile_tor_drafting_graph().ainvoke(
            {
                "project_id": str(project_id),
                "user_input": user_input,
                "template": template_data,
                "target_section": target_section,
                "max_retries": 3,
                "agent_timeout_seconds": get_settings().drafting_agent_timeout_seconds(),
                "human_approved": True,
                "human_feedback": feedback or None,
            }
        )


async def _existing_s4_subs(db: AsyncSession, project_id: uuid.UUID) -> dict[str, str]:
    existing: dict[str, str] = {}
    for sub_key in SCOPE_SUBSECTIONS:
        sub_row = (
            await db.execute(
                select(TORSection).where(
                    TORSection.project_id == project_id,
                    TORSection.section_key == "s4",
                    TORSection.sub_key == sub_key,
                )
            )
        ).scalar_one_or_none()
        if sub_row and (sub_row.content or "").strip():
            existing[sub_key] = sub_row.content or ""
    return existing


async def _fill_missing_s4_subs(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    slot_map: dict,
    quality_score,
    validation_findings,
) -> str | None:
    from app.services.draft_chat_service import collect_scope_subsection_drafts

    existing_subs = await _existing_s4_subs(db, project_id)
    missing = [key for key in SCOPE_SUBSECTIONS if not existing_subs.get(key, "").strip()]
    if not missing:
        return None
    filled = await collect_scope_subsection_drafts(
        slot_map,
        user_id=user_id,
        only_missing=True,
        existing=existing_subs,
    )
    for sub_key, text in filled.items():
        if not (text or "").strip():
            continue
        await _save_draft_section(
            db, project_id, "s4", sub_key, text, quality_score, None
        )
        existing_subs[sub_key] = text
    overview = scope_overview_from_subs(existing_subs)
    if not overview.strip():
        return None
    await _save_draft_section(
        db,
        project_id,
        "s4",
        None,
        overview,
        quality_score,
        validation_findings,
    )
    return overview


async def _persist_draft_output(
    db: AsyncSession,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    target_section: str,
    draft_content: str,
    quality_score,
    validation_findings,
    slot_map: dict,
) -> str:
    persist_key, persist_sub = _persist_keys_for_section(target_section)
    if persist_key == "s4" and persist_sub is None:
        draft_content = await _persist_s4_from_draft(
            db,
            project_id,
            draft_content,
            quality_score,
            validation_findings,
            slot_map,
        )
        overview = await _fill_missing_s4_subs(
            db,
            project_id,
            user_id,
            slot_map,
            quality_score,
            validation_findings,
        )
        return overview or draft_content
    await _save_draft_section(
        db,
        project_id,
        persist_key,
        persist_sub,
        draft_content,
        quality_score,
        validation_findings,
    )
    return draft_content


def _focus_sub_key(body: DraftSectionRequest) -> str | None:
    """Resolve a single scope subsection to draft (never the whole s4 blob)."""
    from app.domain.section_profile import is_scope_storage_key

    ctx = body.additional_context if isinstance(body.additional_context, dict) else {}
    focus = str(ctx.get("focus_sub_key") or "").strip()
    if focus and (is_scope_storage_key(focus) or focus.startswith("s4.")):
        return focus
    key = (body.section_key or "").strip()
    if key != "s4" and (is_scope_storage_key(key) or key.startswith("s4.")):
        return key
    return None


def _user_feedback_from_body(body: DraftSectionRequest) -> str:
    ctx = body.additional_context if isinstance(body.additional_context, dict) else {}
    return str(
        ctx.get("user_feedback")
        or ctx.get("human_feedback")
        or ""
    ).strip()


def _inject_focus_draft_into_slots(
    slot_map: dict,
    focus_sub: str,
    body: DraftSectionRequest,
) -> dict:
    """Prefer the editor text for the focused sub over stale analysis slots."""
    out = dict(slot_map or {})
    ctx = body.additional_context if isinstance(body.additional_context, dict) else {}
    fields = ctx.get("current_draft_fields")
    text = ""
    if isinstance(fields, dict):
        text = str(fields.get(focus_sub) or fields.get("body") or "").strip()
        if not text and len(fields) == 1:
            text = str(next(iter(fields.values())) or "").strip()
    if not text:
        text = str(ctx.get("current_draft") or "").strip()
    if text:
        out[focus_sub] = {
            "content": text,
            "status": "filled",
            "sources": ["editor_redraft"],
        }
    return out


async def _draft_focused_scope_subsection(
    db: AsyncSession,
    request: Request,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    project: Project,
    body: DraftSectionRequest,
    focus_sub: str,
    slot_map: dict,
) -> tuple[str, float | None, list, bool]:
    """Draft and persist exactly one scope subsection."""
    from app.domain.section_profile import subsection_title
    from app.services.draft_chat_service import draft_scope_subsection
    from app.services.thai_draft import (
        is_scope_content_wrong_owner,
        normalize_license_ict_table,
        polish_scope_subsection_draft,
        scope_overview_from_subs,
        scope_subsection_fallback_draft,
    )

    focus_key = focus_sub.removeprefix("scope.").strip()
    label = subsection_title(focus_sub, project.project_type, focus_sub)
    focused_slots = _inject_focus_draft_into_slots(slot_map, focus_sub, body)
    user_feedback = _user_feedback_from_body(body)
    prior = str((focused_slots.get(focus_sub) or {}).get("content") or "").strip()
    if not prior:
        ctx = body.additional_context if isinstance(body.additional_context, dict) else {}
        prior = str(ctx.get("current_draft") or "").strip()

    # Never feed a wrong-owner draft back to the model for ANY subsection.
    prior_for_llm = prior
    if prior and is_scope_content_wrong_owner(focus_key, prior):
        logger.warning(
            "Discarding wrong-owner draft for %s (%s chars) before focused redraft",
            focus_key,
            len(prior),
        )
        prior_for_llm = ""
        focused_slots.pop(focus_sub, None)
        ownership_fix = (
            f"ร่างเดิมผิดหัวข้อสำหรับ «{label}» — ห้ามคัดลอก "
            "ต้องเขียนใหม่เฉพาะสาระของหัวข้อนี้ "
            "จัดลำดับเป็น 1. / 1.1 / 1.2 เท่านั้น"
        )
        user_feedback = (
            f"{user_feedback}\n{ownership_fix}".strip()
            if user_feedback
            else ownership_fix
        )

    # Licenses without user feedback: deterministic table rebuild is enough.
    if focus_key in {"licenses", "s4.5"} and not user_feedback:
        source = prior_for_llm or prior
        if not source or is_scope_content_wrong_owner(focus_key, source):
            from app.services.intake_service import slot_content

            source = (
                slot_content(focused_slots, focus_sub).strip()
                or slot_content(focused_slots, "licenses").strip()
                or slot_content(focused_slots, "_project_intake").strip()[:8000]
            )
        normalized = normalize_license_ict_table(source)
        if normalized.startswith("|") and "รายการ" in normalized and "\n| " in normalized:
            text = polish_scope_subsection_draft(normalized, focus_sub)
            if text:
                await _save_draft_section(
                    db, project_id, "s4", focus_sub, text, 80.0, []
                )
                existing = await _existing_s4_subs(db, project_id)
                existing[focus_sub] = text
                overview = scope_overview_from_subs(existing, project.project_type)
                if overview.strip():
                    await _save_draft_section(
                        db, project_id, "s4", None, overview, 80.0, []
                    )
                return text, 80.0, [], False

    request_id = (request.headers.get("X-AI-Request-Id") or str(uuid.uuid4())).strip()
    redis = getattr(request.app.state, "redis", None)
    parts: list[str] = []
    async with admit(redis, "llm", request_id):
        async for token in draft_scope_subsection(
            focus_sub,
            focused_slots,
            user_id=user_id,
            category=project.project_type,
            current_draft=prior_for_llm or None,
            user_feedback=user_feedback or None,
        ):
            parts.append(token)
    text = polish_scope_subsection_draft("".join(parts).strip(), focus_sub)
    if not text or is_scope_content_wrong_owner(focus_key, text):
        logger.warning(
            "Scope sub %s empty or wrong-owner after LLM; using fallback outline",
            focus_key,
        )
        text = scope_subsection_fallback_draft(focus_key, label, user_feedback)
    if not text:
        raise ValidationError(
            message=f"การสร้างร่างหัวข้อย่อย «{label}» ได้ข้อความว่าง",
            field="draft",
        )
    await _save_draft_section(
        db, project_id, "s4", focus_sub, text, 80.0, []
    )
    existing = await _existing_s4_subs(db, project_id)
    existing[focus_sub] = text
    overview = scope_overview_from_subs(existing, project.project_type)
    if overview.strip():
        await _save_draft_section(
            db, project_id, "s4", None, overview, 80.0, []
        )
    return text, 80.0, [], False


def _draft_ok_response(
    request: Request,
    project_id: uuid.UUID,
    target_section: str,
    draft_content: str,
    quality_score,
    validation_findings,
    rag_failed: bool,
) -> JSONResponse:
    response = SuccessResponse(
        ok=True,
        data=DraftSectionResponse(
            project_id=project_id,
            section_key=target_section,
            draft_content=draft_content,
            quality_score=quality_score,
            validation_findings=validation_findings,
            rag_retrieval_failed=rag_failed,
        ).model_dump(mode="json"),
        meta=MetaInfo(
            request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )
    return JSONResponse(status_code=200, content=response.model_dump(mode="json"))


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
    project = await _load_project_for_draft(db, project_id, current_user)
    target_section = body.section_key
    focus_sub = _focus_sub_key(body)
    analysis = project.analysis_json if isinstance(project.analysis_json, dict) else {}
    from app.services.intake_service import with_project_intake

    slot_map = with_project_intake(_as_slot_map(analysis), project)

    try:
        if focus_sub:
            # One subsection only — never re-run the whole s4 mother draft.
            draft_content, quality_score, validation_findings, rag_failed = (
                await _draft_focused_scope_subsection(
                    db,
                    request,
                    project_id,
                    current_user.id,
                    project,
                    body,
                    focus_sub,
                    slot_map,
                )
            )
            target_section = focus_sub
            await db.flush()
            logger.info(
                "Focused scope draft for project %s, sub=%s, score=%s",
                project_id,
                focus_sub,
                quality_score,
            )
        else:
            all_sections = (
                await db.execute(
                    select(TORSection).where(TORSection.project_id == project_id)
                )
            ).scalars().all()
            user_input = _user_input_for_draft(
                project, list(all_sections), body, slot_map, analysis
            )
            template_data = _template_payload(project)
            final_state = await _invoke_draft_graph(
                request, project_id, user_input, template_data, target_section
            )
            draft_content, quality_score, validation_findings, rag_failed, error = (
                _draft_from_state(final_state)
            )
            if not str(draft_content or "").strip():
                raise ValidationError(
                    message=f"การสร้างร่างล้มเหลว: {error or 'โมเดลส่งร่างว่าง'}",
                    field="draft",
                )
            draft_content = await _persist_draft_output(
                db,
                project_id,
                current_user.id,
                target_section,
                draft_content,
                quality_score,
                validation_findings,
                slot_map,
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

    return _draft_ok_response(
        request,
        project_id,
        target_section,
        draft_content,
        quality_score,
        validation_findings,
        rag_failed,
    )
