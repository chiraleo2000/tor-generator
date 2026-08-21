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

from app import infra as runtime
from app.api.constants import PROJECT_NOT_FOUND
from app.deps import get_current_user, get_db
from app.domain.slots import FACT_REQUIRED_SLOTS, INTAKE_SLOT_LABELS
from app.exceptions import NotFoundError, ValidationError
from app.io_temp import unlink_path, write_temp_bytes
from app.llm_admission import AdmissionTimeoutError, admit
from app.models.chat_message import ChatMessage
from app.models.chat_room import ChatRoom
from app.models.project import Project
from app.models.user import User
from app.providers.factory import ProviderFactory
from app.rag.document_pipeline import ingest_file_bytes
from app.rag.extraction import extract_text
from app.rag.hybrid import hybrid_retrieve
from app.rate_limiter import rate_limit_ai
from app.rbac import require_project_access
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.intake_service import (
    INTAKE_CHAT_SYSTEM,
    analyze_pack,
    append_intake_text,
    apply_slot_map_to_sections,
    build_phase2_opening,
    build_phase3_opening,
    build_slot_question,
    coverage_table,
    empty_slot_map,
    fill_current_slot,
    fill_non_fact_reference_slots,
    fill_reference_slot,
    has_been_analyzed,
    has_intake_material,
    is_ready_to_compose,
    load_project,
    merge_analysis,
    missing_fact_keys,
    next_asking_slot,
    ready_criteria_met,
    slot_map_for_prompt,
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


class FillReferenceBody(BaseModel):
    slot_key: str = Field(..., min_length=2, max_length=20)


class IntakeChatBody(BaseModel):
    content: str = Field(..., min_length=1)
    search_scope: str = "both"


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
    factory = runtime.session_factory or request.app.state.db_session_factory
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
        await ingest_file_bytes(
            db=db,
            filename=name,
            content=content,
            mime_type=mime,
            scope="user",
            owner_id=current_user.id,
            project_id=str(project.id),
            session_factory=factory,
        )
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
    factory = runtime.session_factory or request.app.state.db_session_factory
    await ingest_file_bytes(
        db=db,
        filename=INTAKE_PASTE_FILENAME,
        content=text.encode("utf-8"),
        mime_type="text/plain",
        scope="user",
        owner_id=current_user.id,
        project_id=str(project.id),
        session_factory=factory,
    )
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
    project.current_phase = max(project.current_phase or 0, 1)
    await db.flush()
    return _ok(
        request,
        {
            "slot_map": analysis["slot_map"],
            "gap_questions": analysis["gap_questions"],
            "coverage": coverage_table(analysis["slot_map"]),
            "ready_to_compose": False,
            "analyzed": True,
            "phase": project.current_phase,
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
    filled = await fill_reference_slot(body.slot_key, current_user.id)
    analysis = dict(project.analysis_json or {})
    slot_map = dict(analysis.get("slot_map") or empty_slot_map())
    slot_map[body.slot_key] = {
        "content": filled["content"],
        "status": "reference_only",
        "sources": filled["sources"],
    }
    analysis["slot_map"] = slot_map
    project.analysis_json = analysis
    await db.flush()
    return _ok(request, {"slot_key": body.slot_key, **filled, "coverage": coverage_table(slot_map)})


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
    await apply_slot_map_to_sections(db, project.id, slot_map)
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
        raise ValidationError(message="ต้องวิเคราะห์ใน Phase 1 ก่อนจึงจะคุยต่อได้", field="analyzed")
    room = await _ensure_intake_room(db, project, current_user)
    analysis = dict(project.analysis_json or {})
    slot_map = slot_map_of(project)
    brief = build_phase2_opening(slot_map, list(analysis.get("gap_questions") or []))
    asking = next_asking_slot(slot_map)
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
        analysis["current_asking_slot"] = asking
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
    filled = await fill_non_fact_reference_slots(project, current_user.id)
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
    analysis = dict(project.analysis_json or {})
    analysis["phase4_confirmed"] = True
    project.analysis_json = analysis
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
    if asking and fill_current_slot(slot_map, asking, body.content):
        filled_keys.append(asking)
        asking = next_asking_slot(slot_map)
    analysis["slot_map"] = slot_map
    analysis["current_asking_slot"] = asking
    project.analysis_json = analysis
    await db.flush()
    request_id = (
        request.headers.get("X-AI-Request-Id") or str(uuid.uuid4())
    ).strip()

    async def generate() -> AsyncIterator[str]:
        import asyncio

        result, citations, degraded = await hybrid_retrieve(
            body.content,
            user_id=current_user.id,
            search_scope=(
                body.search_scope if body.search_scope in {"global", "mine", "both"} else "both"
            ),
            top_k=5,
        )
        context = "\n\n".join(
            f"[{c.source_document or 'คลัง'}] {c.text}" for c in result.chunks[:5]
        )
        current_slot = analysis.get("current_asking_slot")
        slot_label = INTAKE_SLOT_LABELS.get(current_slot or "", "")
        slot_instruction = ""
        if current_slot:
            slot_instruction = (
                f"\nกำลังถามช่องถัดไป: {slot_label} ({current_slot})\n"
                "ทวนช่องที่เพิ่งบันทึก แล้วถามเฉพาะช่องนี้\n"
            )
        elif not missing_fact_keys(slot_map):
            slot_instruction = "\nข้อเท็จจริงครบแล้ว เชิญยืนยันไปร่าง TOR\n"
        user = (
            "ผลวิเคราะห์ Phase 1 (อย่าถามซ้ำช่องที่ได้แล้ว):\n"
            f"{slot_map_for_prompt(slot_map)}\n"
            f"{slot_instruction}"
            f"บริบทกฎหมาย:\n{context}\n\n"
            f"ข้อความผู้ใช้:\n{body.content}"
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
                async with admit(redis, "llm", request_id, on_wait=on_wait):
                    await event_q.put(("started", {"request_id": request_id}))
                    llm = ProviderFactory().get_llm()
                    async for token in llm.stream(
                        [
                            {"role": "system", "content": INTAKE_CHAT_SYSTEM},
                            {"role": "user", "content": user},
                        ],
                        temperature=0.2,
                        max_tokens=2048,
                    ):
                        parts_local.append(token)
                        await event_q.put(("token", {"text": token}))
                full_text = "".join(parts_local)
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
