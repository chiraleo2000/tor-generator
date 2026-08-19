"""Knowledge-base chat endpoints (separate from /chat rooms)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.exceptions import NotFoundError, ValidationError
from app.models.user import User
from app.schemas.kb_chat import (
    CreateKBChatSessionResponse,
    KBChatHistoryResponse,
    KBChatMessageRequest,
    KBChatMessageResponse,
)
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.kb_chat_service import MAX_MESSAGE_LENGTH, KnowledgeChatService

router = APIRouter()
SESSION_NOT_FOUND = "ไม่พบเซสชันแชท หรือหมดเวลาแล้ว"


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


@router.post("/sessions")
async def create_kb_session(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    service = KnowledgeChatService()
    row = await service.create_session(db, current_user.id)
    payload = CreateKBChatSessionResponse(session_id=row.id)
    return _ok(request, payload.model_dump(mode="json"), status_code=201)


@router.post("/sessions/{session_id}/message")
async def send_message(
    request: Request,
    session_id: uuid.UUID,
    body: KBChatMessageRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    if len(body.message) > MAX_MESSAGE_LENGTH:
        raise ValidationError(message="ข้อความยาวเกิน 1000 ตัวอักษร", field="message")
    service = KnowledgeChatService()
    row = await service.load_session(db, session_id, current_user.id)
    if row is None:
        raise NotFoundError(SESSION_NOT_FOUND)
    result = await service.answer(
        session_id, current_user.id, body.message, list(row.history or []), db
    )
    payload = KBChatMessageResponse(
        answer=result.answer,
        citations=result.citations,
        no_results=result.no_results,
    )
    return _ok(request, payload.model_dump(mode="json"))


@router.get("/sessions/{session_id}/history")
async def history(
    request: Request,
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    service = KnowledgeChatService()
    row = await service.load_session(db, session_id, current_user.id)
    if row is None:
        raise NotFoundError(SESSION_NOT_FOUND)
    payload = KBChatHistoryResponse(messages=list(row.history or []))
    return _ok(request, payload.model_dump(mode="json"))
