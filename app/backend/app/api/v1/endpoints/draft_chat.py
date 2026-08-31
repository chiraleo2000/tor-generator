"""Chat-driven TOR drafting endpoints (Phase 3).

POST /projects/{id}/draft-chat/start — auto-draft all 13 sections (SSE stream)
POST /projects/{id}/draft-chat/message — edit/accept/redraft via chat (SSE stream)
GET  /projects/{id}/draft-chat/status — drafting progress

หมวดขอบเขตงาน (s4) บันทึกลงหัวข้อย่อย s4.1–s4.14 โดยตรง
ส่วนหัวข้อหลักเก็บเฉพาะสรุปสั้น ๆ เพื่อไม่ให้ซ้ำตอนส่งออกขั้นที่ ๔
"""

from __future__ import annotations

import asyncio
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
from app.domain.tor_sections import (
    SCOPE_SUBSECTIONS,
    TOR_SECTION_LABELS,
    TOR_SECTION_ORDER,
)
from app.draft_job_store import bump_progress, get_job, mark_status, set_job
from app.exceptions import NotFoundError, ValidationError
from app.export.table_parse import split_scope_subsection_draft
from app.llm_admission import AdmissionTimeoutError, admit
from app.models.project import Project
from app.models.tor_section import TORSection
from app.models.user import User
from app.rate_limiter import rate_limit_ai
from app.rbac import require_project_access
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.draft_chat_service import (
    build_merged_scope,
    build_scope_overview,
    draft_scope_subsection,
    draft_single_section,
    edit_section_draft,
    parse_draft_message_intent,
)
from app.services.intake_service import is_ready_to_compose, slot_map_of, with_project_intake

logger = logging.getLogger("tor_app.draft_chat")
router = APIRouter()
_DRAFT_JOBS: dict[str, asyncio.Task[int]] = {}
SECTION_TIMEOUT_SECONDS = 1800


async def _consume_sse(events: AsyncIterator[str]) -> int:
    count = 0
    async for _event in events:
        count += 1
    return count


class DraftChatMessageBody(BaseModel):
    content: str = Field(..., min_length=1)
    section_key: str | None = None


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _section_done_event(section_key: str, label: str, content: str, drafted_count: int) -> str:
    return _sse(
        "section_done",
        {
            "section_key": section_key,
            "title": label,
            "content": content,
            "drafted_count": drafted_count,
            "total": len(TOR_SECTION_ORDER),
        },
    )


def _s4_ai_map(rows: list[TORSection]) -> dict[str, str]:
    return {
        row.sub_key: (row.ai_draft or row.content or "").strip()
        for row in rows
        if row.sub_key and str(row.ai_draft or row.content or "").strip()
    }


def _s4_complete(drafted: dict[str, str]) -> bool:
    return all(str(drafted.get(key) or "").strip() for key in SCOPE_SUBSECTIONS)


async def _existing_section_text(
    session_factory: Any,
    project_id: uuid.UUID,
    section_key: str,
) -> str | None:
    async with session_factory() as persist:
        if section_key == "s4":
            drafted = _s4_ai_map(await _load_s4_rows(persist, project_id))
            if _s4_complete(drafted):
                return build_merged_scope(drafted)
            return None
        row = await _get_section(persist, project_id, section_key)
        if row is None or not str(row.ai_draft or "").strip():
            return None
        text = (row.content or row.ai_draft or "").strip()
    return text or None


async def _iter_llm_section_sse(
    redis: Any,
    request_id: str,
    section_key: str,
    slot_map: dict[str, Any],
    user_id: uuid.UUID,
    parts: list[str],
    errors: list[str],
) -> AsyncIterator[str]:
    try:
        async with admit(redis, "llm", f"{request_id}-{section_key}"):
            async for token in draft_single_section(
                section_key, slot_map, user_id=user_id
            ):
                parts.append(token)
                yield _sse("token", {"section_key": section_key, "text": token})
    except AdmissionTimeoutError:
        errors.append("หมดเวลารอคิวโมเดลภาษา")
        yield _sse(
            "section_error",
            {"section_key": section_key, "message": errors[-1]},
        )
    except Exception as exc:
        logger.exception("Draft failed for %s", section_key)
        errors.append(str(exc)[:200])
        yield _sse(
            "section_error",
            {"section_key": section_key, "message": errors[-1]},
        )


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


async def _load_s4_rows(db: AsyncSession, project_id: uuid.UUID) -> list[TORSection]:
    return list(
        (
            await db.execute(
                select(TORSection).where(
                    TORSection.project_id == project_id,
                    TORSection.section_key == "s4",
                    TORSection.sub_key.is_not(None),
                )
            )
        ).scalars().all()
    )


async def _load_s4_subs(db: AsyncSession, project_id: uuid.UUID) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in await _load_s4_rows(db, project_id):
        if row.sub_key:
            out[row.sub_key] = row.content or ""
    return out


async def _upsert_sub(
    db: AsyncSession, project_id: uuid.UUID, sub_key: str, content: str
) -> None:
    row = (
        await db.execute(
            select(TORSection).where(
                TORSection.project_id == project_id,
                TORSection.section_key == "s4",
                TORSection.sub_key == sub_key,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        db.add(
            TORSection(
                project_id=project_id,
                section_key="s4",
                sub_key=sub_key,
                content=content,
                ai_draft=content,
                version=1,
            )
        )
        return
    row.content = content
    row.ai_draft = content


async def _save_section(db: AsyncSession, project_id: uuid.UUID, key: str, content: str) -> None:
    if key == "s4":
        await _save_s4_bundle(db, project_id, content)
        return
    from app.domain.section_fields import persist_section_fields

    content = persist_section_fields(key, content)
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


async def _save_s4_bundle(
    db: AsyncSession,
    project_id: uuid.UUID,
    content: str,
    subs: dict[str, str] | None = None,
) -> None:
    """Persist s4.x rows; top-level s4 keeps a short overview only."""
    parts = dict(subs or {})
    if not parts:
        parts = split_scope_subsection_draft(content)
    for sub_key, body in parts.items():
        if sub_key not in SCOPE_SUBSECTIONS:
            continue
        text = (body or "").strip()
        if text:
            await _upsert_sub(db, project_id, sub_key, text)
    overview = build_scope_overview(parts) if parts else (content or "").strip()
    if not overview and content.strip():
        overview = content.strip()
        if len(overview) > 360:
            overview = overview[:360].rstrip() + "…"
        overview = f"{overview}\n\n(รายละเอียดครบในหัวข้อย่อย ๔.๑–๔.๑๔)"
    row = await _get_section(db, project_id, "s4")
    if row is None:
        db.add(
            TORSection(
                project_id=project_id,
                section_key="s4",
                content=overview,
                ai_draft=overview,
                version=1,
            )
        )
        return
    row.content = overview
    row.ai_draft = overview


async def _persist_s4_sub(
    session_factory: Any, project_id: uuid.UUID, sub_key: str, text: str
) -> None:
    async with session_factory() as persist:
        await _upsert_sub(persist, project_id, sub_key, text)
        await persist.commit()


async def _emit_s4_sub_done(
    session_factory: Any | None,
    project_id: uuid.UUID | None,
    sub_key: str,
    title: str,
    text: str,
) -> AsyncIterator[str]:
    if session_factory is not None and project_id is not None:
        await _persist_s4_sub(session_factory, project_id, sub_key, text)
    yield _sse(
        "subsection_done",
        {
            "section_key": "s4",
            "sub_key": sub_key,
            "title": title,
            "content": text,
        },
    )


async def _replay_existing_s4_sub(
    sub_key: str,
    title: str,
    prior: str,
    collected: dict[str, str],
    session_factory: Any | None,
    project_id: uuid.UUID | None,
) -> AsyncIterator[str]:
    collected[sub_key] = prior
    yield _sse(
        "token",
        {
            "section_key": "s4",
            "sub_key": sub_key,
            "text": f"\n### {sub_key} {title}\n{prior}\n",
        },
    )
    async for event in _emit_s4_sub_done(session_factory, project_id, sub_key, title, prior):
        yield event


async def _draft_new_s4_sub(
    redis: Any,
    request_id: str,
    sub_key: str,
    title: str,
    slot_map: dict[str, Any],
    user_id: uuid.UUID,
    collected: dict[str, str],
    errors: list[str],
    session_factory: Any | None,
    project_id: uuid.UUID | None,
) -> AsyncIterator[str]:
    yield _sse(
        "subsection_start",
        {"section_key": "s4", "sub_key": sub_key, "title": title},
    )
    parts: list[str] = []
    try:
        async with admit(redis, "llm", f"{request_id}-{sub_key}"):
            async for token in draft_scope_subsection(sub_key, slot_map, user_id=user_id):
                parts.append(token)
                yield _sse(
                    "token",
                    {"section_key": "s4", "sub_key": sub_key, "text": token},
                )
    except AdmissionTimeoutError:
        errors.append(f"หมดเวลารอคิวโมเดลภาษา ({sub_key})")
        yield _sse(
            "section_error",
            {"section_key": "s4", "sub_key": sub_key, "message": errors[-1]},
        )
        return
    except Exception as exc:
        logger.exception("Draft failed for %s", sub_key)
        errors.append(str(exc)[:200])
        yield _sse(
            "section_error",
            {"section_key": "s4", "sub_key": sub_key, "message": errors[-1]},
        )
        return
    text = "".join(parts).strip()
    if not text:
        return
    collected[sub_key] = text
    async for event in _emit_s4_sub_done(session_factory, project_id, sub_key, title, text):
        yield event


async def _iter_s4_subsection_sse(
    redis: Any,
    request_id: str,
    slot_map: dict[str, Any],
    user_id: uuid.UUID,
    existing: dict[str, str],
    collected: dict[str, str],
    errors: list[str],
    session_factory: Any | None = None,
    project_id: uuid.UUID | None = None,
) -> AsyncIterator[str]:
    for sub_key, title in SCOPE_SUBSECTIONS.items():
        prior = (existing.get(sub_key) or "").strip()
        if prior:
            async for event in _replay_existing_s4_sub(
                sub_key, title, prior, collected, session_factory, project_id
            ):
                yield event
            continue
        async for event in _draft_new_s4_sub(
            redis,
            request_id,
            sub_key,
            title,
            slot_map,
            user_id,
            collected,
            errors,
            session_factory,
            project_id,
        ):
            yield event


async def _draft_missing_section(
    session_factory: Any,
    project_id: uuid.UUID,
    section_key: str,
    slot_map: dict[str, Any],
    user_id: uuid.UUID,
    request_id: str,
    redis: Any,
) -> bool:
    """Draft one missing section. Return True when content was saved."""
    if section_key == "s4":
        collected: dict[str, str] = {}
        errors: list[str] = []
        async with session_factory() as read_session:
            prior_rows = await _load_s4_rows(read_session, project_id)
        prior_ai = {
            row.sub_key: (row.ai_draft or "").strip()
            for row in prior_rows
            if row.sub_key and str(row.ai_draft or "").strip()
        }
        await _consume_sse(
            _iter_s4_subsection_sse(
                redis,
                request_id,
                slot_map,
                user_id,
                prior_ai,
                collected,
                errors,
                session_factory=session_factory,
                project_id=project_id,
            )
        )
        if not _s4_complete(collected):
            logger.warning(
                "s4 incomplete for %s (%s/%s)",
                project_id,
                len(collected),
                len(SCOPE_SUBSECTIONS),
            )
            return False
        preview = build_merged_scope(collected)
        async with session_factory() as persist:
            await _save_s4_bundle(persist, project_id, preview, collected)
            await persist.commit()
        return True
    parts: list[str] = []
    errors: list[str] = []
    await _consume_sse(
        _iter_llm_section_sse(
            redis, request_id, section_key, slot_map, user_id, parts, errors
        )
    )
    if errors:
        return False
    full_text = "".join(parts).strip()
    if not full_text:
        return False
    async with session_factory() as persist:
        await _save_section(persist, project_id, section_key, full_text)
        await persist.commit()
    return True


async def _run_sequential_draft(
    session_factory: Any,
    project_id: uuid.UUID,
    slot_map: dict[str, Any],
    user_id: uuid.UUID,
    request_id: str,
    redis: Any,
    remaining_passes: int = 1,
    reset_store: bool = True,
) -> int:
    """Draft s1–s13 (and s4.1–s4.14) one LM Studio call at a time. Survives SSE disconnect."""
    total = len(TOR_SECTION_ORDER)
    drafted_count = 0
    if reset_store:
        await set_job(redis, project_id, "running", 0, total)
    try:
        for section_key in TOR_SECTION_ORDER:
            existing = await _existing_section_text(session_factory, project_id, section_key)
            if existing:
                drafted_count += 1
                await bump_progress(redis, project_id, drafted_count)
                logger.info("Skip existing %s for %s", section_key, project_id)
                continue
            logger.info("Drafting %s for %s", section_key, project_id)
            try:
                saved = await asyncio.wait_for(
                    _draft_missing_section(
                        session_factory,
                        project_id,
                        section_key,
                        slot_map,
                        user_id,
                        request_id,
                        redis,
                    ),
                    timeout=SECTION_TIMEOUT_SECONDS,
                )
            except TimeoutError:
                logger.warning("Draft timed out for %s on %s", section_key, project_id)
                saved = False
            except Exception:
                logger.exception("Draft failed for %s on %s", section_key, project_id)
                saved = False
            if not saved:
                continue
            drafted_count += 1
            await bump_progress(redis, project_id, drafted_count)
        if drafted_count < total and remaining_passes > 0:
            logger.info(
                "Retry incomplete draft for %s (%s/%s)",
                project_id,
                drafted_count,
                total,
            )
            return await _run_sequential_draft(
                session_factory,
                project_id,
                slot_map,
                user_id,
                request_id,
                redis,
                remaining_passes - 1,
                reset_store=False,
            )
        await mark_status(
            redis, project_id, "done" if drafted_count == total else "failed"
        )
        return drafted_count
    except Exception:
        await mark_status(redis, project_id, "failed")
        raise


async def _ensure_draft_job(
    session_factory: Any,
    project_id: uuid.UUID,
    slot_map: dict[str, Any],
    user_id: uuid.UUID,
    request_id: str,
    redis: Any,
) -> asyncio.Task[int] | None:
    key = str(project_id)
    task = _DRAFT_JOBS.get(key)
    if task is not None and not task.done():
        return task
    stored = await get_job(redis, project_id)
    if stored and stored["status"] in {"queued", "running"}:
        return None
    await set_job(redis, project_id, "queued", 0, len(TOR_SECTION_ORDER))
    _DRAFT_JOBS[key] = asyncio.create_task(
        _run_sequential_draft(
            session_factory, project_id, slot_map, user_id, request_id, redis
        )
    )
    return _DRAFT_JOBS[key]


async def _emit_newly_done_sections(
    session_factory: Any,
    project_id: uuid.UUID,
    seen: set[str],
) -> AsyncIterator[str]:
    for key in TOR_SECTION_ORDER:
        if key in seen:
            continue
        text = await _existing_section_text(session_factory, project_id, key)
        if not text:
            continue
        seen.add(key)
        yield _section_done_event(key, TOR_SECTION_LABELS.get(key, key), text, len(seen))


async def _stream_background_job_progress(
    redis: Any,
    session_factory: Any,
    project_id: uuid.UUID,
    seen: set[str],
) -> AsyncIterator[str]:
    drafted_count = len(seen)
    while True:
        stored = await get_job(redis, project_id)
        async for event in _emit_newly_done_sections(session_factory, project_id, seen):
            yield event
        if stored is None or stored["status"] in {"done", "failed"}:
            drafted_count = int((stored or {}).get("drafted_count") or len(seen))
            break
        yield ": ping\n\n"
        await asyncio.sleep(2)
    yield _sse(
        "all_done",
        {"drafted_count": drafted_count, "total": len(TOR_SECTION_ORDER)},
    )


async def _stream_attached_job_progress(
    job: asyncio.Task[int],
    redis: Any,
    session_factory: Any,
    project_id: uuid.UUID,
    seen: set[str],
) -> AsyncIterator[str]:
    while not job.done():
        yield ": ping\n\n"
        _done, _pending = await asyncio.wait({job}, timeout=2)
        async for event in _emit_newly_done_sections(session_factory, project_id, seen):
            yield event
        if _done:
            break
    drafted_count = 0
    try:
        drafted_count = job.result()
    except Exception:
        logger.exception("Sequential draft job failed for %s", project_id)
    async for event in _emit_newly_done_sections(session_factory, project_id, seen):
        yield event
    yield _sse(
        "all_done",
        {
            "drafted_count": drafted_count or len(seen),
            "total": len(TOR_SECTION_ORDER),
        },
    )


async def _stream_start_draft_chat(
    session_factory: Any,
    project_id: uuid.UUID,
    redis: Any,
    job: asyncio.Task[int] | None,
) -> AsyncIterator[str]:
    yield _sse(
        "progress",
        {"message": "เริ่มร่างทีละหมวดจากโมเดลภาษา", "total": len(TOR_SECTION_ORDER)},
    )
    seen: set[str] = set()
    async for event in _emit_newly_done_sections(session_factory, project_id, seen):
        yield event
    if job is None:
        async for event in _stream_background_job_progress(
            redis, session_factory, project_id, seen
        ):
            yield event
        return
    async for event in _stream_attached_job_progress(
        job, redis, session_factory, project_id, seen
    ):
        yield event


@router.post("/{project_id}/draft-chat/start", dependencies=[Depends(rate_limit_ai)])
async def start_draft_chat(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Auto-draft all 13 TOR sections. Streams SSE progress; work continues if the client drops."""
    project = await _project(db, project_id, current_user)
    if not is_ready_to_compose(project):
        raise ValidationError(
            message="ต้องยืนยันพร้อมร่าง (confirm-ready) ก่อนจึงจะเริ่มร่างได้"
        )
    slot_map = with_project_intake(slot_map_of(project), project)
    request_id = (
        request.headers.get("X-AI-Request-Id") or str(uuid.uuid4())
    ).strip()
    session_factory = request.app.state.db_session_factory
    redis = getattr(request.app.state, "redis", None)
    job = await _ensure_draft_job(
        session_factory, project_id, slot_map, current_user.id, request_id, redis
    )

    return StreamingResponse(
        _stream_start_draft_chat(session_factory, project_id, redis, job),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _stream_accept_intent(
    session_factory: Any,
    project_id: uuid.UUID,
    section_key: str | None,
) -> AsyncIterator[str]:
    if not section_key:
        yield _sse("error", {"message": "กรุณาระบุหมวดที่ยอมรับ เช่น 'ยอมรับ หมวด 6'"})
        return
    async with session_factory() as persist:
        row = await _get_section(persist, project_id, section_key)
        if row is None:
            yield _sse("error", {"message": f"ยังไม่มีร่างหมวด {section_key}"})
            return
        row.is_approved = True
        await persist.commit()
    yield _sse("accepted", {"section_key": section_key, "message": "ยอมรับแล้ว"})


async def _stream_s4_redraft(
    redis: Any,
    request_id: str,
    slot_map: dict[str, Any],
    user_id: uuid.UUID,
    session_factory: Any,
    project_id: uuid.UUID,
    section_key: str,
    label: str,
    intent: str,
) -> AsyncIterator[str]:
    collected: dict[str, str] = {}
    errors: list[str] = []
    async for event in _iter_s4_subsection_sse(
        redis,
        request_id,
        slot_map,
        user_id,
        {},
        collected,
        errors,
        session_factory=session_factory,
        project_id=project_id,
    ):
        yield event
    if not collected:
        return
    preview = build_merged_scope(collected)
    async with session_factory() as persist:
        await _save_s4_bundle(persist, project_id, preview, collected)
        await persist.commit()
    yield _sse(
        "section_done",
        {
            "section_key": section_key,
            "title": label,
            "content": preview,
            "intent": intent,
        },
    )


async def _load_section_draft(
    session_factory: Any,
    project_id: uuid.UUID,
    section_key: str,
) -> str:
    async with session_factory() as read_session:
        if section_key == "s4":
            return build_merged_scope(await _load_s4_subs(read_session, project_id))
        row = await _get_section(read_session, project_id, section_key)
        return (row.content or "") if row else ""


async def _stream_section_revision(
    redis: Any,
    request_id: str,
    section_key: str,
    label: str,
    intent: str,
    detail: str,
    slot_map: dict[str, Any],
    user_id: uuid.UUID,
    session_factory: Any,
    project_id: uuid.UUID,
    current_draft: str,
) -> AsyncIterator[str]:
    parts: list[str] = []
    try:
        async with admit(redis, "llm", request_id):
            if intent in ("edit", "freeform") and current_draft:
                stream = edit_section_draft(section_key, current_draft, detail, slot_map)
            else:
                stream = draft_single_section(section_key, slot_map, user_id=user_id)
            async for token in stream:
                parts.append(token)
                yield _sse("token", {"section_key": section_key, "text": token})
    except AdmissionTimeoutError:
        yield _sse("error", {"message": "หมดเวลารอคิวโมเดลภาษา"})
        return
    except Exception as exc:
        logger.exception("Draft chat message failed for %s", section_key)
        yield _sse("error", {"message": str(exc)[:200]})
        return

    full_text = "".join(parts)
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


async def _stream_draft_chat_message(
    request: Request,
    project_id: uuid.UUID,
    section_key: str | None,
    intent: str,
    detail: str,
    slot_map: dict[str, Any],
    user_id: uuid.UUID,
    request_id: str,
    session_factory: Any,
) -> AsyncIterator[str]:
    if intent == "accept":
        async for event in _stream_accept_intent(session_factory, project_id, section_key):
            yield event
        return

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

    redis = getattr(request.app.state, "redis", None)
    if section_key == "s4" and intent in ("redraft",):
        async for event in _stream_s4_redraft(
            redis,
            request_id,
            slot_map,
            user_id,
            session_factory,
            project_id,
            section_key,
            label,
            intent,
        ):
            yield event
        return

    current_draft = await _load_section_draft(session_factory, project_id, section_key)
    async for event in _stream_section_revision(
        redis,
        request_id,
        section_key,
        label,
        intent,
        detail,
        slot_map,
        user_id,
        session_factory,
        project_id,
        current_draft,
    ):
        yield event


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
    slot_map = with_project_intake(slot_map_of(project), project)
    intent, target_key, detail = parse_draft_message_intent(body.content)
    section_key = body.section_key or target_key
    request_id = (
        request.headers.get("X-AI-Request-Id") or str(uuid.uuid4())
    ).strip()
    session_factory = request.app.state.db_session_factory

    return StreamingResponse(
        _stream_draft_chat_message(
            request,
            project_id,
            section_key,
            intent,
            detail,
            slot_map,
            current_user.id,
            request_id,
            session_factory,
        ),
        media_type="text/event-stream",
    )


def _draft_status_row(
    key: str,
    row: TORSection | None,
    *,
    s4_ready: bool,
    s4_subs: dict[str, str],
) -> tuple[dict[str, Any], bool]:
    if key == "s4":
        has_content = s4_ready or any((value or "").strip() for value in s4_subs.values())
        preview = build_merged_scope(s4_subs)[:200] if has_content else ""
        ai_drafted = s4_ready
    else:
        has_content = bool(row and (row.content or "").strip())
        preview = (row.content or "")[:200] if row else ""
        ai_drafted = bool(row and str(row.ai_draft or "").strip())
    return (
        {
            "section_key": key,
            "title": TOR_SECTION_LABELS.get(key, key),
            "has_content": has_content or ai_drafted,
            "ai_drafted": ai_drafted,
            "content_preview": preview,
            "human_confirmed": bool(row.is_approved) if row else False,
        },
        ai_drafted,
    )


@router.get("/{project_id}/draft-chat/status")
async def draft_chat_status(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Get current drafting progress."""
    await _project(db, project_id, current_user)
    redis = getattr(request.app.state, "redis", None)
    job = await get_job(redis, project_id)
    sections = (
        await db.execute(
            select(TORSection).where(
                TORSection.project_id == project_id,
                TORSection.sub_key.is_(None),
            )
        )
    ).scalars().all()
    section_map = {s.section_key: s for s in sections}
    s4_rows = await _load_s4_rows(db, project_id)
    s4_subs = {row.sub_key: row.content or "" for row in s4_rows if row.sub_key}
    s4_ai_map = _s4_ai_map(s4_rows)
    s4_ready = _s4_complete(s4_ai_map)
    status_list = []
    drafted_count = 0
    for key in TOR_SECTION_ORDER:
        row_data, ai_drafted = _draft_status_row(
            key, section_map.get(key), s4_ready=s4_ready, s4_subs=s4_subs
        )
        if ai_drafted:
            drafted_count += 1
        status_list.append(row_data)
    payload: dict[str, Any] = {
        "sections": status_list,
        "drafted_count": drafted_count,
        "total": len(TOR_SECTION_ORDER),
        "all_drafted": drafted_count == len(TOR_SECTION_ORDER),
    }
    if job:
        payload["job_status"] = job["status"]
        payload["drafted_count"] = job["drafted_count"]
        payload["total"] = job["total"] or payload["total"]
        payload["all_drafted"] = job["status"] == "done"
    return _ok(request, payload)
