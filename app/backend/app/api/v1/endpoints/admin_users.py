"""Admin user management endpoints."""

from __future__ import annotations

from typing import Annotated

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.constants import DISABLED_EMAIL_PREFIX
from app.deps import get_db
from app.exceptions import NotFoundError, ValidationError
from app.models.user import User
from app.rbac import require_role
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.auth_service import AuthService

router = APIRouter()


class AdminUserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    organization: str
    role: str = Field(default="officer")


class AdminUserUpdate(BaseModel):
    role: str | None = None
    disabled: bool | None = None


def _user_payload(user: User) -> dict:
    disabled = user.email.startswith(DISABLED_EMAIL_PREFIX)
    return {
        "id": str(user.id),
        "name": user.name,
        "email": user.email.replace(DISABLED_EMAIL_PREFIX, "", 1) if disabled else user.email,
        "organization": user.organization,
        "role": user.role,
        "disabled": disabled,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.get("")
async def list_users(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
) -> JSONResponse:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    payload = SuccessResponse(
        ok=True,
        data={"items": [_user_payload(u) for u in users]},
        meta=MetaInfo(
            request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )
    return JSONResponse(content=payload.model_dump(mode="json"))


@router.post("")
async def create_user(
    request: Request,
    body: AdminUserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
) -> JSONResponse:
    if body.role not in ("officer", "reviewer", "admin"):
        raise ValidationError(message="บทบาทไม่ถูกต้อง", field="role")
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise ValidationError(message="อีเมลนี้ถูกใช้แล้ว", field="email")
    violations = AuthService.validate_password_policy(body.password)
    if violations:
        raise ValidationError(message=violations[0], field="password")
    user = User(
        name=body.name,
        email=body.email,
        password_hash=AuthService.hash_password(body.password),
        organization=body.organization,
        role=body.role,
    )
    db.add(user)
    await db.flush()
    payload = SuccessResponse(
        ok=True,
        data=_user_payload(user),
        meta=MetaInfo(
            request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )
    return JSONResponse(status_code=201, content=payload.model_dump(mode="json"))


@router.put("/{user_id}")
async def update_user(
    request: Request,
    user_id: uuid.UUID,
    body: AdminUserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
) -> JSONResponse:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise NotFoundError(message="ไม่พบผู้ใช้")
    if body.role:
        if body.role not in ("officer", "reviewer", "admin"):
            raise ValidationError(message="บทบาทไม่ถูกต้อง", field="role")
        user.role = body.role
    if body.disabled is True and not user.email.startswith(DISABLED_EMAIL_PREFIX):
        user.email = f"{DISABLED_EMAIL_PREFIX}{user.email}"
    if body.disabled is False and user.email.startswith(DISABLED_EMAIL_PREFIX):
        user.email = user.email.replace(DISABLED_EMAIL_PREFIX, "", 1)
    await db.flush()
    payload = SuccessResponse(
        ok=True,
        data=_user_payload(user),
        meta=MetaInfo(
            request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )
    return JSONResponse(content=payload.model_dump(mode="json"))
