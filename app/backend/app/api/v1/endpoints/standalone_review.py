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
from app.domain.extraction_map import infer_review_budget, map_extracted_text
from app.exceptions import NotFoundError, ValidationError
from app.io_temp import unlink_path, write_temp_bytes
from app.models.project import Project
from app.models.review_job import ReviewJob
from app.models.tor_section import TORSection
from app.models.user import User
from app.orchestrator.graph import _create_rule_engine
from app.rag.extraction import extract_text
from app.rule_engine.engine import (
    KIND_LEGAL,
    KIND_RISK,
    Finding,
    Severity,
    attach_legal_basis,
    finding_as_dict,
    first_law_citation,
)
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.review_job_store import (
    fetch_review_job,
    save_review_job,
    save_review_result,
    store_review_original,
)

router = APIRouter()

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


def _job_preview(job: ReviewJob) -> dict[str, Any]:
    result = job.result_json if isinstance(job.result_json, dict) else {}
    preview = dict(result)
    preview["id"] = str(job.id)
    preview["filename"] = job.filename
    preview["extracted_text"] = (job.extracted_text or "")[:20000]
    preview["status"] = str(result.get("status") or job.status)
    return preview


async def _extract_compare_item(
    db: AsyncSession,
    owner_id: uuid.UUID,
    job_id: str,
) -> tuple[str, str, str] | None:
    """Return (id, display name, text) for a POST /review/extract job."""
    try:
        parsed = uuid.UUID(str(job_id))
    except ValueError:
        return None
    job = await fetch_review_job(db, parsed, owner_id)
    if job is None:
        return None
    name = str(job.filename or job_id)
    text = str(job.extracted_text or "")
    return (str(job.id), name, text)


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
    owner_id: uuid.UUID,
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
        item = await _extract_compare_item(db, owner_id, job_id)
        if item is not None:
            items.append(item)
    return items


def _validate_document(text: str) -> tuple[Any, dict[str, Any]]:
    engine = _create_rule_engine()
    mapped = map_extracted_text(text)
    if not mapped:
        mapped = {"s1": text}
    metadata: dict[str, object] = {}
    document: dict[str, Any] = {**mapped, "sections": mapped, "metadata": metadata}
    budget = infer_review_budget(text, mapped)
    if budget is not None:
        document["budget"] = budget
        metadata["budget"] = budget
    return engine.validate(document), document


def _run_engine(text: str, job_id: str) -> dict[str, Any]:
    result, _document = _validate_document(text)
    attach_legal_basis(result.findings, "")
    return {
        "id": job_id,
        "quality_score": result.quality_score,
        "findings": [finding_as_dict(f, aliases=True) for f in result.findings],
        "status": "completed",
        "overall_assessment": "",
    }


def _suggestion_as_finding(suggestion: Any, rag_text: str) -> dict[str, Any]:
    kind = str(getattr(suggestion, "finding_kind", "") or KIND_RISK)
    if kind not in {KIND_LEGAL, KIND_RISK}:
        kind = KIND_RISK
    basis = str(getattr(suggestion, "legal_basis", "") or "")
    if kind == KIND_LEGAL and not basis:
        basis = first_law_citation(rag_text)
    finding = Finding(
        severity=Severity.WARNING,
        rule_violated=f"REVIEW_{str(getattr(suggestion, 'category', 'ai')).upper()}",
        affected_section=str(getattr(suggestion, "section_key", "s1") or "s1"),
        message=str(getattr(suggestion, "suggested_text", "") or "")[:280],
        recommended_correction=str(getattr(suggestion, "suggested_text", "") or ""),
        finding_kind=kind,
        legal_basis=basis or None,
        excerpt=str(getattr(suggestion, "current_text", "") or "")[:180] or None,
        risk_type=str(getattr(suggestion, "risk_type", "") or "") or None,
    )
    return finding_as_dict(finding, aliases=True)


async def _law_context() -> str:
    try:
        from app.rag.law_review import law_review_context

        return await law_review_context()
    except Exception:
        return ""


async def _enrich_with_review_agent(
    sections_map: dict[str, str],
    document: dict[str, Any],
    rag_text: str,
) -> tuple[list[dict[str, Any]], str]:
    try:
        from app.orchestrator.agents.review_agent import ReviewAgent
        from app.providers.factory import ProviderFactory

        factory = ProviderFactory()
        llm = factory.get_llm("structured")
        agent = ReviewAgent()
        result = await agent.review(
            llm=llm,
            sections=sections_map,
            project_metadata={
                "budget": document.get("budget"),
                "legal_context": rag_text,
            },
        )
    except Exception:
        return [], ""
    extras = [_suggestion_as_finding(item, rag_text) for item in result.suggestions]
    return extras, result.overall_assessment


async def _run_full_review(text: str, job_id: str) -> dict[str, Any]:
    result, document = _validate_document(text)
    rag_text = await _law_context()
    attach_legal_basis(result.findings, rag_text)
    findings = [finding_as_dict(f, aliases=True) for f in result.findings]
    sections_map = {
        key: value
        for key, value in document.items()
        if isinstance(key, str) and key.startswith("s") and isinstance(value, str)
    }
    extras, assessment = await _enrich_with_review_agent(sections_map, document, rag_text)
    seen = {(item.get("rule_violated"), item.get("message")) for item in findings}
    for item in extras:
        key = (item.get("rule_violated"), item.get("message"))
        if key in seen:
            continue
        findings.append(item)
        seen.add(key)
    return {
        "id": job_id,
        "quality_score": result.quality_score,
        "findings": findings,
        "status": "completed",
        "overall_assessment": assessment,
    }


@router.post("/extract")
async def extract_review_document(
    request: Request,
    file: UploadFile,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
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
    grid_id = store_review_original(
        getattr(request.app.state, "mongo", None),
        raw=raw,
        filename=file.filename or "tor.bin",
        mime=mime,
        owner_id=current_user.id,
    )
    job = ReviewJob(
        id=uuid.uuid4(),
        owner_id=current_user.id,
        filename=file.filename or "tor.bin",
        extracted_text=text,
        mongo_gridfs_id=grid_id,
        status="extracted",
        result_json={},
    )
    await save_review_job(db, job)
    return _envelope(
        request,
        {"id": str(job.id), "extracted_text": text[:20000], "status": "extracted"},
    )


@router.post("/run")
async def run_standalone_review(
    request: Request,
    body: dict,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    job_id = body.get("id") or body.get("review_id")
    text = body.get("text") or ""
    job: ReviewJob | None = None
    if job_id:
        try:
            parsed = uuid.UUID(str(job_id))
        except ValueError as exc:
            raise ValidationError(message="รหัสงานตรวจสอบไม่ถูกต้อง") from exc
        job = await fetch_review_job(db, parsed, current_user.id)
        if job:
            text = job.extracted_text or text
            job_id = str(job.id)
    if not text:
        raise ValidationError(message="ไม่มีข้อความให้ตรวจสอบ")
    payload = await _run_full_review(text, str(job_id or uuid.uuid4()))
    if job is not None:
        await save_review_result(db, job, payload)
    return _envelope(request, payload)


@router.get("/{review_id}")
async def get_standalone_review(
    request: Request,
    review_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    try:
        parsed = uuid.UUID(review_id)
    except ValueError as exc:
        raise NotFoundError(message="ไม่พบงานตรวจสอบ") from exc
    job = await fetch_review_job(db, parsed, current_user.id)
    if not job:
        raise NotFoundError(message="ไม่พบงานตรวจสอบ")
    return _envelope(request, _job_preview(job))


@router.post("/compare-projects")
async def compare_projects(
    request: Request,
    body: CompareRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    if len(body.project_ids) + len(body.extract_ids) < 2:
        raise ValidationError(message="ต้องระบุอย่างน้อย 2 รายการ")
    items = await _collect_compare_documents(
        db, current_user.id, body.project_ids, body.extract_ids
    )
    ids = [item[0] for item in items]
    names = [item[1] for item in items]
    texts = [item[2] for item in items]
    return _envelope(request, {"comparisons": _pairwise_jaccard(ids, names, texts)})
