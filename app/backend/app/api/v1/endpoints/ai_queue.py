"""AI admission queue status endpoint."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.deps import get_current_user
from app.llm_admission import get_queue_status
from app.models.user import User
from app.schemas.responses import MetaInfo, SuccessResponse

router = APIRouter()


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


@router.get("/queue/{request_id}")
async def ai_queue_status(
    request: Request,
    request_id: str,
    _: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    redis = getattr(request.app.state, "redis", None)
    return _ok(request, await get_queue_status(redis, request_id))
