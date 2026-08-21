"""Chat-driven TOR drafting endpoints (Phase 3).

POST /projects/{id}/draft-chat/start — auto-draft all 13 sections (SSE stream)
POST /projects/{id}/draft-chat/message — edit/accept/redraft via chat (SSE stream)
GET  /projects/{id}/draft-chat/status — drafting progress
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Annotated, Any, AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.domain.tor_sections import TOR_SECTION_LABELS, TOR_SECTION_ORDER
from app.exceptions import NotFoundError, ValidationError
from app.llm_admission import AdmissionTimeoutError, admit
from app.models.project import Project
from app.models.tor_section import TORSection
from app.models.user import User
from app.rate_limiter import rate_limit_ai
from app.rbac import require_project_access
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.draft_chat_service import (
    draft_single_section,
    edit_section_draft,
    parse_draft_message_intent,
)
from app.services.intake_service import is_ready_to_compose, slot_map_of

logger = logging.getLogger("tor_app.draft_chat")
router = APIRouter()


class DraftChatMessageBody(BaseModel):
    content: str = Field(..., min_length=1)
    section_key: str | None = None


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _ok(request: Request, data: Any) -> JSONResponse:
    payload = SuccessResponse(
        ok=True,
        data=data,
        meta=MetaInfo(
            request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
            timestamp="",
        ),
    )
    return JSONResponse(content=payload.model_dump(mode="json"))


async def _project(db: AsyncSession, project_id: uuid.UUID, user: User) -> Project:
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if project is None:
        raise NotFoundError(message="ไม่พบโครงการ")
    require_project_access(project.owner_id, user)
    return project


async def _get_section(db: AsyncSession, project_id: uuid.UUID, key: str) -> TORSection | None:
    return (
        await db.execute(
            select(TORSection).where(
                TORSection.project_id == project_id,
                TORSection.section_key == key,
                TORSection.sub_key.is_(None),
            )
        )
    ).scalar_one_or_none()


async def _save_section(db: AsyncSession, project_id: uuid.UUID, key: str, content: str) -> None:
    row = await _get_section(db, project_id, key)
    if row is None:
        db.add(
            TORSection(
                project_id=project_id,
                section_key=key,
                content=content,
                ai_draft=content,
                version=1,
            )
        )
        return
    row.content = content
    row.ai_draft = content


@router.post("/{project_id}/draft-chat/start", dependencies=[Depends(rate_limit_ai)])
async def start_draft_chat(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Auto-draft all 13 TOR sections. Streams SSE events per section."""
    project = await _project(db, project_id, current_user)
    if not is_ready_to_compose(project):
        raise ValidationError(
            message="ต้องยืนยันพร้อมร่าง (confirm-ready) ก่อนจึงจะเริ่มร่างได้"
        )
    slot_map = slot_map_of(project)
    request_id = (
        request.headers.get("X-AI-Request-Id") or str(uuid.uuid4())
    ).strip()
    session_factory = request.app.state.db_session_factory

    async def generate() -> AsyncIterator[str]:
        import asyncio

        redis = getattr(request.app.state, "redis", None)
        drafted_count = 0

        for section_key in TOR_SECTION_ORDER:
            label = TOR_SECTION_LABELS.get(section_key, section_key)
            yield _sse(
                "section_start",
                {
                    "section_key": section_key,
                    "title": label,
                    "index": TOR_SECTION_ORDER.index(section_key),
                    "total": len(TOR_SECTION_ORDER),
                },
            )

            parts: list[str] = []
            try:
                async with admit(redis, "llm", f"{request_id}-{section_key}"):
                    async for token in draft_single_section(
                        section_key, slot_map, user_id=current_user.id
                    ):
                        parts.append(token)
                        yield _sse("token", {"section_key": section_key, "text": token})
            except AdmissionTimeoutError:
                yield _sse(
                    "section_error",
                    {"section_key": section_key, "message": "หมดเวลารอคิว LLM"},
                )
                continue
            except Exception as exc:
                logger.exception("Draft failed for %s", section_key)
                yield _sse(
                    "section_error",
                    {"section_key": section_key, "message": str(exc)[:200]},
                )
                continue

            full_text = "".join(parts)
            # Save to database
            async with session_factory() as persist:
                await _save_section(persist, project_id, section_key, full_text)
                await persist.commit()

            drafted_count += 1
            yield _sse(
                "section_done",
                {
                    "section_key": section_key,
                    "title": label,
                    "content": full_text,
                    "drafted_count": drafted_count,
                    "total": len(TOR_SECTION_ORDER),
                },
            )
            # Small pause between sections to not overwhelm LM Studio
            await asyncio.sleep(0.5)

        yield _sse(
            "all_done",
            {"drafted_count": drafted_count, "total": len(TOR_SECTION_ORDER)},
        )

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/{project_id}/draft-chat/message", dependencies=[Depends(rate_limit_ai)])
async def draft_chat_message(
    request: Request,
    project_id: uuid.UUID,
    body: DraftChatMessageBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Handle user message: accept, edit, redraft, or freeform feedback."""
    project = await _project(db, project_id, current_user)
    slot_map = slot_map_of(project)
    intent, target_key, detail = parse_draft_message_intent(body.content)
    # Use explicit section_key from body if provided
    section_key = body.section_key or target_key
    request_id = (
        request.headers.get("X-AI-Request-Id") or str(uuid.uuid4())
    ).strip()
    session_factory = request.app.state.db_session_factory

    async def generate() -> AsyncIterator[str]:
        redis = getattr(request.app.state, "redis", None)

        if intent == "accept":
            yield _sse("accepted", {"section_key": section_key, "message": "ยอมรับแล้ว"})
            return

        # For edit/redraft/freeform — need to re-draft the section
        if not section_key:
            yield _sse(
                "error",
                {"message": "กรุณาระบุหมวดที่ต้องการแก้ไข เช่น 'ร่างใหม่ หมวด 1'"},
            )
            return

        label = TOR_SECTION_LABELS.get(section_key, section_key)
        yield _sse(
            "section_start",
            {"section_key": section_key, "title": label, "intent": intent},
        )

        # Load current draft for edit context
        current_draft = ""
        async with session_factory() as read_session:
            row = await _get_section(read_session, project_id, section_key)
            if row:
                current_draft = row.content or ""

        parts: list[str] = []
        try:
            async with admit(redis, "llm", request_id):
                if intent in ("edit", "freeform") and current_draft:
                    stream = edit_section_draft(
                        section_key, current_draft, detail, slot_map
                    )
                else:
                    stream = draft_single_section(
                        section_key, slot_map, user_id=current_user.id
                    )
                async for token in stream:
                    parts.append(token)
                    yield _sse("token", {"section_key": section_key, "text": token})
        except AdmissionTimeoutError:
            yield _sse("error", {"message": "หมดเวลารอคิว LLM"})
            return
        except Exception as exc:
            logger.exception("Draft chat message failed for %s", section_key)
            yield _sse("error", {"message": str(exc)[:200]})
            return

        full_text = "".join(parts)
        # Save updated draft
        async with session_factory() as persist:
            await _save_section(persist, project_id, section_key, full_text)
            await persist.commit()

        yield _sse(
            "section_done",
            {
                "section_key": section_key,
                "title": label,
                "content": full_text,
                "intent": intent,
            },
        )

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/{project_id}/draft-chat/status")
async def draft_chat_status(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Get current drafting progress."""
    await _project(db, project_id, current_user)
    sections = (
        await db.execute(
            select(TORSection).where(
                TORSection.project_id == project_id,
                TORSection.sub_key.is_(None),
            )
        )
    ).scalars().all()
    section_map = {s.section_key: s for s in sections}
    status_list = []
    drafted_count = 0
    for key in TOR_SECTION_ORDER:
        row = section_map.get(key)
        has_content = bool(row and (row.content or "").strip())
        if has_content:
            drafted_count += 1
        status_list.append(
            {
                "section_key": key,
                "title": TOR_SECTION_LABELS.get(key, key),
                "has_content": has_content,
                "content_preview": (row.content or "")[:200] if row else "",
                "human_confirmed": bool(row.is_approved) if row else False,
            }
        )
    return _ok(
        request,
        {
            "sections": status_list,
            "drafted_count": drafted_count,
            "total": len(TOR_SECTION_ORDER),
            "all_drafted": drafted_count == len(TOR_SECTION_ORDER),
        },
    )
