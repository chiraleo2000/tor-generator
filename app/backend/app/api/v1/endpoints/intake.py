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
from app.domain.slots import INTAKE_SLOT_LABELS
from app.exceptions import NotFoundError, ValidationError
from app.io_temp import unlink_path, write_temp_bytes
from app.models.chat_message import ChatMessage
from app.models.chat_room import ChatRoom
from app.models.project import Project
from app.models.user import User
from app.providers.factory import ProviderFactory
from app.rag.document_pipeline import ingest_file_bytes
from app.rag.extraction import extract_text
from app.rag.hybrid import hybrid_retrieve
from app.rbac import require_project_access
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.intake_service import (
    analyze_pack,
    append_intake_text,
    apply_slot_map_to_sections,
    coverage_table,
    empty_slot_map,
    fill_reference_slot,
    load_project,
    merge_analysis,
    ready_criteria_met,
)

logger = logging.getLogger("tor_app.intake")
router = APIRouter()
INTAKE_PASTE_FILENAME = "ข้อความผู้ใช้.txt"
CHAT_USER_SOURCE = "ผู้ใช้ตอบในแชท"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _apply_chat_fact_to_first_gap(slot_map: dict[str, Any], user_text: str) -> None:
    answer = user_text.strip()
    if not slot_map or len(answer) <= 12:
        return
    for slot in slot_map.values():
        if not isinstance(slot, dict) or slot.get("status") != "gap":
            continue
        previous = str(slot.get("content") or "")
        slot["content"] = f"{previous}\n{answer}".strip() if previous else answer
        slot["status"] = "filled"
        sources = slot.get("sources")
        if isinstance(sources, list):
            sources.append(CHAT_USER_SOURCE)
        else:
            slot["sources"] = [CHAT_USER_SOURCE]
        return


async def _persist_intake_assistant(
    session_maker,
    project_id: uuid.UUID,
    room_id: uuid.UUID,
    slot_map: dict[str, Any],
    content: str,
    citations: list,
) -> None:
    async with session_maker() as persist:
        row = (await persist.execute(select(Project).where(Project.id == project_id))).scalar_one()
        merged = dict(row.analysis_json or {})
        merged["slot_map"] = slot_map
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
    project.analysis_json = analysis
    await db.flush()
    return _ok(
        request,
        {
            "slot_map": analysis["slot_map"],
            "gap_questions": analysis["gap_questions"],
            "coverage": coverage_table(analysis["slot_map"]),
            "ready_to_compose": False,
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
    project.current_phase = max(project.current_phase or 0, 2)
    await apply_slot_map_to_sections(db, project.id, slot_map)
    await db.flush()
    return _ok(request, {"ready_to_compose": True, "phase": project.current_phase})


@router.post("/{project_id}/intake/chat")
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
    gaps = analysis.get("gap_questions") or []

    async def generate() -> AsyncIterator[str]:
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
        system = (
            "คุณเป็นบอท intake ร่าง TOR ภาครัฐ "
            "ช่วยจัดช่อง s1-s13 และ s4.1-s4.14 ถามส่วนขาด "
            "เมื่อผู้ใช้ให้ข้อเท็จจริงโครงการ ให้สรุปว่าใส่ช่องใด "
            "กฎหมายจาก RAG ใส่เป็น Reference ไม่ใช่ข้อเท็จจริงโครงการ "
            "เมื่อครบเกณฑ์ ให้ถามว่าพร้อมร่าง TOR แล้วหรือยัง"
        )
        user = (
            f"แผนที่ช่องปัจจุบัน: {json.dumps(slot_map, ensure_ascii=False)[:8000]}\n"
            f"คำถามที่ค้าง: {gaps}\n"
            f"บริบท RAG:\n{context}\n\nข้อความผู้ใช้:\n{body.content}"
        )
        llm = ProviderFactory().get_llm()
        parts: list[str] = []
        try:
            async for token in llm.stream(
                [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                max_tokens=2048,
            ):
                parts.append(token)
                yield _sse("token", {"text": token})
        except Exception as exc:
            logger.exception("intake chat failed")
            yield _sse("error", {"message": str(exc)})
            return
        full = "".join(parts)
        _apply_chat_fact_to_first_gap(slot_map, body.content)
        await _persist_intake_assistant(
            request.app.state.db_session_factory,
            project.id,
            room.id,
            slot_map,
            full,
            citations,
        )
        yield _sse(
            "done",
            {
                "content": full,
                "citations": citations,
                "coverage": coverage_table(slot_map),
                "graph_degraded": degraded,
            },
        )

    return StreamingResponse(generate(), media_type="text/event-stream")
