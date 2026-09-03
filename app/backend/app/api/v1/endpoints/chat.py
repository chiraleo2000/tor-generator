"""KB and draft-intake chat rooms with SSE streaming."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, AsyncIterator

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import infra as runtime
from app.api.v1.endpoints.knowledge_base import _validate_kb_bytes
from app.deps import get_current_user, get_db
from app.domain.corpus import GROUP_USER
from app.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.llm_admission import AdmissionTimeoutError, admit
from app.models.chat_message import ChatMessage
from app.models.chat_prompt_template import ChatPromptTemplate
from app.models.chat_room import ChatRoom
from app.models.user import User
from app.providers.factory import ProviderFactory
from app.rag.document_pipeline import ingest_file_bytes
from app.rag.hybrid import unpack_hybrid
from app.rag.hybrid import hybrid_retrieve_multi as hybrid_retrieve
from app.rag.kb_qa import (
    CHAT_MAX_TOKENS,
    DRAFT_INTAKE_CONTEXT_CHUNKS,
    DRAFT_INTAKE_MAX_TOKENS,
    DRAFT_INTAKE_SYSTEM,
    DRAFT_INTAKE_TOP_K,
    build_kb_qa_messages,
    chat_rag_top_k,
    trim_history,
)
from app.rate_limiter import rate_limit_ai
from app.schemas.responses import MetaInfo, SuccessResponse

logger = logging.getLogger("tor_app.chat")
router = APIRouter()

KIND_KB = "kb"
KIND_DRAFT_INTAKE = "draft_intake"
VALID_KINDS = frozenset({KIND_KB, KIND_DRAFT_INTAKE})
VALID_SCOPES = frozenset({"global", "mine", "both"})
INVALID_KIND_MESSAGE = "ชนิดห้องไม่ถูกต้อง"
DEFAULT_ROOM_TITLE = "ห้องใหม่"


class RoomCreate(BaseModel):
    kind: str = KIND_KB
    title: str | None = None
    project_id: uuid.UUID | None = None


class RoomRename(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)


class SendMessage(BaseModel):
    content: str = Field(..., min_length=1)
    search_scope: str = "both"


def _ok(request: Request, data: Any, status_code: int = 200) -> JSONResponse:
    payload = SuccessResponse(
        ok=True,
        data=data,
        meta=MetaInfo(
            request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def _last_loaded_message(room: ChatRoom) -> ChatMessage | None:
    try:
        unloaded = sa_inspect(room).unloaded
    except NoInspectionAvailable:
        messages = list(getattr(room, "messages", None) or [])
        return messages[-1] if messages else None
    if "messages" in unloaded:
        return None
    messages = room.messages
    return messages[-1] if messages else None


def _room_card(room: ChatRoom) -> dict[str, Any]:
    last = _last_loaded_message(room)
    preview = (last.content[:80] if last else "")
    return {
        "id": str(room.id),
        "kind": room.kind,
        "project_id": str(room.project_id) if room.project_id else None,
        "title": room.title,
        "updated_at": room.updated_at.isoformat() if room.updated_at else None,
        "last_message": preview,
        "last_role": last.role if last else None,
    }


async def _owned_room(
    db: AsyncSession, room_id: uuid.UUID, user: User
) -> ChatRoom:
    room = (
        await db.execute(
            select(ChatRoom)
            .options(selectinload(ChatRoom.messages))
            .where(ChatRoom.id == room_id)
        )
    ).scalar_one_or_none()
    if room is None:
        raise NotFoundError(message="ไม่พบห้องแชท")
    if room.user_id != user.id:
        raise AuthorizationError(message="ไม่มีสิทธิ์เข้าถึงห้องนี้")
    return room


def _require_valid_kind(kind: str) -> None:
    if kind not in VALID_KINDS:
        raise ValidationError(message=INVALID_KIND_MESSAGE, field="kind")


@router.get("/rooms")
async def list_rooms(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    kind: str = KIND_KB,
    project_id: uuid.UUID | None = None,
) -> JSONResponse:
    _require_valid_kind(kind)
    stmt = (
        select(ChatRoom)
        .options(selectinload(ChatRoom.messages))
        .where(ChatRoom.user_id == current_user.id, ChatRoom.kind == kind)
    )
    if project_id is not None:
        stmt = stmt.where(ChatRoom.project_id == project_id)
    rows = (
        (await db.execute(stmt.order_by(ChatRoom.updated_at.desc()))).scalars().all()
    )
    return _ok(request, {"rooms": [_room_card(item) for item in rows]})


@router.post("/rooms")
async def create_room(
    request: Request,
    body: RoomCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    _require_valid_kind(body.kind)
    if body.kind == KIND_DRAFT_INTAKE and body.project_id is None:
        raise ValidationError(message="ห้องร่างต้องระบุโครงการ", field="project_id")
    title = (body.title or DEFAULT_ROOM_TITLE).strip() or DEFAULT_ROOM_TITLE
    if body.kind == KIND_DRAFT_INTAKE and body.project_id is not None:
        existing = (
            await db.execute(
                select(ChatRoom).where(
                    ChatRoom.user_id == current_user.id,
                    ChatRoom.kind == KIND_DRAFT_INTAKE,
                    ChatRoom.project_id == body.project_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            loaded = await _owned_room(db, existing.id, current_user)
            return _ok(request, _room_card(loaded))
    room = ChatRoom(
        user_id=current_user.id,
        kind=body.kind,
        project_id=body.project_id,
        title=title[:255],
    )
    db.add(room)
    await db.flush()
    return _ok(request, _room_card(room), status_code=201)


@router.patch("/rooms/{room_id}")
async def rename_room(
    request: Request,
    room_id: uuid.UUID,
    body: RoomRename,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    room = await _owned_room(db, room_id, current_user)
    room.title = body.title.strip()[:255]
    await db.flush()
    return _ok(request, _room_card(room))


@router.delete("/rooms/{room_id}")
async def delete_room(
    request: Request,
    room_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    room = await _owned_room(db, room_id, current_user)
    await db.delete(room)
    await db.flush()
    return _ok(request, {"id": str(room_id), "deleted": True})


@router.get("/rooms/{room_id}/messages")
async def list_messages(
    request: Request,
    room_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    room = await _owned_room(db, room_id, current_user)
    messages = [
        {
            "id": str(item.id),
            "role": item.role,
            "content": item.content,
            "citations": item.citations or [],
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }
        for item in room.messages
    ]
    return _ok(request, {"room": _room_card(room), "messages": messages})


@router.get("/prompts")
async def list_prompts(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
    kind: str = KIND_KB,
) -> JSONResponse:
    _require_valid_kind(kind)
    rows = (
        (
            await db.execute(
                select(ChatPromptTemplate)
                .where(ChatPromptTemplate.kind == kind)
                .order_by(ChatPromptTemplate.sort_order)
            )
        )
        .scalars()
        .all()
    )
    return _ok(
        request,
        {
            "prompts": [
                {"id": str(item.id), "title": item.title, "body": item.body}
                for item in rows
            ]
        },
    )


@router.post("/rooms/{room_id}/attachments")
async def upload_attachment(
    request: Request,
    room_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: Annotated[UploadFile, File()],
) -> JSONResponse:
    room = await _owned_room(db, room_id, current_user)
    content = await file.read()
    if not content:
        raise ValidationError(message="ไฟล์ว่าง", field="file")
    mime = _validate_kb_bytes(content, file.content_type or "", file.filename or "")
    factory = runtime.session_factory or request.app.state.db_session_factory
    doc = await ingest_file_bytes(
        db=db,
        filename=file.filename or "upload.bin",
        content=content,
        mime_type=mime,
        scope="user",
        owner_id=current_user.id,
        project_id=str(room.project_id) if room.project_id else None,
        session_factory=factory,
        corpus_group=GROUP_USER,
        category="other",
    )
    status = doc.processing_status
    return _ok(
        request,
        {
            "document_id": str(doc.id),
            "name": doc.name,
            "status": status,
            "processing_status": status,
            "chunk_count": doc.chunk_count,
        },
    )


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _intake_messages(question: str, chunks: Any, degraded: bool) -> list[dict[str, str]]:
    context_bits = [
        f"[{chunk.source_document or 'คลัง'}] {chunk.text}" for chunk in chunks
    ]
    system = DRAFT_INTAKE_SYSTEM
    if degraded:
        system += " (กราฟ Neo4j ไม่พร้อม ใช้เฉพาะชิ้นข้อความ)"
    return [
        {"role": "system", "content": system},
        {
            "role": "user",
            "content": (
                "บริบทจากคลังความรู้:\n"
                + "\n\n".join(context_bits[:DRAFT_INTAKE_CONTEXT_CHUNKS])
                + "\n\nคำถาม:\n"
                + question
            ),
        },
    ]


def _room_llm_messages(
    *,
    is_kb: bool,
    question: str,
    chunks: Any,
    history: list[dict[str, str]],
    degraded: bool,
) -> list[dict[str, str]]:
    if is_kb:
        return build_kb_qa_messages(
            question=question,
            chunks=chunks,
            history=history,
            degraded=degraded,
        )
    return _intake_messages(question, chunks, degraded)


async def _persist_assistant_reply(
    session_factory: Any,
    room_id: uuid.UUID,
    content: str,
    citations: Any,
) -> None:
    async with session_factory() as persist:
        persist.add(
            ChatMessage(
                room_id=room_id,
                role="assistant",
                content=content,
                citations=citations,
            )
        )
        await persist.commit()


def _queued_event(event_q: Any, request_id: str):
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

    return on_wait


async def _run_chat_llm(
    *,
    redis: Any,
    request_id: str,
    event_q: Any,
    messages: list[dict[str, str]],
    max_tokens: int,
    session_factory: Any,
    room_id: uuid.UUID,
    citations: Any,
    degraded: bool,
    mcp_degraded: bool = False,
) -> None:
    parts_local: list[str] = []
    try:
        async with admit(redis, "llm", request_id, on_wait=_queued_event(event_q, request_id)):
            await event_q.put(("started", {"request_id": request_id}))
            llm = ProviderFactory().get_llm()
            async for token in llm.stream(
                messages,
                temperature=0.2,
                max_tokens=max_tokens,
            ):
                parts_local.append(token)
                await event_q.put(("token", {"text": token}))
        full_text = "".join(parts_local)
        await _persist_assistant_reply(session_factory, room_id, full_text, citations)
        await event_q.put(
            (
                "done",
                {
                    "content": full_text,
                    "citations": citations,
                    "graph_degraded": degraded,
                    "mcp_degraded": mcp_degraded,
                },
            )
        )
    except AdmissionTimeoutError as exc:
        await event_q.put(("error", {"message": str(exc)}))
    except Exception as exc:
        logger.exception("chat stream failed")
        await event_q.put(("error", {"message": str(exc)}))
    finally:
        await event_q.put(None)


async def _iter_chat_sse(
    *,
    request: Request,
    room: ChatRoom,
    user: User,
    question: str,
    scope: str,
    prior: list[dict[str, str]],
    is_kb: bool,
    top_k: int,
    max_tokens: int,
    request_id: str,
) -> AsyncIterator[str]:
    import asyncio

    result, citations, degraded, mcp_degraded = unpack_hybrid(
        await hybrid_retrieve(
            question,
            user_id=user.id,
            search_scope=scope,
            top_k=top_k,
        )
    )
    messages = _room_llm_messages(
        is_kb=is_kb,
        question=question,
        chunks=result.chunks,
        history=prior,
        degraded=degraded,
    )
    event_q: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()
    task = asyncio.create_task(
        _run_chat_llm(
            redis=getattr(request.app.state, "redis", None),
            request_id=request_id,
            event_q=event_q,
            messages=messages,
            max_tokens=max_tokens,
            session_factory=request.app.state.db_session_factory,
            room_id=room.id,
            citations=citations,
            degraded=degraded,
            mcp_degraded=mcp_degraded,
        )
    )
    try:
        while True:
            item = await event_q.get()
            if item is None:
                break
            event_name, payload = item
            yield _sse(event_name, payload)
    finally:
        await task


@router.post("/rooms/{room_id}/messages", dependencies=[Depends(rate_limit_ai)])
async def send_message(
    request: Request,
    room_id: uuid.UUID,
    body: SendMessage,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    room = await _owned_room(db, room_id, current_user)
    scope = body.search_scope if body.search_scope in VALID_SCOPES else "both"
    user_msg = ChatMessage(room_id=room.id, role="user", content=body.content, citations=[])
    db.add(user_msg)
    await db.flush()
    if room.title == DEFAULT_ROOM_TITLE:
        room.title = body.content[:60]
    room.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    prior = trim_history(
        [
            {"role": item.role, "content": item.content}
            for item in room.messages
            if getattr(item, "id", None) != user_msg.id
        ]
    )
    is_kb = room.kind == KIND_KB
    top_k = chat_rag_top_k() if is_kb else DRAFT_INTAKE_TOP_K
    max_tokens = CHAT_MAX_TOKENS if is_kb else DRAFT_INTAKE_MAX_TOKENS
    request_id = (
        request.headers.get("X-AI-Request-Id") or str(uuid.uuid4())
    ).strip()
    return StreamingResponse(
        _iter_chat_sse(
            request=request,
            room=room,
            user=current_user,
            question=body.content,
            scope=scope,
            prior=prior,
            is_kb=is_kb,
            top_k=top_k,
            max_tokens=max_tokens,
            request_id=request_id,
        ),
        media_type="text/event-stream",
    )
