"""Project intake: bulk upload, analyze pack, coverage, chat, fill-reference, confirm."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Any, AsyncIterator

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.constants import PROJECT_NOT_FOUND
from app.deps import get_current_user, get_db
from app.domain.slots import FACT_REQUIRED_SLOTS, INTAKE_SLOT_LABELS
from app.exceptions import NotFoundError, ValidationError
from app.io_temp import unlink_path, write_temp_bytes
from app.llm_admission import AdmissionTimeoutError, admit
from app.models.chat_message import ChatMessage
from app.models.chat_room import ChatRoom
from app.models.project import Project
from app.models.tor_section import TORSection
from app.models.user import User
from app.providers.factory import ProviderFactory
from app.rag.extraction import extract_text
from app.rag.hybrid import hybrid_retrieve, unpack_hybrid
from app.rate_limiter import rate_limit_ai
from app.rbac import require_project_access
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.intake_service import (
    INTAKE_CHAT_SYSTEM,
    INTAKE_TEXT_CHAR_LIMIT,
    analyze_pack,
    append_intake_text,
    append_next_slot_question,
    apply_chat_answer_to_slots,
    apply_reference_to_slot,
    attest_hitl_sections,
    build_phase2_opening,
    build_phase3_opening,
    build_slot_question,
    coverage_progress,
    coverage_table,
    empty_slot_map,
    fill_current_slot,
    fill_non_fact_reference_slots,
    fill_reference_slot,
    has_been_analyzed,
    has_intake_material,
    is_fill_reference_request,
    is_ready_to_compose,
    load_project,
    merge_analysis,
    missing_fact_keys,
    next_asking_slot,
    parse_fill_reference_request,
    phase2_filled_ack,
    phase2_template_reply,
    ready_criteria_met,
    slot_map_of,
)

logger = logging.getLogger("tor_app.intake")
router = APIRouter()
INTAKE_PASTE_FILENAME = "ข้อความผู้ใช้.txt"
INTAKE_MAX_UPLOAD_BYTES = 50 * 1024 * 1024



def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _persist_intake_assistant(
    session_maker,
    project_id: uuid.UUID,
    room_id: uuid.UUID,
    slot_map: dict[str, Any],
    content: str,
    citations: list,
    asking_slot: str | None = None,
) -> None:
    async with session_maker() as persist:
        row = (await persist.execute(select(Project).where(Project.id == project_id))).scalar_one()
        merged = dict(row.analysis_json or {})
        merged["slot_map"] = slot_map
        merged["current_asking_slot"] = asking_slot
        row.analysis_json = merged
        persist.add(
            ChatMessage(
                room_id=room_id,
                role="assistant",
                content=content,
                citations=citations,
            )
        )
        await persist.commit()


async def _attach_legal_to_filled(
    slot_map: dict[str, Any],
    filled_keys: list[str],
    user_id: uuid.UUID,
    attach: bool,
) -> str:
    if not attach or not filled_keys:
        return ""
    target = filled_keys[-1]
    filled = await fill_reference_slot(target, user_id)
    action = apply_reference_to_slot(slot_map, target, filled, force_append=True)
    if action == "skipped":
        return ""
    label = INTAKE_SLOT_LABELS.get(target, target)
    return f"แนบอ้างอิงกฎหมายประกอบ {label} แล้ว โดยไม่ทับข้อเท็จจริงที่วิเคราะห์ไว้\n\n"


class FillReferenceBody(BaseModel):
    slot_key: str = Field(..., min_length=2, max_length=20)


class IntakeChatBody(BaseModel):
    content: str = Field(..., min_length=1)
    search_scope: str = "both"
    attach_legal_reference: bool = False


class ConfirmReadyBody(BaseModel):
    confirm: bool = True


class IntakeTextBody(BaseModel):
    content: str = Field(..., min_length=20, max_length=INTAKE_TEXT_CHAR_LIMIT)


def _ok(request: Request, data: Any) -> JSONResponse:
    payload = SuccessResponse(
        ok=True,
        data=data,
        meta=MetaInfo(
            request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )
    return JSONResponse(content=payload.model_dump(mode="json"))


async def _project(db: AsyncSession, project_id: uuid.UUID, user: User):
    project = await load_project(db, project_id)
    if project is None:
        raise NotFoundError(message=PROJECT_NOT_FOUND)
    require_project_access(project.owner_id, user)
    return project


async def _ensure_intake_room(db: AsyncSession, project, user: User) -> ChatRoom:
    existing = (
        await db.execute(
            select(ChatRoom).where(
                ChatRoom.user_id == user.id,
                ChatRoom.kind == "draft_intake",
                ChatRoom.project_id == project.id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    room = ChatRoom(
        user_id=user.id,
        kind="draft_intake",
        project_id=project.id,
        title=f"ร่าง {project.name}"[:255],
    )
    db.add(room)
    await db.flush()
    return room


def _flag_analysis(project: Project) -> None:
    try:
        flag_modified(project, "analysis_json")
    except AttributeError:
        pass


def _intake_pack(texts: Any) -> tuple[str, list[str]]:
    items = texts if isinstance(texts, list) else []
    pack = "\n\n".join(
        str(item.get("text") or "").strip()
        for item in items
        if isinstance(item, dict) and str(item.get("text") or "").strip()
    )
    filenames = [str(item.get("name")) for item in items if isinstance(item, dict)]
    return pack, filenames


def _gap_questions_for(slot_map: dict[str, Any]) -> list[str]:
    return [
        f"ขอข้อมูลสำหรับ {INTAKE_SLOT_LABELS.get(key, key)} ({key})"
        for key in FACT_REQUIRED_SLOTS
        if (slot_map.get(key) or {}).get("status") != "filled"
    ]


def _apply_analyze_result(project: Project, result: dict[str, Any]) -> dict[str, Any]:
    analysis = merge_analysis(project.analysis_json or {}, result)
    analysis["intake_files"] = analysis.get("intake_files") or (project.analysis_json or {}).get(
        "intake_files", []
    )
    analysis["analyzed"] = True
    analysis["standard_fill_keys"] = []
    project.analysis_json = analysis
    _flag_analysis(project)
    project.current_phase = max(project.current_phase or 0, 1)
    return analysis


async def _persist_heuristic_slot_map(
    project: Project, db: AsyncSession, slot_map: dict[str, Any]
) -> None:
    analysis = merge_analysis(
        project.analysis_json or {},
        {
            "slot_map": slot_map,
            "gap_questions": _gap_questions_for(slot_map),
            "ready_to_compose": False,
            "analyzed": True,
        },
    )
    analysis["intake_files"] = analysis.get("intake_files") or (project.analysis_json or {}).get(
        "intake_files", []
    )
    project.analysis_json = analysis
    _flag_analysis(project)
    project.current_phase = max(project.current_phase or 0, 1)
    await db.flush()
    await db.commit()


def _asking_key(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _chat_done_payload(
    *,
    content: str,
    slot_map: dict[str, Any],
    filled_keys: list[str],
    asking_key: str | None,
    citations: list | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "content": content,
        "citations": citations or [],
        "coverage": coverage_table(slot_map),
        "filled_slots": filled_keys,
        "current_slot": asking_key,
        "next_question": build_slot_question(asking_key) if asking_key else None,
        "all_fact_filled": not missing_fact_keys(slot_map),
        "progress": coverage_progress(slot_map),
    }
    if extra:
        payload.update(extra)
    return payload


async def _stream_reference_fill(
    *,
    session_maker,
    project_id: uuid.UUID,
    room_id: uuid.UUID,
    slot_map: dict[str, Any],
    analysis: dict[str, Any],
    ref_key: str,
    filled_keys: list[str],
    user_id: uuid.UUID,
) -> AsyncIterator[str]:
    filled = await fill_reference_slot(ref_key, user_id)
    action = apply_reference_to_slot(slot_map, ref_key, filled, as_standard=True)
    label = INTAKE_SLOT_LABELS.get(ref_key, ref_key)
    if action == "skipped":
        reply = f"หมวด {label} มีข้อเท็จจริงอยู่แล้ว จึงไม่ทับข้อมูลนั้นครับ"
    else:
        reply = f"ใส่มาตรฐานกลางจากคลังให้หมวด {label} แล้วครับ"
    asking = _asking_key(analysis.get("current_asking_slot"))
    reply = append_next_slot_question(reply, asking)
    await _persist_intake_assistant(
        session_maker, project_id, room_id, slot_map, reply, [], asking_slot=asking
    )
    yield _sse(
        "done",
        _chat_done_payload(
            content=reply,
            slot_map=slot_map,
            filled_keys=filled_keys,
            asking_key=asking,
            extra={"reference_action": action, "reference_slot": ref_key},
        ),
    )


async def _stream_reference_prompt(
    *,
    session_maker,
    project_id: uuid.UUID,
    room_id: uuid.UUID,
    slot_map: dict[str, Any],
    analysis: dict[str, Any],
) -> AsyncIterator[str]:
    asking = _asking_key(analysis.get("current_asking_slot"))
    reply = append_next_slot_question(
        "ระบุหมวดที่ต้องการดึงมาตรฐาน เช่น ดึงอ้างอิงกฎหมายให้ s10",
        asking,
    )
    await _persist_intake_assistant(
        session_maker, project_id, room_id, slot_map, reply, [], asking_slot=asking
    )
    yield _sse(
        "done",
        _chat_done_payload(
            content=reply, slot_map=slot_map, filled_keys=[], asking_key=asking
        ),
    )


async def _stream_filled_ack(
    *,
    session_maker,
    project_id: uuid.UUID,
    room_id: uuid.UUID,
    slot_map: dict[str, Any],
    filled_keys: list[str],
    asking: Any,
    user_id: uuid.UUID,
    attach_legal: bool,
) -> AsyncIterator[str]:
    asking_key = _asking_key(asking)
    reply = phase2_filled_ack(filled_keys, asking_key)
    if attach_legal and filled_keys:
        extra = await _attach_legal_to_filled(slot_map, filled_keys, user_id, True)
        if extra:
            reply = extra + reply
    await _persist_intake_assistant(
        session_maker, project_id, room_id, slot_map, reply, [], asking_slot=asking_key
    )
    yield _sse(
        "done",
        _chat_done_payload(
            content=reply,
            slot_map=slot_map,
            filled_keys=filled_keys,
            asking_key=asking_key,
        ),
    )


async def _retrieve_legal_context(
    content: str,
    user_id: uuid.UUID,
    search_scope: str,
    attach: bool,
) -> tuple[str, list, bool]:
    if not attach:
        return "", [], False
    scope = search_scope if search_scope in {"global", "mine", "both"} else "both"
    result, citations, degraded, _mcp = unpack_hybrid(
        await hybrid_retrieve(content, user_id=user_id, search_scope=scope, top_k=3)
    )
    context = "\n\n".join(
        f"[{c.source_document or 'คลัง'}] {c.text}" for c in result.chunks[:3]
    )
    return context, citations, degraded


def _intake_llm_user_prompt(
    analysis: dict[str, Any], slot_map: dict[str, Any], content: str, context: str
) -> str:
    current_slot = analysis.get("current_asking_slot")
    slot_label = INTAKE_SLOT_LABELS.get(current_slot or "", "")
    missing = missing_fact_keys(slot_map)
    missing_labels = ", ".join(
        INTAKE_SLOT_LABELS.get(key, key) for key in missing[:6]
    ) or "(ไม่มี)"
    return (
        f"ช่องที่กำลังถาม: {slot_label or '-'} ({current_slot or '-'})\n"
        f"ช่องข้อเท็จจริงที่ยังขาด: {missing_labels}\n"
        f"บริบทกฎหมาย:\n{(context or '(ไม่มี)')[:1200]}\n\n"
        f"ข้อความผู้ใช้:\n{(content or '')[:2000]}\n\n"
        "ตอบสั้นเป็นภาษาพูด ไม่เกิน 4 ประโยค แล้วถามเฉพาะช่องที่ยังขาด (ถ้ามี)"
    )


@dataclass
class _IntakeLlmWork:
    request: Request
    project: Project
    room: ChatRoom
    analysis: dict[str, Any]
    slot_map: dict[str, Any]
    filled_keys: list[str]
    asking_key: str | None
    all_filled_now: bool
    request_id: str
    attached: str
    citations: list
    degraded: bool
    user_prompt: str


async def _persist_llm_reply(work: _IntakeLlmWork, content: str, asking: str | None) -> None:
    await _persist_intake_assistant(
        work.request.app.state.db_session_factory,
        work.project.id,
        work.room.id,
        work.slot_map,
        content,
        work.citations,
        asking_slot=asking,
    )


async def _run_intake_llm_job(work: _IntakeLlmWork, event_q) -> None:
    parts_local: list[str] = []
    redis = getattr(work.request.app.state, "redis", None)

    async def on_wait(position: int, waiting_ms: int) -> None:
        await event_q.put(
            (
                "queued",
                {
                    "request_id": work.request_id,
                    "position": position,
                    "waiting_ms": waiting_ms,
                },
            )
        )

    try:
        await event_q.put(("started", {"request_id": work.request_id}))
        async with admit(redis, "llm", work.request_id, on_wait=on_wait):
            llm = ProviderFactory().get_llm("chat")  # NOSONAR python:S930
            async for token in llm.stream(
                [
                    {"role": "system", "content": INTAKE_CHAT_SYSTEM},
                    {"role": "user", "content": work.user_prompt},
                ],
                temperature=0.2,
                max_tokens=384,
            ):
                parts_local.append(token)
                await event_q.put(("token", {"text": token}))
        asking = _asking_key(work.analysis.get("current_asking_slot"))
        full_text = append_next_slot_question(work.attached + "".join(parts_local), asking)
        if not str(full_text or "").strip():
            full_text = phase2_template_reply(
                filled_keys=work.filled_keys,
                next_slot=work.asking_key,
                all_filled=work.all_filled_now,
            )
        await _persist_llm_reply(work, full_text, asking)
        await event_q.put(
            (
                "done",
                _chat_done_payload(
                    content=full_text,
                    slot_map=work.slot_map,
                    filled_keys=work.filled_keys,
                    asking_key=asking,
                    citations=work.citations,
                    extra={"graph_degraded": work.degraded},
                ),
            )
        )
    except TimeoutError:
        fallback = phase2_template_reply(
            filled_keys=work.filled_keys,
            next_slot=work.asking_key,
            all_filled=work.all_filled_now,
        )
        logger.warning("intake chat LLM timed out; using template fallback")
        await _persist_llm_reply(work, fallback, work.asking_key)
        await event_q.put(("token", {"text": fallback}))
        await event_q.put(
            (
                "done",
                _chat_done_payload(
                    content=fallback,
                    slot_map=work.slot_map,
                    filled_keys=work.filled_keys,
                    asking_key=work.asking_key,
                    citations=work.citations,
                    extra={"fast_path": True},
                ),
            )
        )
    except AdmissionTimeoutError as exc:
        await event_q.put(("error", {"message": str(exc)}))
    except Exception as exc:
        logger.exception("intake chat failed")
        await event_q.put(("error", {"message": str(exc)}))
    finally:
        await event_q.put(None)


async def _stream_intake_llm(work: _IntakeLlmWork) -> AsyncIterator[str]:
    import asyncio

    event_q: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()
    task = asyncio.create_task(_run_intake_llm_job(work, event_q))
    try:
        while True:
            item = await event_q.get()
            if item is None:
                break
            event_name, payload = item
            yield _sse(event_name, payload)
    finally:
        await task


async def _iter_intake_chat_sse(
    *,
    request: Request,
    project: Project,
    room: ChatRoom,
    body: IntakeChatBody,
    user_id: uuid.UUID,
    analysis: dict[str, Any],
    slot_map: dict[str, Any],
    filled_keys: list[str],
    asking: Any,
    ref_key: str | None,
    request_id: str,
) -> AsyncIterator[str]:
    session_maker = request.app.state.db_session_factory
    asking_key = _asking_key(asking)
    all_filled_now = not missing_fact_keys(slot_map)

    if ref_key:
        async for event in _stream_reference_fill(
            session_maker=session_maker,
            project_id=project.id,
            room_id=room.id,
            slot_map=slot_map,
            analysis=analysis,
            ref_key=ref_key,
            filled_keys=filled_keys,
            user_id=user_id,
        ):
            yield event
        return

    if is_fill_reference_request(body.content):
        async for event in _stream_reference_prompt(
            session_maker=session_maker,
            project_id=project.id,
            room_id=room.id,
            slot_map=slot_map,
            analysis=analysis,
        ):
            yield event
        return

    if filled_keys or all_filled_now:
        async for event in _stream_filled_ack(
            session_maker=session_maker,
            project_id=project.id,
            room_id=room.id,
            slot_map=slot_map,
            filled_keys=filled_keys,
            asking=asking,
            user_id=user_id,
            attach_legal=body.attach_legal_reference,
        ):
            yield event
        return

    attached = await _attach_legal_to_filled(
        slot_map, filled_keys, user_id, body.attach_legal_reference
    )
    context, citations, degraded = await _retrieve_legal_context(
        body.content, user_id, body.search_scope, body.attach_legal_reference
    )
    work = _IntakeLlmWork(
        request=request,
        project=project,
        room=room,
        analysis=analysis,
        slot_map=slot_map,
        filled_keys=filled_keys,
        asking_key=asking_key,
        all_filled_now=all_filled_now,
        request_id=request_id,
        attached=attached,
        citations=citations,
        degraded=degraded,
        user_prompt=_intake_llm_user_prompt(analysis, slot_map, body.content, context),
    )
    async for event in _stream_intake_llm(work):
        yield event


@router.post("/{project_id}/intake/upload")
async def intake_upload(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    files: Annotated[list[UploadFile], File()],
) -> JSONResponse:
    project = await _project(db, project_id, current_user)
    saved: list[str] = []
    for upload in files:
        content = await upload.read()
        if not content:
            continue
        if len(content) > INTAKE_MAX_UPLOAD_BYTES:
            raise ValidationError(
                message=f"ขนาดไฟล์เกินกำหนด สูงสุด {INTAKE_MAX_UPLOAD_BYTES // (1024 * 1024)} MB",
                field="files",
            )
        mime = upload.content_type or "application/pdf"
        name = upload.filename or "upload.bin"
        tmp_suffix = "." + name.rsplit(".", 1)[-1] if "." in name else ".bin"
        tmp_path = await write_temp_bytes(content, suffix=tmp_suffix)
        extracted = extract_text(tmp_path, mime)
        await unlink_path(tmp_path)
        # Stay on this project pack only — do not ingest into shared/user RAG.
        file_status = "ocr" if extracted.method in {"ocr", "mixed"} else "ok"
        if not (extracted.text or "").strip():
            file_status = "empty"
        append_intake_text(
            project,
            name,
            extracted.text,
            file_status,
            warnings=extracted.warnings,
        )
        saved.append(name)
    await db.flush()
    return _ok(request, {"files": saved, "count": len(saved)})


@router.post("/{project_id}/intake/text")
async def intake_text(
    request: Request,
    project_id: uuid.UUID,
    body: IntakeTextBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    project = await _project(db, project_id, current_user)
    text = body.content.strip()
    append_intake_text(project, INTAKE_PASTE_FILENAME, text)
    await db.flush()
    return _ok(request, {"files": [INTAKE_PASTE_FILENAME], "count": 1})


@router.post("/{project_id}/intake/analyze")
async def intake_analyze(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    project = await _project(db, project_id, current_user)
    pack, filenames = _intake_pack((project.extracted_fields or {}).get("intake_texts") or [])
    if not pack.strip():
        raise ValidationError(message="ยังไม่มีเอกสารให้วิเคราะห์", field="files")

    result = await analyze_pack(
        project,
        pack,
        filenames,
        persist_heuristic=lambda slot_map: _persist_heuristic_slot_map(project, db, slot_map),
    )
    analysis = _apply_analyze_result(project, result)
    await db.flush()
    return _ok(
        request,
        {
            "slot_map": analysis["slot_map"],
            "gap_questions": analysis.get("gap_questions") or [],
            "coverage": coverage_table(analysis["slot_map"]),
            "ready_to_compose": False,
            "analyzed": True,
            "phase": project.current_phase,
            "standard_fill_keys": [],
        },
    )


@router.get("/{project_id}/intake/coverage")
async def intake_coverage(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    project = await _project(db, project_id, current_user)
    slot_map = (project.analysis_json or {}).get("slot_map") or empty_slot_map()
    return _ok(
        request,
        {
            "coverage": coverage_table(slot_map),
            "gap_questions": (project.analysis_json or {}).get("gap_questions") or [],
            "ready_to_compose": bool((project.analysis_json or {}).get("ready_to_compose")),
            "slot_map": slot_map,
            "has_material": has_intake_material(project),
            "analyzed": has_been_analyzed(project),
        },
    )


@router.post("/{project_id}/intake/fill-reference")
async def intake_fill_reference(
    request: Request,
    project_id: uuid.UUID,
    body: FillReferenceBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    project = await _project(db, project_id, current_user)
    if body.slot_key not in INTAKE_SLOT_LABELS:
        raise ValidationError(message="รหัสช่องไม่ถูกต้อง", field="slot_key")
    analysis = dict(project.analysis_json or {})
    slot_map = dict(analysis.get("slot_map") or empty_slot_map())
    existing = slot_map.get(body.slot_key)
    if (
        isinstance(existing, dict)
        and existing.get("status") == "filled"
        and body.slot_key in FACT_REQUIRED_SLOTS
    ):
        return _ok(
            request,
            {
                "slot_key": body.slot_key,
                "action": "skipped",
                "skipped": True,
                "content": existing.get("content") or "",
                "sources": existing.get("sources") or [],
                "coverage": coverage_table(slot_map),
            },
        )
    filled = await fill_reference_slot(body.slot_key, current_user.id)
    action = apply_reference_to_slot(slot_map, body.slot_key, filled)
    analysis["slot_map"] = slot_map
    project.analysis_json = analysis
    await db.flush()
    current = slot_map.get(body.slot_key) or {}
    return _ok(
        request,
        {
            "slot_key": body.slot_key,
            "action": action,
            "skipped": action == "skipped",
            "content": current.get("content") or filled.get("content") or "",
            "sources": current.get("sources") or filled.get("sources") or [],
            "coverage": coverage_table(slot_map),
        },
    )


@router.post("/{project_id}/intake/confirm-ready")
async def intake_confirm_ready(
    request: Request,
    project_id: uuid.UUID,
    body: ConfirmReadyBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    project = await _project(db, project_id, current_user)
    analysis = dict(project.analysis_json or {})
    slot_map = analysis.get("slot_map") or empty_slot_map()
    if not ready_criteria_met(slot_map):
        raise ValidationError(
            message="ยังมีช่องข้อเท็จจริงที่บังคับว่าง — ตอบในแชทหรืออัปโหลดเอกสารเพิ่ม",
            field="ready_to_compose",
        )
    if not body.confirm:
        raise ValidationError(message="ต้องยืนยันพร้อมร่าง", field="confirm")
    analysis["ready_to_compose"] = True
    project.analysis_json = analysis
    project.current_phase = max(project.current_phase or 0, 3)
    await db.commit()
    return _ok(request, {"ready_to_compose": True, "phase": project.current_phase})


@router.post("/{project_id}/intake/open-qa")
async def intake_open_qa(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Seed Phase 2 chat with a spoken summary of Phase 1 analysis (once)."""
    project = await _project(db, project_id, current_user)
    if not has_been_analyzed(project):
        raise ValidationError(message="ต้องวิเคราะห์ในขั้นที่ ๑ ก่อนจึงจะคุยต่อได้", field="analyzed")
    room = await _ensure_intake_room(db, project, current_user)
    analysis = dict(project.analysis_json or {})
    slot_map = slot_map_of(project)
    brief = build_phase2_opening(slot_map, list(analysis.get("gap_questions") or []))
    asking = next_asking_slot(slot_map)
    analysis["current_asking_slot"] = asking
    if not analysis.get("phase2_briefed"):
        db.add(
            ChatMessage(
                room_id=room.id,
                role="assistant",
                content=brief,
                citations=[],
            )
        )
        analysis["phase2_briefed"] = True
        analysis["phase2_followup_slot"] = asking
        project.analysis_json = analysis
        await db.commit()
    elif asking and analysis.get("phase2_followup_slot") != asking:
        db.add(
            ChatMessage(
                room_id=room.id,
                role="assistant",
                content=build_slot_question(asking),
                citations=[],
            )
        )
        analysis["phase2_followup_slot"] = asking
        project.analysis_json = analysis
        await db.commit()
    return _ok(
        request,
        {
            "brief": brief,
            "room_id": str(room.id),
            "coverage": coverage_table(slot_map),
            "current_slot": analysis.get("current_asking_slot") or asking,
            "next_question": build_slot_question(asking) if asking else None,
        },
    )


@router.post("/{project_id}/intake/open-draft")
async def intake_open_draft(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Seed Phase 3 chat so the officer can ask for section rewrites in conversation."""
    project = await _project(db, project_id, current_user)
    if not has_been_analyzed(project):
        raise ValidationError(message="ต้องวิเคราะห์ก่อนจึงจะร่างได้", field="analyzed")
    room = await _ensure_intake_room(db, project, current_user)
    analysis = dict(project.analysis_json or {})
    brief = build_phase3_opening()
    if not analysis.get("phase3_opened"):
        db.add(
            ChatMessage(
                room_id=room.id,
                role="assistant",
                content=brief,
                citations=[],
            )
        )
        analysis["phase3_opened"] = True
        project.analysis_json = analysis
        await db.commit()
    return _ok(request, {"brief": brief, "room_id": str(room.id)})


@router.get("/{project_id}/intake/qa-next")
async def intake_qa_next(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    """Return the next slot question for sequential Phase 2 Q&A."""
    project = await _project(db, project_id, current_user)
    analysis = dict(project.analysis_json or {})
    slot_map = analysis.get("slot_map") or empty_slot_map()
    current = analysis.get("current_asking_slot")
    asking = next_asking_slot(slot_map, current if isinstance(current, str) else None)
    all_filled = not missing_fact_keys(slot_map)
    if asking != current:
        analysis["current_asking_slot"] = asking
        project.analysis_json = analysis
        await db.flush()
    return _ok(
        request,
        {
            "current_slot": asking,
            "question": build_slot_question(asking) if asking else None,
            "slot_label": INTAKE_SLOT_LABELS.get(asking or "", ""),
            "coverage": coverage_table(slot_map),
            "all_fact_filled": all_filled,
            "missing_count": len(missing_fact_keys(slot_map)),
            "total_fact_slots": len(FACT_REQUIRED_SLOTS),
        },
    )


@router.post("/{project_id}/intake/fill-references")
async def intake_fill_references(
    request: Request,
    project_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    project = await _project(db, project_id, current_user)
    if not has_been_analyzed(project):
        raise ValidationError(message="ต้องวิเคราะห์ก่อนจึงจะดึงกฎระเบียบได้", field="analyzed")
    filled = await fill_non_fact_reference_slots(
        project, current_user.id, as_standard=True
    )
    await db.flush()
    return _ok(
        request,
        {
            "filled_keys": filled["filled_keys"],
            "coverage": coverage_table(filled["slot_map"]),
        },
    )


@router.post("/{project_id}/intake/confirm-phase4")
async def intake_confirm_phase4(
    request: Request,
    project_id: uuid.UUID,
    body: ConfirmReadyBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    project = await _project(db, project_id, current_user)
    if not is_ready_to_compose(project):
        raise ValidationError(
            message="ต้องยืนยันพร้อมร่างและครบช่องข้อเท็จจริงก่อน",
            field="ready_to_compose",
        )
    if not body.confirm:
        raise ValidationError(message="ต้องยืนยันด้วยตนเองก่อนเข้าทบทวน", field="confirm")
    sec_result = await db.execute(
        select(TORSection).where(
            TORSection.project_id == project_id,
            TORSection.sub_key.is_(None),
        )
    )
    fetched = sec_result.scalars().all()
    rows = list(fetched) if isinstance(fetched, (list, tuple)) else []
    if rows:
        attest_hitl_sections(rows)
    analysis = dict(project.analysis_json or {})
    analysis["phase4_confirmed"] = True
    project.analysis_json = analysis
    try:
        flag_modified(project, "analysis_json")
    except AttributeError:
        pass
    project.current_phase = max(project.current_phase or 0, 4)
    await db.commit()
    return _ok(request, {"phase4_confirmed": True, "phase": project.current_phase})


@router.post("/{project_id}/intake/chat", dependencies=[Depends(rate_limit_ai)])
async def intake_chat(
    request: Request,
    project_id: uuid.UUID,
    body: IntakeChatBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    project = await _project(db, project_id, current_user)
    room = await _ensure_intake_room(db, project, current_user)
    db.add(ChatMessage(room_id=room.id, role="user", content=body.content, citations=[]))
    await db.flush()
    analysis = dict(project.analysis_json or {})
    slot_map = analysis.get("slot_map") or empty_slot_map()
    asking = next_asking_slot(
        slot_map,
        analysis.get("current_asking_slot")
        if isinstance(analysis.get("current_asking_slot"), str)
        else None,
    )
    filled_keys: list[str] = []
    ref_key = parse_fill_reference_request(body.content)
    if not ref_key:
        filled_keys = apply_chat_answer_to_slots(slot_map, body.content)
        asking = next_asking_slot(slot_map)
    analysis["slot_map"] = slot_map
    analysis["current_asking_slot"] = asking
    project.analysis_json = analysis
    # Commit before SSE so slot fills + user message survive if the stream ends early.
    await db.commit()
    request_id = (
        request.headers.get("X-AI-Request-Id") or str(uuid.uuid4())
    ).strip()
    return StreamingResponse(
        _iter_intake_chat_sse(
            request=request,
            project=project,
            room=room,
            body=body,
            user_id=current_user.id,
            analysis=analysis,
            slot_map=slot_map,
            filled_keys=filled_keys,
            asking=asking,
            ref_key=ref_key,
            request_id=request_id,
        ),
        media_type="text/event-stream",
    )
