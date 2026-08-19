"""Agent TOR drafting session endpoints."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db, get_minio
from app.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.models.agent_session import AgentSession
from app.models.project import Project
from app.models.user import User
from app.rbac import require_project_access
from app.schemas.agent import (
    AnswerRequest,
    AnswerResponse,
    ConfirmRequest,
    CoverageResponse,
    CreateSessionResponse,
    DraftResponse,
    ExportResponse,
    ReviewRequest,
    StatusResponse,
)
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.agent_workflow import (
    default_state,
    load_state,
    persist_state,
    run_answer,
    run_confirm,
    run_review,
    run_start,
)

logger = logging.getLogger("tor_app.agent_api")
router = APIRouter()

SESSION_NOT_FOUND = "ไม่พบเซสชันที่ต้องการ"
MIN_TEXT = 50


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


async def _get_owned_session(
    db: AsyncSession, session_id: uuid.UUID, user: User
) -> tuple[AgentSession, Project]:
    row = (
        await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError(SESSION_NOT_FOUND)
    project = (
        await db.execute(select(Project).where(Project.id == row.project_id))
    ).scalar_one_or_none()
    if project is None:
        raise NotFoundError(SESSION_NOT_FOUND)
    require_project_access(project.owner_id, user)
    if row.user_id != user.id and user.role not in {"admin", "reviewer"}:
        raise AuthorizationError(message="คุณไม่มีสิทธิ์เข้าถึงเซสชันนี้")
    return row, project


def _create_payload(state: dict) -> dict:
    return CreateSessionResponse(
        session_id=uuid.UUID(str(state["session_id"])),
        project_id=uuid.UUID(str(state["project_id"])),
        phase=str(state.get("phase") or "idle"),
        coverage_map=list(state.get("coverage_map") or []),
        readiness_score=float(state.get("readiness_score") or 0),
        ready=bool(state.get("ready")),
        gap_questions=list(state.get("gap_questions") or []),
        warnings=list(state.get("warnings") or []),
        error=state.get("error"),
    ).model_dump(mode="json")


@router.post("/sessions")
async def create_session(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    files: Annotated[list[UploadFile] | None, File()] = None,
    free_text: Annotated[str | None, Form()] = None,
    name: Annotated[str | None, Form()] = None,
    ministry: Annotated[str | None, Form()] = None,
    budget: Annotated[int | None, Form()] = None,
    project_type: Annotated[str | None, Form()] = None,
    project_id: Annotated[uuid.UUID | None, Form()] = None,
) -> JSONResponse:
    uploads = list(files or [])
    text = (free_text or "").strip()
    if not uploads and len(text) < MIN_TEXT:
        raise ValidationError(
            message="ต้องอัปโหลดเอกสารหรือวางข้อความอย่างน้อย 50 ตัวอักษร",
            field="free_text",
        )
    if project_id is not None:
        project = (
            await db.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        if project is None:
            raise NotFoundError("ไม่พบโครงการที่ต้องการ")
        require_project_access(project.owner_id, current_user)
        project.workflow_mode = "agent"
    else:
        project = Project(
            owner_id=current_user.id,
            name=(name or "โครงการ TOR (Agent)").strip() or "โครงการ TOR (Agent)",
            ministry=(ministry or current_user.organization or "ไม่ระบุ").strip(),
            budget=int(budget or 1),
            project_type=project_type or "general",
            current_step=0,
            workflow_mode="agent",
        )
        db.add(project)
        await db.flush()
    session = AgentSession(project_id=project.id, user_id=current_user.id, phase="ingesting")
    db.add(session)
    await db.flush()
    state = default_state(
        session.id,
        project.id,
        current_user.id,
        {
            "name": project.name,
            "ministry": project.ministry,
            "budget": project.budget,
            "project_type": project.project_type,
        },
    )
    state["pending_files"] = uploads
    state["free_text"] = text
    try:
        get_minio(request)
        state["storage_backend"] = "minio"
    except HTTPException:
        state["storage_backend"] = "local"
    state = await run_start(state)
    await persist_state(db, session, state)
    return _ok(request, _create_payload(state), status_code=201)


@router.post("/sessions/{session_id}/ingest")
async def ingest_more(
    request: Request,
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    files: Annotated[list[UploadFile] | None, File()] = None,
    free_text: Annotated[str | None, Form()] = None,
) -> JSONResponse:
    row, _project = await _get_owned_session(db, session_id, current_user)
    state = load_state(row)
    state["pending_files"] = list(files or [])
    state["free_text"] = (free_text or "").strip()
    state = await run_start(state)
    await persist_state(db, row, state)
    return _ok(request, _create_payload(state))


@router.get("/sessions/{session_id}/status")
async def session_status(
    request: Request,
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    row, _project = await _get_owned_session(db, session_id, current_user)
    state = load_state(row)
    payload = StatusResponse(
        session_id=row.id,
        project_id=row.project_id,
        phase=str(state.get("phase") or row.phase),
        readiness_score=float(state.get("readiness_score") or 0),
        ready=bool(state.get("ready")),
        gap_iteration=int(state.get("gap_iteration") or 0),
        warnings=list(state.get("warnings") or []),
        error=state.get("error"),
    )
    return _ok(request, payload.model_dump(mode="json"))


@router.delete("/sessions/{session_id}")
async def delete_session(
    request: Request,
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    row, _project = await _get_owned_session(db, session_id, current_user)
    await db.delete(row)
    return _ok(request, {"deleted": True, "session_id": str(session_id)})


@router.get("/sessions/{session_id}/coverage")
async def coverage(
    request: Request,
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    row, _project = await _get_owned_session(db, session_id, current_user)
    state = load_state(row)
    payload = CoverageResponse(
        coverage_map=list(state.get("coverage_map") or []),
        readiness_score=float(state.get("readiness_score") or 0),
        ready=bool(state.get("ready")),
        gap_questions=list(state.get("gap_questions") or []),
        phase=str(state.get("phase") or row.phase),
    )
    return _ok(request, payload.model_dump(mode="json"))


@router.post("/sessions/{session_id}/answer")
async def answer(
    request: Request,
    session_id: uuid.UUID,
    body: AnswerRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    row, _project = await _get_owned_session(db, session_id, current_user)
    before = set()
    state = load_state(row)
    for key, slot in (state.get("slot_map") or {}).items():
        if isinstance(slot, dict) and slot.get("status") == "filled":
            before.add(key)
    state = await run_answer(state, body.answer)
    after = set()
    for key, slot in (state.get("slot_map") or {}).items():
        if isinstance(slot, dict) and slot.get("status") == "filled":
            after.add(key)
    await persist_state(db, row, state)
    payload = AnswerResponse(
        coverage_map=list(state.get("coverage_map") or []),
        readiness_score=float(state.get("readiness_score") or 0),
        ready=bool(state.get("ready")),
        gap_questions=list(state.get("gap_questions") or []),
        affected_slots=sorted(after - before),
        phase=str(state.get("phase") or row.phase),
        gap_iteration=int(state.get("gap_iteration") or 0),
    )
    return _ok(request, payload.model_dump(mode="json"))


@router.post("/sessions/{session_id}/confirm")
async def confirm(
    request: Request,
    session_id: uuid.UUID,
    body: ConfirmRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    row, _project = await _get_owned_session(db, session_id, current_user)
    state = await run_confirm(load_state(row), body.user_confirmed)
    await persist_state(db, row, state)
    payload = DraftResponse(
        section_drafts=dict(state.get("section_drafts") or {}),
        quality_scores=dict(state.get("draft_quality_scores") or {}),
        overall_quality_score=float(state.get("overall_quality_score") or 0),
        validation_findings=list(state.get("validation_findings") or []),
        warnings=list(state.get("warnings") or []),
        phase=str(state.get("phase") or row.phase),
        mandatory_review_sections=list(state.get("mandatory_review_sections") or []),
    )
    return _ok(request, payload.model_dump(mode="json"))


@router.get("/sessions/{session_id}/draft")
async def get_draft(
    request: Request,
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    row, _project = await _get_owned_session(db, session_id, current_user)
    state = load_state(row)
    payload = DraftResponse(
        section_drafts=dict(state.get("section_drafts") or {}),
        quality_scores=dict(state.get("draft_quality_scores") or {}),
        overall_quality_score=float(state.get("overall_quality_score") or 0),
        validation_findings=list(state.get("validation_findings") or []),
        warnings=list(state.get("warnings") or []),
        phase=str(state.get("phase") or row.phase),
        mandatory_review_sections=list(state.get("mandatory_review_sections") or []),
    )
    return _ok(request, payload.model_dump(mode="json"))


@router.post("/sessions/{session_id}/review")
async def review(
    request: Request,
    session_id: uuid.UUID,
    body: ReviewRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    row, _project = await _get_owned_session(db, session_id, current_user)
    state = await run_review(
        load_state(row),
        body.human_approved,
        body.human_feedback,
        body.acknowledged_sections,
    )
    await persist_state(db, row, state)
    payload = ExportResponse(
        docx_url=state.get("export_docx_url"),
        pdf_url=state.get("export_pdf_url"),
        phase=str(state.get("phase") or row.phase),
        error=state.get("error"),
    )
    return _ok(request, payload.model_dump(mode="json"))


@router.get("/sessions/{session_id}/export")
async def get_export(
    request: Request,
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    row, _project = await _get_owned_session(db, session_id, current_user)
    state = load_state(row)
    required = {"s3", "s6", "s8", "s10", "s13"}
    acknowledged = set(state.get("sections_acknowledged") or [])
    if state.get("phase") != "complete" and not required.issubset(acknowledged):
        raise ValidationError(message="ต้องยืนยันหมวดที่ต้องตรวจก่อนส่งออก")
    payload = ExportResponse(
        docx_url=state.get("export_docx_url"),
        pdf_url=state.get("export_pdf_url"),
        phase=str(state.get("phase") or row.phase),
        error=state.get("error"),
    )
    return _ok(request, payload.model_dump(mode="json"))
