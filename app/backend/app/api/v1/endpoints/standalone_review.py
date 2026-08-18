"""Standalone TOR review (upload existing TOR, not wizard Step 7)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db
from app.domain.extraction_map import map_extracted_text
from app.exceptions import NotFoundError, ValidationError
from app.io_temp import unlink_path, write_temp_bytes
from app.models.project import Project
from app.models.tor_section import TORSection
from app.models.user import User
from app.orchestrator.graph import _create_rule_engine
from app.rag.extraction import extract_text
from app.schemas.responses import MetaInfo, SuccessResponse

router = APIRouter()

_REVIEW_JOBS: dict[str, dict[str, Any]] = {}
_COMPARE_LIMIT = 5


class CompareRequest(BaseModel):
    """Compare saved projects and/or standalone extract jobs (Jaccard)."""

    project_ids: list[uuid.UUID] = Field(default_factory=list)
    extract_ids: list[str] = Field(default_factory=list)


def _envelope(request: Request, data: object, status_code: int = 200) -> JSONResponse:
    payload = SuccessResponse(
        ok=True,
        data=data,
        meta=MetaInfo(
            request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def _token_set(value: str) -> set[str]:
    """Split text into tokens of length > 1 (spaces/newlines as separators)."""
    return {part for part in value.replace("\n", " ").split(" ") if len(part) > 1}


def _jaccard(left: str, right: str) -> float:
    """Return Jaccard similarity of token sets; 0.0 when both sides are empty."""
    left_tokens, right_tokens = _token_set(left), _token_set(right)
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return len(left_tokens & right_tokens) / len(union)


def _pairwise_jaccard(
    ids: list[str],
    names: list[str],
    texts: list[str],
) -> list[dict[str, Any]]:
    """Pairwise Jaccard scores for collected compare documents."""
    scores: list[dict[str, Any]] = []
    count = len(texts)
    for i in range(count):
        for j in range(i + 1, count):
            scores.append(
                {
                    "left": names[i],
                    "right": names[j],
                    "left_id": ids[i],
                    "right_id": ids[j],
                    "jaccard": round(_jaccard(texts[i], texts[j]), 4),
                }
            )
    return scores


def _extract_compare_item(job_id: str) -> tuple[str, str, str] | None:
    """Return (id, display name, text) for a POST /review/extract job."""
    job = _REVIEW_JOBS.get(job_id)
    if job is None:
        return None
    name = str(job.get("filename") or job_id)
    text = str(job.get("extracted_text") or "")
    return (job_id, name, text)


async def _project_compare_item(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> tuple[str, str, str] | None:
    """Return (id, name, concatenated section text) for a saved project."""
    project = (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if project is None:
        return None
    sections = (
        await db.execute(select(TORSection).where(TORSection.project_id == project_id))
    ).scalars().all()
    text = " ".join(section.content or "" for section in sections)
    return (str(project_id), project.name, text)


async def _collect_compare_documents(
    db: AsyncSession,
    project_ids: list[uuid.UUID],
    extract_ids: list[str],
    limit: int = _COMPARE_LIMIT,
) -> list[tuple[str, str, str]]:
    """Resolve up to ``limit`` compare documents from projects then extract jobs."""
    items: list[tuple[str, str, str]] = []
    for project_id in project_ids:
        if len(items) >= limit:
            return items
        item = await _project_compare_item(db, project_id)
        if item is not None:
            items.append(item)
    for job_id in extract_ids:
        if len(items) >= limit:
            return items
        item = _extract_compare_item(job_id)
        if item is not None:
            items.append(item)
    return items


@router.post("/extract")
async def extract_review_document(
    request: Request,
    file: UploadFile,
    _: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    raw = await file.read()
    if not raw:
        raise ValidationError(message="ไฟล์ว่างเปล่า")
    suffix = Path(file.filename or "upload.bin").suffix or ".bin"
    mime = file.content_type or "application/octet-stream"
    tmp_path = await write_temp_bytes(raw, suffix)
    try:
        result = extract_text(tmp_path, mime)
        text = result.text
    finally:
        await unlink_path(tmp_path)
    job_id = str(uuid.uuid4())
    _REVIEW_JOBS[job_id] = {
        "id": job_id,
        "filename": file.filename,
        "extracted_text": text,
        "status": "extracted",
        "result": None,
    }
    return _envelope(
        request,
        {"id": job_id, "extracted_text": text[:20000], "status": "extracted"},
    )


@router.post("/run")
async def run_standalone_review(
    request: Request,
    body: dict,
    _: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    job_id = body.get("id") or body.get("review_id")
    text = body.get("text") or ""
    job = _REVIEW_JOBS.get(job_id) if job_id else None
    if job:
        text = job.get("extracted_text") or text
    if not text:
        raise ValidationError(message="ไม่มีข้อความให้ตรวจสอบ")
    engine = _create_rule_engine()
    mapped = map_extracted_text(text)
    if not mapped:
        mapped = {"s1": text}
    document = {**mapped, "sections": mapped, "metadata": {}}
    result = engine.validate(document)
    payload = {
        "id": job_id or str(uuid.uuid4()),
        "quality_score": result.quality_score,
        "findings": [
            {
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "rule": f.rule_violated,
                "section": f.affected_section,
                "message": f.message,
                "recommendation": f.recommended_correction,
            }
            for f in result.findings
        ],
        "status": "completed",
    }
    if job_id:
        _REVIEW_JOBS[job_id]["result"] = payload
        _REVIEW_JOBS[job_id]["status"] = "completed"
    return _envelope(request, payload)


@router.get("/{review_id}")
async def get_standalone_review(
    request: Request,
    review_id: str,
    _: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    job = _REVIEW_JOBS.get(review_id)
    if not job:
        raise NotFoundError(message="ไม่พบงานตรวจสอบ")
    return _envelope(request, job.get("result") or job)


@router.post("/compare-projects")
async def compare_projects(
    request: Request,
    body: CompareRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    if len(body.project_ids) + len(body.extract_ids) < 2:
        raise ValidationError(message="ต้องระบุอย่างน้อย 2 รายการ")
    items = await _collect_compare_documents(db, body.project_ids, body.extract_ids)
    ids = [item[0] for item in items]
    names = [item[1] for item in items]
    texts = [item[2] for item in items]
    return _envelope(request, {"comparisons": _pairwise_jaccard(ids, names, texts)})
