"""Project intake: bulk upload, analyze pack, coverage, chat, fill-reference, confirm."""

from __future__ import annotations

import json
import logging
import uuid
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
from app.rag.hybrid import hybrid_retrieve
from app.rate_limiter import rate_limit_ai
from app.rbac import require_project_access
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.intake_service import (
    INTAKE_CHAT_SYSTEM,
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
    content: str = Field(..., min_length=20, max_length=200_000)


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
        mime = upload.content_type or "application/pdf"
        name = upload.filename or "upload.bin"
        tmp_suffix = "." + name.rsplit(".", 1)[-1] if "." in name else ".bin"
        tmp_path = await write_temp_bytes(content, suffix=tmp_suffix)
        extracted = extract_text(tmp_path, mime)
        await unlink_path(tmp_path)
        # Stay on this project pack only — do not ingest into shared/user RAG.
        file_status = "ocr" if extracted.method in {"ocr", "mixed"} else "ok"
        append_intake_text(project, name, extracted.text, file_status)
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
    texts = (project.extracted_fields or {}).get("intake_texts") or []
    pack = "\n\n".join(
        f"## {item.get('name')}\n{item.get('text')}" for item in texts if isinstance(item, dict)
    )
    filenames = [str(item.get("name")) for item in texts if isinstance(item, dict)]
    if not pack.strip():
        raise ValidationError(message="ยังไม่มีเอกสารให้วิเคราะห์", field="files")
    result = await analyze_pack(project, pack, filenames)
    analysis = merge_analysis(project.analysis_json or {}, result)
    analysis["intake_files"] = analysis.get("intake_files") or (project.analysis_json or {}).get(
        "intake_files", []
    )
    analysis["analyzed"] = True
    project.analysis_json = analysis
    try:
        flag_modified(project, "analysis_json")
    except AttributeError:
        pass
    project.current_phase = max(project.current_phase or 0, 1)
    await db.flush()
    # Best-effort: fill legal/standard gaps from knowledge base so Phase 2 is not all-gap.
    try:
        filled_refs = await fill_non_fact_reference_slots(
            project, current_user.id, as_standard=True
        )
        analysis = dict(project.analysis_json or {})
        analysis["standard_fill_keys"] = filled_refs.get("filled_keys") or []
        project.analysis_json = analysis
        await db.flush()
    except Exception as exc:  # noqa: BLE001 — analyze must still return
        logger.warning("post-analyze standard fill skipped: %s", exc)
    return _ok(
        request,
        {
            "slot_map": analysis["slot_map"],
            "gap_questions": analysis.get("gap_questions") or [],
            "coverage": coverage_table(analysis["slot_map"]),
            "ready_to_compose": False,
            "analyzed": True,
            "phase": project.current_phase,
            "standard_fill_keys": analysis.get("standard_fill_keys") or [],
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

    async def generate() -> AsyncIterator[str]:
        import asyncio

        if ref_key:
            filled = await fill_reference_slot(ref_key, current_user.id)
            action = apply_reference_to_slot(slot_map, ref_key, filled, as_standard=True)
            label = INTAKE_SLOT_LABELS.get(ref_key, ref_key)
            if action == "skipped":
                reply = f"หมวด {label} มีข้อเท็จจริงอยู่แล้ว จึงไม่ทับข้อมูลนั้นครับ"
            else:
                reply = f"ใส่มาตรฐานกลางจากคลังให้หมวด {label} แล้วครับ"
            asking_now = analysis.get("current_asking_slot")
            asking_key = asking_now if isinstance(asking_now, str) else None
            reply = append_next_slot_question(reply, asking_key)
            await _persist_intake_assistant(
                request.app.state.db_session_factory,
                project.id,
                room.id,
                slot_map,
                reply,
                [],
                asking_slot=asking_key,
            )
            yield _sse(
                "done",
                {
                    "content": reply,
                    "citations": [],
                    "coverage": coverage_table(slot_map),
                    "filled_slots": filled_keys,
                    "current_slot": asking_key,
                    "next_question": build_slot_question(asking_key) if asking_key else None,
                    "all_fact_filled": not missing_fact_keys(slot_map),
                    "reference_action": action,
                    "reference_slot": ref_key,
                },
            )
            return

        if is_fill_reference_request(body.content):
            asking_now = analysis.get("current_asking_slot")
            asking_key = asking_now if isinstance(asking_now, str) else None
            reply = append_next_slot_question(
                "ระบุหมวดที่ต้องการดึงมาตรฐาน เช่น ดึงอ้างอิงกฎหมายให้ s10",
                asking_key,
            )
            await _persist_intake_assistant(
                request.app.state.db_session_factory,
                project.id,
                room.id,
                slot_map,
                reply,
                [],
                asking_slot=asking_key,
            )
            yield _sse(
                "done",
                {
                    "content": reply,
                    "citations": [],
                    "coverage": coverage_table(slot_map),
                    "filled_slots": [],
                    "current_slot": asking_key,
                    "next_question": build_slot_question(asking_key) if asking_key else None,
                    "all_fact_filled": not missing_fact_keys(slot_map),
                },
            )
            return

        # Fast deterministic ack when slots were filled — no LLM wait.
        if filled_keys or not missing_fact_keys(slot_map):
            asking_key = asking if isinstance(asking, str) else None
            reply = phase2_filled_ack(filled_keys, asking_key)
            if body.attach_legal_reference and filled_keys:
                extra = await _attach_legal_to_filled(
                    slot_map, filled_keys, current_user.id, True
                )
                if extra:
                    reply = extra + reply
            await _persist_intake_assistant(
                request.app.state.db_session_factory,
                project.id,
                room.id,
                slot_map,
                reply,
                [],
                asking_slot=asking_key,
            )
            yield _sse(
                "done",
                {
                    "content": reply,
                    "citations": [],
                    "coverage": coverage_table(slot_map),
                    "filled_slots": filled_keys,
                    "current_slot": asking_key,
                    "next_question": build_slot_question(asking_key) if asking_key else None,
                    "all_fact_filled": not missing_fact_keys(slot_map),
                    "progress": coverage_progress(slot_map),
                },
            )
            return


        # Instant Phase-2 replies (no LLM hang / no "กำลังพิมพ์..." forever).
        if chat_path.startswith("fast"):
            reply = phase2_filled_ack(filled_keys, asking_key) if filled_keys else phase2_template_reply(
                filled_keys=filled_keys,
                next_slot=asking_key,
                all_filled=all_filled_now,
            )
            progress = coverage_progress(slot_map)
            await _persist_intake_assistant(
                request.app.state.db_session_factory,
                project.id,
                room.id,
                slot_map,
                reply,
                [],
                asking_slot=asking_key,
            )
            step = 12
            for i in range(0, len(reply), step):
                yield _sse("token", {"text": reply[i : i + step]})
            yield _sse(
                "done",
                {
                    "content": reply,
                    "citations": [],
                    "coverage": coverage_table(slot_map),
                    "filled_slots": filled_keys,
                    "current_slot": asking_key,
                    "next_question": build_slot_question(asking_key) if asking_key else None,
                    "all_fact_filled": all_filled_now,
                    "progress": progress,
                    "fast_path": True,
                },
            )
            return

        attached = await _attach_legal_to_filled(
            slot_map,
            filled_keys,
            current_user.id,
            body.attach_legal_reference,
        )

        context = ""
        citations: list = []
        degraded = False
        # Only hit embed/RAG when the officer asked for legal attach (H-D).
        if body.attach_legal_reference:
            result, citations, degraded = await hybrid_retrieve(
                body.content,
                user_id=current_user.id,
                search_scope=(
                    body.search_scope
                    if body.search_scope in {"global", "mine", "both"}
                    else "both"
                ),
                top_k=3,
            )
            context = "\n\n".join(
                f"[{c.source_document or 'คลัง'}] {c.text}" for c in result.chunks[:3]
            )
        current_slot = analysis.get("current_asking_slot")
        slot_label = INTAKE_SLOT_LABELS.get(current_slot or "", "")
        missing = missing_fact_keys(slot_map)
        missing_labels = ", ".join(
            INTAKE_SLOT_LABELS.get(key, key) for key in missing[:6]
        ) or "(ไม่มี)"
        user = (
            f"ช่องที่กำลังถาม: {slot_label or '-'} ({current_slot or '-'})\n"
            f"ช่องข้อเท็จจริงที่ยังขาด: {missing_labels}\n"
            f"บริบทกฎหมาย:\n{(context or '(ไม่มี)')[:1200]}\n\n"
            f"ข้อความผู้ใช้:\n{(body.content or '')[:2000]}\n\n"
            "ตอบสั้นเป็นภาษาพูด ไม่เกิน 4 ประโยค แล้วถามเฉพาะช่องที่ยังขาด (ถ้ามี)"
        )
        redis = getattr(request.app.state, "redis", None)
        event_q: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()

        async def on_wait(position: int, waiting_ms: int) -> None:
            await event_q.put(
                (
                    "queued",
                    {
                        "request_id": request_id,
                        "position": position,
                        "waiting_ms": waiting_ms,
                    },
                )
            )

        async def run_llm() -> None:
            parts_local: list[str] = []
            try:
                await event_q.put(("started", {"request_id": request_id}))
                async with admit(redis, "llm", request_id, on_wait=on_wait):
                    llm = ProviderFactory().get_llm("chat")  # NOSONAR python:S930 — ProviderFactory.get_llm(task=...)
                    # No short asyncio.timeout — LM Studio often queues sequentially;
                    # provider lm_studio_timeout already bounds the HTTP stream.
                    async for token in llm.stream(
                        [
                            {"role": "system", "content": INTAKE_CHAT_SYSTEM},
                            {"role": "user", "content": user},
                        ],
                        temperature=0.2,
                        max_tokens=384,
                    ):
                        parts_local.append(token)
                        await event_q.put(("token", {"text": token}))
                full_text = append_next_slot_question(
                    attached + "".join(parts_local),
                    analysis.get("current_asking_slot")
                    if isinstance(analysis.get("current_asking_slot"), str)
                    else None,
                )
                if not str(full_text or "").strip():
                    full_text = phase2_template_reply(
                        filled_keys=filled_keys,
                        next_slot=asking_key,
                        all_filled=all_filled_now,
                    )
                await _persist_intake_assistant(
                    request.app.state.db_session_factory,
                    project.id,
                    room.id,
                    slot_map,
                    full_text,
                    citations,
                    asking_slot=analysis.get("current_asking_slot")
                    if isinstance(analysis.get("current_asking_slot"), str)
                    else None,
                )
                await event_q.put(
                    (
                        "done",
                        {
                            "content": full_text,
                            "citations": citations,
                            "coverage": coverage_table(slot_map),
                            "graph_degraded": degraded,
                            "filled_slots": filled_keys,
                            "current_slot": analysis.get("current_asking_slot"),
                            "next_question": (
                                build_slot_question(analysis["current_asking_slot"])
                                if analysis.get("current_asking_slot")
                                else None
                            ),
                            "all_fact_filled": not missing_fact_keys(slot_map),
                            "progress": coverage_progress(slot_map),
                        },
                    )
                )
            except TimeoutError:
                fallback = phase2_template_reply(
                    filled_keys=filled_keys,
                    next_slot=asking_key,
                    all_filled=all_filled_now,
                )
                logger.warning("intake chat LLM timed out; using template fallback")
                await _persist_intake_assistant(
                    request.app.state.db_session_factory,
                    project.id,
                    room.id,
                    slot_map,
                    fallback,
                    citations,
                    asking_slot=asking_key,
                )
                await event_q.put(("token", {"text": fallback}))
                await event_q.put(
                    (
                        "done",
                        {
                            "content": fallback,
                            "citations": citations,
                            "coverage": coverage_table(slot_map),
                            "filled_slots": filled_keys,
                            "current_slot": asking_key,
                            "next_question": (
                                build_slot_question(asking_key) if asking_key else None
                            ),
                            "all_fact_filled": all_filled_now,
                            "progress": coverage_progress(slot_map),
                            "fast_path": True,
                        },
                    )
                )
            except AdmissionTimeoutError as exc:
                await event_q.put(("error", {"message": str(exc)}))
            except Exception as exc:
                logger.exception("intake chat failed")
                await event_q.put(("error", {"message": str(exc)}))
            finally:
                await event_q.put(None)

        task = asyncio.create_task(run_llm())
        try:
            while True:
                item = await event_q.get()
                if item is None:
                    break
                event_name, payload = item
                yield _sse(event_name, payload)
        finally:
            await task

    return StreamingResponse(generate(), media_type="text/event-stream")
