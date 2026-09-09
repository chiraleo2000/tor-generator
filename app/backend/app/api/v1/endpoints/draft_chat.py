"""Chat-driven TOR drafting endpoints (Phase 3).

POST /projects/{id}/draft-chat/start — auto-draft mother sections (SSE stream)
POST /projects/{id}/draft-chat/message — edit/accept/redraft via chat (SSE stream)
GET  /projects/{id}/draft-chat/status — drafting progress

หมวดขอบเขตงาน (s4) บันทึกลงหัวข้อย่อยตาม Section_Profile ของประเภทงาน
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from dataclasses import dataclass
from typing import Annotated, Any, AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.domain.section_profile import LEGACY_SCOPE_TITLES, profile_for_project
from app.domain.tor_sections import TOR_SECTION_LABELS
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
    fallback_scope_subsection,
    fallback_section_text,
    parse_draft_message_intent,
)
from app.services.intake_service import is_ready_to_compose, slot_map_of, with_project_intake

logger = logging.getLogger("tor_app.draft_chat")
router = APIRouter()
_DRAFT_JOBS: dict[str, asyncio.Task[int]] = {}
# Live SSE fan-out from the background draft job to connected observers.
_DRAFT_EVENT_SUBS: dict[str, list[asyncio.Queue[str]]] = {}


def _subscribe_draft_events(project_id: uuid.UUID) -> asyncio.Queue[str]:
    key = str(project_id)
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=512)
    _DRAFT_EVENT_SUBS.setdefault(key, []).append(queue)
    return queue


def _unsubscribe_draft_events(project_id: uuid.UUID, queue: asyncio.Queue[str]) -> None:
    key = str(project_id)
    subs = _DRAFT_EVENT_SUBS.get(key)
    if not subs:
        return
    try:
        subs.remove(queue)
    except ValueError:
        return
    if not subs:
        _DRAFT_EVENT_SUBS.pop(key, None)


def _publish_draft_sse(project_id: uuid.UUID, raw: str, *, drop_ok: bool = True) -> None:
    """Push one SSE frame to live observers. Token frames may drop if a queue is full."""
    for queue in _DRAFT_EVENT_SUBS.get(str(project_id), ()):
        try:
            queue.put_nowait(raw)
            continue
        except asyncio.QueueFull:
            if drop_ok:
                continue
        try:
            queue.get_nowait()
        except asyncio.QueueEmpty:
            pass
        try:
            queue.put_nowait(raw)
        except asyncio.QueueFull:
            pass


def _sse_payload_section_key(raw: str) -> str | None:
    if "event: section_done" not in raw:
        return None
    for line in raw.splitlines():
        if not line.startswith("data: "):
            continue
        try:
            data = json.loads(line[6:])
        except json.JSONDecodeError:
            return None
        key = data.get("section_key")
        return key if isinstance(key, str) else None
    return None


def _ptype_of(proj: Any) -> str | None:
    if proj is None:
        return None
    raw = getattr(proj, "project_type", None)
    return raw if isinstance(raw, str) else None


def _mains(project_type: str | None) -> list[str]:
    return profile_for_project(project_type).main_storage_keys()


def _scopes(project_type: str | None) -> dict[str, str]:
    return {
        item.storage_key: item.title
        for item in profile_for_project(project_type).scope_subsections
    }


def _section_timeout_seconds() -> int:
    raw = os.environ.get("DRAFT_SECTION_TIMEOUT_SECONDS", "300")
    try:
        return max(30, int(raw))
    except ValueError:
        return 180


# Per-section cap. Local Gemma compose often needs 4–5 minutes; 1800s blocked 13/13 for hours.
SECTION_TIMEOUT_SECONDS = _section_timeout_seconds()


def sequential_draft_order(project_type: str | None = None) -> list[str]:
    """Draft s4 last so later mother sections are not blocked by scope LLM calls."""
    order = _mains(project_type)
    rest = [key for key in order if key != "s4"]
    if "s4" in order:
        return rest + ["s4"]
    return rest


@dataclass
class _SeqDraft:
    session_factory: Any
    project_id: uuid.UUID
    slot_map: dict[str, Any]
    user_id: uuid.UUID
    request_id: str
    redis: Any
    project_type: str | None = None


@dataclass
class _S4Work:
    redis: Any
    request_id: str
    slot_map: dict[str, Any]
    user_id: uuid.UUID
    collected: dict[str, str]
    errors: list[str]
    session_factory: Any | None = None
    project_id: uuid.UUID | None = None
    project_type: str | None = None


@dataclass
class _ChatStream:
    request: Request
    project_id: uuid.UUID
    section_key: str | None
    intent: str
    detail: str
    slot_map: dict[str, Any]
    user_id: uuid.UUID
    request_id: str
    session_factory: Any
    project_type: str | None = None


async def _consume_sse(events: AsyncIterator[str]) -> int:
    count = 0
    async for _event in events:
        count += 1
    return count


def _sse_drop_ok(raw: str) -> bool:
    """Only token frames are safe to drop when an observer queue is full."""
    return raw.startswith("event: token")


async def _relay_job_sse(project_id: uuid.UUID, events: AsyncIterator[str]) -> int:
    """Consume draft SSE while forwarding frames to live /start observers."""
    count = 0
    async for raw in events:
        count += 1
        _publish_draft_sse(project_id, raw, drop_ok=_sse_drop_ok(raw))
        await asyncio.sleep(0)
    return count


class DraftChatMessageBody(BaseModel):
    content: str = Field(..., min_length=1)
    section_key: str | None = None


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _section_done_event(
    section_key: str,
    label: str,
    content: str,
    drafted_count: int,
    total: int | None = None,
    project_type: str | None = None,
) -> str:
    if total is None:
        total = len(_mains(project_type))
    return _sse(
        "section_done",
        {
            "section_key": section_key,
            "title": label,
            "content": content,
            "drafted_count": drafted_count,
            "total": total,
        },
    )


def _s4_ai_map(rows: list[TORSection]) -> dict[str, str]:
    return {
        row.sub_key: (row.ai_draft or row.content or "").strip()
        for row in rows
        if row.sub_key and str(row.ai_draft or row.content or "").strip()
    }


def _s4_complete(drafted: dict[str, str], project_type: str | None = None) -> bool:
    return all(str(drafted.get(key) or "").strip() for key in _scopes(project_type))


async def _existing_section_text(
    session_factory: Any,
    project_id: uuid.UUID,
    section_key: str,
) -> str | None:
    async with session_factory() as persist:
        if section_key == "s4":
            proj = await persist.get(Project, project_id)
            ptype = _ptype_of(proj)
            drafted = _s4_ai_map(await _load_s4_rows(persist, project_id))
            if _s4_complete(drafted, ptype):
                return build_merged_scope(drafted, ptype)
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
    except Exception as exc:  # NOSONAR python:S110 — LLM draft fail-open per section
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


def _s4_overview_text(parts: dict[str, str], content: str) -> str:
    overview = build_scope_overview(parts) if parts else (content or "").strip()
    if overview or not content.strip():
        return overview
    clipped = content.strip()
    if len(clipped) > 360:
        clipped = clipped[:360].rstrip() + "…"
    return f"{clipped}\n\n(รายละเอียดอยู่ในหัวข้อย่อยขอบเขตของงานตามประเภทโครงการ)"


async def _save_s4_bundle(
    db: AsyncSession,
    project_id: uuid.UUID,
    content: str,
    subs: dict[str, str] | None = None,
) -> None:
    """Persist scope subsection rows; top-level s4 keeps a short overview only."""
    parts = dict(subs or {})
    if not parts:
        parts = split_scope_subsection_draft(content)
    proj = await db.get(Project, project_id)
    ptype = _ptype_of(proj)
    allowed = set(_scopes(ptype)) | set(LEGACY_SCOPE_TITLES)
    for sub_key, body in parts.items():
        text = (body or "").strip()
        if sub_key not in allowed or not text:
            continue
        await _upsert_sub(db, project_id, sub_key, text)
    overview = _s4_overview_text(parts, content)
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


async def _draft_new_s4_sub(work: _S4Work, sub_key: str, title: str) -> AsyncIterator[str]:
    yield _sse(
        "subsection_start",
        {"section_key": "s4", "sub_key": sub_key, "title": title},
    )
    parts: list[str] = []
    try:
        async with admit(work.redis, "llm", f"{work.request_id}-{sub_key}"):
            async with asyncio.timeout(SECTION_TIMEOUT_SECONDS):
                async for token in draft_scope_subsection(
                    sub_key, work.slot_map, user_id=work.user_id
                ):
                    parts.append(token)
                    yield _sse(
                        "token",
                        {"section_key": "s4", "sub_key": sub_key, "text": token},
                    )
    except AdmissionTimeoutError:
        work.errors.append(f"หมดเวลารอคิวโมเดลภาษา ({sub_key})")
        yield _sse(
            "section_error",
            {"section_key": "s4", "sub_key": sub_key, "message": work.errors[-1]},
        )
        return
    except TimeoutError:
        work.errors.append(f"หมดเวลาร่างหัวข้อย่อย ({sub_key})")
        yield _sse(
            "section_error",
            {"section_key": "s4", "sub_key": sub_key, "message": work.errors[-1]},
        )
        return
    except Exception as exc:  # NOSONAR python:S110 — LLM draft fail-open per subsection
        logger.exception("Draft failed for %s", sub_key)
        work.errors.append(str(exc)[:200])
        yield _sse(
            "section_error",
            {"section_key": "s4", "sub_key": sub_key, "message": work.errors[-1]},
        )
        return
    text = "".join(parts).strip()
    if not text:
        return
    work.collected[sub_key] = text
    async for event in _emit_s4_sub_done(
        work.session_factory, work.project_id, sub_key, title, text
    ):
        yield event


async def _iter_s4_subsection_sse(work: _S4Work, existing: dict[str, str]) -> AsyncIterator[str]:
    for sub_key, title in _scopes(work.project_type).items():
        prior = (existing.get(sub_key) or "").strip()
        if prior:
            async for event in _replay_existing_s4_sub(
                sub_key, title, prior, work.collected, work.session_factory, work.project_id
            ):
                yield event
            continue
        async for event in _draft_new_s4_sub(work, sub_key, title):
            yield event


async def _draft_missing_s4(job: _SeqDraft) -> bool:
    work = _S4Work(
        redis=job.redis,
        request_id=job.request_id,
        slot_map=job.slot_map,
        user_id=job.user_id,
        collected={},
        errors=[],
        session_factory=job.session_factory,
        project_id=job.project_id,
        project_type=job.project_type,
    )
    async with job.session_factory() as read_session:
        prior_rows = await _load_s4_rows(read_session, job.project_id)
    prior_ai = {
        row.sub_key: (row.ai_draft or "").strip()
        for row in prior_rows
        if row.sub_key and str(row.ai_draft or "").strip()
    }
    await _relay_job_sse(job.project_id, _iter_s4_subsection_sse(work, prior_ai))
    for sub_key in _scopes(job.project_type):
        if str(work.collected.get(sub_key) or "").strip():
            continue
        filled = fallback_scope_subsection(sub_key, job.slot_map, job.project_type).strip()
        if not filled:
            continue
        work.collected[sub_key] = filled
    if not _s4_complete(work.collected, job.project_type):
        logger.warning(
            "s4 incomplete for %s (%s/%s)",
            job.project_id,
            len(work.collected),
            len(_scopes(job.project_type)),
        )
        return False
    preview = build_merged_scope(work.collected, job.project_type)
    async with job.session_factory() as persist:
        await _save_s4_bundle(persist, job.project_id, preview, work.collected)
        await persist.commit()
    return True


async def _draft_missing_section(job: _SeqDraft, section_key: str) -> bool:
    """Draft one missing section. Return True when content was saved."""
    if section_key == "s4":
        return await _draft_missing_s4(job)
    parts: list[str] = []
    errors: list[str] = []
    await _relay_job_sse(
        job.project_id,
        _iter_llm_section_sse(
            job.redis,
            job.request_id,
            section_key,
            job.slot_map,
            job.user_id,
            parts,
            errors,
        ),
    )
    if errors:
        logger.warning("Draft LLM error for %s: %s", section_key, errors[:2])
    full_text = "".join(parts).strip() or fallback_section_text(
        section_key, job.slot_map
    ).strip()
    if not full_text:
        return False
    async with job.session_factory() as persist:
        await _save_section(persist, job.project_id, section_key, full_text)
        await persist.commit()
    return True


def section_draft_timeout(section_key: str) -> float:
    """s4 still has many subsections; cap the whole pass so หมวด 5–13 are not blocked."""
    if section_key == "s4":
        return float(SECTION_TIMEOUT_SECONDS * 3)
    return float(SECTION_TIMEOUT_SECONDS)


async def _persist_fallback_s4(job: _SeqDraft) -> bool:
    collected: dict[str, str] = {}
    async with job.session_factory() as read_session:
        prior_rows = await _load_s4_rows(read_session, job.project_id)
    for row in prior_rows:
        text = str(row.ai_draft or row.content or "").strip()
        if row.sub_key and text:
            collected[row.sub_key] = text
    for sub_key in _scopes(job.project_type):
        if str(collected.get(sub_key) or "").strip():
            continue
        filled = fallback_scope_subsection(sub_key, job.slot_map, job.project_type).strip()
        if filled:
            collected[sub_key] = filled
    if not _s4_complete(collected, job.project_type):
        return False
    preview = build_merged_scope(collected, job.project_type)
    async with job.session_factory() as persist:
        await _save_s4_bundle(persist, job.project_id, preview, collected)
        await persist.commit()
    return True


async def _persist_fallback_section(job: _SeqDraft, section_key: str) -> bool:
    if section_key == "s4":
        return await _persist_fallback_s4(job)
    text = fallback_section_text(section_key, job.slot_map).strip()
    if not text:
        return False
    async with job.session_factory() as persist:
        await _save_section(persist, job.project_id, section_key, text)
        await persist.commit()
    return True


async def _try_draft_one_section(job: _SeqDraft, section_key: str) -> bool:
    label = TOR_SECTION_LABELS.get(section_key, section_key)
    _publish_draft_sse(
        job.project_id,
        _sse("section_start", {"section_key": section_key, "title": label}),
        drop_ok=False,
    )
    existing = await _existing_section_text(
        job.session_factory, job.project_id, section_key
    )
    if existing:
        logger.info("Skip existing %s for %s", section_key, job.project_id)
        return True
    logger.info("Drafting %s for %s", section_key, job.project_id)
    try:
        return await asyncio.wait_for(
            _draft_missing_section(job, section_key),
            timeout=section_draft_timeout(section_key),
        )
    except TimeoutError:
        logger.warning("Draft timed out for %s on %s", section_key, job.project_id)
        try:
            return await _persist_fallback_section(job, section_key)
        except Exception:  # NOSONAR python:S110 — skip this section and continue
            logger.exception("Fallback draft failed for %s", section_key)
            return False
    except Exception:  # NOSONAR python:S110 — one section must not abort the job
        logger.exception("Draft failed for %s on %s", section_key, job.project_id)
        try:
            return await _persist_fallback_section(job, section_key)
        except Exception:  # NOSONAR python:S110 — skip this section and continue
            logger.exception("Fallback draft failed for %s", section_key)
            return False


async def _publish_section_done(
    job: _SeqDraft, section_key: str, drafted_count: int
) -> None:
    text = await _existing_section_text(
        job.session_factory, job.project_id, section_key
    )
    if not text:
        return
    label = TOR_SECTION_LABELS.get(section_key, section_key)
    _publish_draft_sse(
        job.project_id,
        _section_done_event(section_key, label, text, drafted_count),
        drop_ok=False,
    )


async def _run_sequential_draft(
    job: _SeqDraft, remaining_passes: int = 2, reset_store: bool = True
) -> int:
    """Draft remaining sections one LLM call at a time. Survives SSE disconnect."""
    from app.services.draft_chat_service import clear_s4_rag_cache

    total = len(_mains(job.project_type))
    drafted_count = 0
    if reset_store:
        clear_s4_rag_cache()
        await set_job(job.redis, job.project_id, "running", 0, total)
    try:
        for section_key in sequential_draft_order(job.project_type):
            saved = await _try_draft_one_section(job, section_key)
            if not saved:
                continue
            drafted_count += 1
            await bump_progress(job.redis, job.project_id, drafted_count)
            await _publish_section_done(job, section_key, drafted_count)
        if drafted_count < total and remaining_passes > 0:
            logger.info(
                "Retry incomplete draft for %s (%s/%s)",
                job.project_id,
                drafted_count,
                total,
            )
            return await _run_sequential_draft(job, remaining_passes - 1, False)
        await mark_status(
            job.redis, job.project_id, "done" if drafted_count == total else "failed"
        )
        return drafted_count
    except Exception:  # NOSONAR python:S110 — mark failed then re-raise
        await mark_status(job.redis, job.project_id, "failed")
        raise


async def _ensure_draft_job(
    session_factory: Any,
    project_id: uuid.UUID,
    slot_map: dict[str, Any],
    user_id: uuid.UUID,
    request_id: str,
    redis: Any,
    project_type: str | None = None,
) -> asyncio.Task[int] | None:
    key = str(project_id)
    task = _DRAFT_JOBS.get(key)
    if task is not None and not task.done():
        return task
    stored = await get_job(redis, project_id)
    resume = bool(stored and stored["status"] in {"queued", "running"})
    if resume:
        logger.warning(
            "Resuming draft job %s (redis=%s, no live task)",
            key,
            stored.get("status") if stored else None,
        )
    else:
        await set_job(redis, project_id, "queued", 0, len(_mains(project_type)))
    job = _SeqDraft(
        session_factory=session_factory,
        project_id=project_id,
        slot_map=slot_map,
        user_id=user_id,
        request_id=request_id,
        redis=redis,
        project_type=project_type,
    )
    _DRAFT_JOBS[key] = asyncio.create_task(
        _run_sequential_draft(job, remaining_passes=2, reset_store=not resume)
    )
    return _DRAFT_JOBS[key]


async def _emit_newly_done_sections(
    session_factory: Any,
    project_id: uuid.UUID,
    seen: set[str],
    project_type: str | None = None,
) -> AsyncIterator[str]:
    if project_type is None:
        async with session_factory() as session:
            proj = await session.get(Project, project_id)
            project_type = _ptype_of(proj)
    total = len(_mains(project_type))
    for key in _mains(project_type):
        if key in seen:
            continue
        text = await _existing_section_text(session_factory, project_id, key)
        if not text:
            continue
        seen.add(key)
        yield _section_done_event(
            key, TOR_SECTION_LABELS.get(key, key), text, len(seen), total, project_type
        )


async def _drain_draft_event_queue(
    queue: asyncio.Queue[str],
    seen: set[str],
) -> AsyncIterator[str]:
    while True:
        try:
            raw = queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        key = _sse_payload_section_key(raw)
        if key:
            seen.add(key)
        yield raw


async def _stream_job_live_events(
    queue: asyncio.Queue[str],
    session_factory: Any,
    project_id: uuid.UUID,
    seen: set[str],
    *,
    job_done: Any,
) -> AsyncIterator[str]:
    """Yield live job frames; fall back to DB poll when the queue is quiet."""
    while not job_done():
        try:
            raw = await asyncio.wait_for(queue.get(), timeout=0.75)
        except TimeoutError:
            yield ": ping\n\n"
            async for event in _emit_newly_done_sections(session_factory, project_id, seen):
                yield event
            continue
        key = _sse_payload_section_key(raw)
        if key:
            seen.add(key)
        yield raw
    async for raw in _drain_draft_event_queue(queue, seen):
        yield raw
    async for event in _emit_newly_done_sections(session_factory, project_id, seen):
        yield event


async def _iter_background_live_frames(
    redis: Any,
    live: asyncio.Queue[str],
    session_factory: Any,
    project_id: uuid.UUID,
    seen: set[str],
) -> AsyncIterator[str]:
    while True:
        stored = await get_job(redis, project_id)
        if (stored or {}).get("status") in {"done", "failed"}:
            break
        try:
            raw = await asyncio.wait_for(live.get(), timeout=0.75)
        except TimeoutError:
            yield ": ping\n\n"
            async for event in _emit_newly_done_sections(session_factory, project_id, seen):
                yield event
            continue
        key = _sse_payload_section_key(raw)
        if key:
            seen.add(key)
        yield raw


async def _stream_background_job_progress(
    redis: Any,
    session_factory: Any,
    project_id: uuid.UUID,
    seen: set[str],
    queue: asyncio.Queue[str] | None = None,
) -> AsyncIterator[str]:
    owned = queue is None
    live = queue or _subscribe_draft_events(project_id)
    drafted_count = len(seen)
    try:
        async for frame in _iter_background_live_frames(
            redis, live, session_factory, project_id, seen
        ):
            yield frame
        async for raw in _drain_draft_event_queue(live, seen):
            yield raw
        async for event in _emit_newly_done_sections(session_factory, project_id, seen):
            yield event
        stored = await get_job(redis, project_id)
        drafted_count = int((stored or {}).get("drafted_count") or len(seen))
    finally:
        if owned:
            _unsubscribe_draft_events(project_id, live)
    ptype = None
    async with session_factory() as session:
        proj = await session.get(Project, project_id)
        ptype = _ptype_of(proj)
    yield _sse(
        "all_done",
        {"drafted_count": drafted_count, "total": len(_mains(ptype))},
    )


async def _stream_attached_job_progress(
    job: asyncio.Task[int],
    session_factory: Any,
    project_id: uuid.UUID,
    seen: set[str],
    queue: asyncio.Queue[str] | None = None,
) -> AsyncIterator[str]:
    owned = queue is None
    live = queue or _subscribe_draft_events(project_id)
    try:
        async for event in _stream_job_live_events(
            live,
            session_factory,
            project_id,
            seen,
            job_done=job.done,
        ):
            yield event
    finally:
        if owned:
            _unsubscribe_draft_events(project_id, live)
    drafted_count = 0
    try:
        drafted_count = job.result()
    except Exception:  # NOSONAR python:S110 — observer still closes SSE
        logger.exception("Sequential draft job failed for %s", project_id)
    async for event in _emit_newly_done_sections(session_factory, project_id, seen):
        yield event
    ptype = None
    async with session_factory() as session:
        proj = await session.get(Project, project_id)
        ptype = _ptype_of(proj)
    yield _sse(
        "all_done",
        {
            "drafted_count": drafted_count or len(seen),
            "total": len(_mains(ptype)),
        },
    )


async def _stream_start_draft_chat(
    session_factory: Any,
    project_id: uuid.UUID,
    redis: Any,
    job: asyncio.Task[int] | None,
    queue: asyncio.Queue[str],
) -> AsyncIterator[str]:
    try:
        ptype = None
        async with session_factory() as session:
            proj = await session.get(Project, project_id)
            ptype = _ptype_of(proj)
        yield _sse(
            "progress",
            {
                "message": "เริ่มร่างทีละหมวดจากโมเดลภาษา",
                "total": len(_mains(ptype)),
            },
        )
        seen: set[str] = set()
        async for event in _emit_newly_done_sections(session_factory, project_id, seen):
            yield event
        if job is None:
            async for event in _stream_background_job_progress(
                redis, session_factory, project_id, seen, queue
            ):
                yield event
            return
        async for event in _stream_attached_job_progress(
            job, session_factory, project_id, seen, queue
        ):
            yield event
    finally:
        _unsubscribe_draft_events(project_id, queue)


@router.post("/{project_id}/draft-chat/start", dependencies=[Depends(rate_limit_ai)])
async def start_draft_chat(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Auto-draft mother TOR sections for this project's profile. Work continues if the client drops."""
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
    # Subscribe before spawning the job so the first section_start is not missed.
    queue = _subscribe_draft_events(project_id)
    job = await _ensure_draft_job(
        session_factory,
        project_id,
        slot_map,
        current_user.id,
        request_id,
        redis,
        project.project_type,
    )

    return StreamingResponse(
        _stream_start_draft_chat(session_factory, project_id, redis, job, queue),
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
    stream: _ChatStream, redis: Any, label: str
) -> AsyncIterator[str]:
    work = _S4Work(
        redis=redis,
        request_id=stream.request_id,
        slot_map=stream.slot_map,
        user_id=stream.user_id,
        collected={},
        errors=[],
        session_factory=stream.session_factory,
        project_id=stream.project_id,
        project_type=stream.project_type,
    )
    async for event in _iter_s4_subsection_sse(work, {}):
        yield event
    if not work.collected:
        return
    preview = build_merged_scope(work.collected, stream.project_type)
    async with stream.session_factory() as persist:
        await _save_s4_bundle(persist, stream.project_id, preview, work.collected)
        await persist.commit()
    yield _sse(
        "section_done",
        {
            "section_key": stream.section_key,
            "title": label,
            "content": preview,
            "intent": stream.intent,
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
    stream: _ChatStream,
    redis: Any,
    label: str,
    current_draft: str,
) -> AsyncIterator[str]:
    section_key = stream.section_key or ""
    parts: list[str] = []
    try:
        async with admit(redis, "llm", stream.request_id):
            if stream.intent in ("edit", "freeform") and current_draft:
                token_stream = edit_section_draft(
                    section_key, current_draft, stream.detail, stream.slot_map
                )
            else:
                token_stream = draft_single_section(
                    section_key, stream.slot_map, user_id=stream.user_id
                )
            async for token in token_stream:
                parts.append(token)
                yield _sse("token", {"section_key": section_key, "text": token})
    except AdmissionTimeoutError:
        yield _sse("error", {"message": "หมดเวลารอคิวโมเดลภาษา"})
        return
    except Exception as exc:  # NOSONAR python:S110 — chat still returns an error event
        logger.exception("Draft chat message failed for %s", section_key)
        yield _sse("error", {"message": str(exc)[:200]})
        return

    full_text = "".join(parts)
    async with stream.session_factory() as persist:
        await _save_section(persist, stream.project_id, section_key, full_text)
        await persist.commit()
    yield _sse(
        "section_done",
        {
            "section_key": section_key,
            "title": label,
            "content": full_text,
            "intent": stream.intent,
        },
    )


async def _stream_draft_chat_message(stream: _ChatStream) -> AsyncIterator[str]:
    if stream.intent == "accept":
        async for event in _stream_accept_intent(
            stream.session_factory, stream.project_id, stream.section_key
        ):
            yield event
        return

    if not stream.section_key:
        yield _sse(
            "error",
            {"message": "กรุณาระบุหมวดที่ต้องการแก้ไข เช่น 'ร่างใหม่ หมวด 1'"},
        )
        return

    label = TOR_SECTION_LABELS.get(stream.section_key, stream.section_key)
    yield _sse(
        "section_start",
        {"section_key": stream.section_key, "title": label, "intent": stream.intent},
    )

    redis = getattr(stream.request.app.state, "redis", None)
    if stream.section_key == "s4" and stream.intent == "redraft":
        async for event in _stream_s4_redraft(stream, redis, label):
            yield event
        return

    current_draft = await _load_section_draft(
        stream.session_factory, stream.project_id, stream.section_key
    )
    async for event in _stream_section_revision(stream, redis, label, current_draft):
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
            _ChatStream(
                request=request,
                project_id=project_id,
                section_key=section_key,
                intent=intent,
                detail=detail,
                slot_map=slot_map,
                user_id=current_user.id,
                request_id=request_id,
                session_factory=session_factory,
                project_type=project.project_type,
            )
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
    project = await _project(db, project_id, current_user)
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
    s4_ready = _s4_complete(s4_ai_map, project.project_type)
    status_list = []
    drafted_count = 0
    mains = _mains(project.project_type)
    for key in mains:
        row_data, ai_drafted = _draft_status_row(
            key, section_map.get(key), s4_ready=s4_ready, s4_subs=s4_subs
        )
        if ai_drafted:
            drafted_count += 1
        status_list.append(row_data)
    sections_complete = drafted_count == len(mains)
    payload: dict[str, Any] = {
        "sections": status_list,
        "drafted_count": drafted_count,
        "total": len(mains),
        "all_drafted": sections_complete,
    }
    if job:
        payload["job_status"] = job["status"]
        payload["total"] = job["total"] or payload["total"]
        payload["drafted_count"] = max(drafted_count, job["drafted_count"])
        payload["all_drafted"] = sections_complete
    return _ok(request, payload)
