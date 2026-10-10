"""Standalone TOR analysis tool (legal, lock-in, project, recommendations)."""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.review import (
    _get_project_with_access,
    _project_requirements_text,
)
from app.deps import get_current_user, get_db
from app.domain.extraction_map import infer_review_budget, map_extracted_text
from app.domain.tor_sections import TOR_SECTION_LABELS
from app.exceptions import ValidationError
from app.models.tor_section import TORSection
from app.models.user import User
from app.schemas.responses import MetaInfo, SuccessResponse
from app.services.bidder_risk import strip_page_markers
from app.services.tor_analysis import (
    PART_LABELS,
    PART_LEGAL,
    PART_LOCK_IN,
    PART_PROJECT,
    AnalyzerFinding,
    TorAnalysisResult,
    analysis_as_dict,
    analyze_tor,
)
from app.services.tor_assemble import assemble_review_document
from app.services.web_search import HARD_MAX_RESULTS, HARD_MIN_RESULTS, WebSource, search_web

logger = logging.getLogger("tor_app.analyze")

router = APIRouter()

ANALYZE_EMPTY_MESSAGE = "ไม่มีข้อความให้วิเคราะห์ — วางข้อความ TOR หรือเลือกโครงการ"
PREFER_LEGAL_CORPUS = (
    "แหล่งออนไลน์เป็นข้อมูลประกอบ หากถ้อยคำขัดกับคลังกฎหมาย ให้ยึดคลังกฎหมายก่อน"
)
NO_WARM_CONTRACT_NOTE = (
    "ข้อความที่แนะนำมาจากตัววิเคราะห์และคลังที่มีอยู่ "
    "ไม่แต่งถ้อยคำสัญญาจากพี่วอร์มที่ยังไม่มีในคลัง"
)

_PART_ORDER = (PART_LEGAL, PART_LOCK_IN, PART_PROJECT)
_WEB_SEARCH_TIMEOUT_SECONDS = 8
_RATE_RE = re.compile(r"ร้อยละ\s*(\d+(?:\.\d+)?)")
_YEAR_RE = re.compile(r"พ\.ศ\.\s*(\d{4})")
_PRB_MARK = "พ.ร.บ."
_LEGAL_TOPIC_MARKERS = (
    "ค่าปรับ",
    "ทุนจดทะเบียน",
    _PRB_MARK,
    "ระเบียบกระทรวงการคลัง",
    "มาตรา",
    "หรือเทียบเท่า",
)


class AnalyzeRequest(BaseModel):
    """Analyze pasted TOR text or a saved project draft."""

    text: str | None = Field(default=None, max_length=200_000)
    project_id: uuid.UUID | None = None


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


async def _law_context(project_type: str | None = None) -> str:
    try:
        from app.rag.law_review import law_review_context

        return await asyncio.wait_for(law_review_context(project_type), timeout=30)
    except Exception:
        return ""


def _document_from_text(text: str) -> dict[str, Any]:
    clean = strip_page_markers(text)
    mapped = map_extracted_text(clean)
    if not mapped:
        mapped = {"s1": clean or text}
    document: dict[str, Any] = {**mapped, "sections": mapped, "metadata": {}}
    budget = infer_review_budget(clean or text, mapped)
    if budget is not None:
        document["budget"] = budget
        document["metadata"]["budget"] = budget
    document["_source_text"] = text
    return document


def source_as_dict(source: WebSource, *, conflicts_with_legal_kb: bool = False) -> dict[str, Any]:
    return {
        "title": source.title,
        "url": source.url,
        "snippet": source.snippet,
        "published": source.published,
        "conflicts_with_legal_kb": conflicts_with_legal_kb,
    }


def source_conflicts_with_legal_kb(snippet: str, rag_text: str) -> bool:
    """True when a web snippet contradicts numbers or years in the legal corpus."""
    rag = (rag_text or "").strip()
    web = (snippet or "").strip()
    if not rag or not web:
        return False
    if not any(marker in rag and marker in web for marker in _LEGAL_TOPIC_MARKERS):
        return False
    rag_rates = set(_RATE_RE.findall(rag))
    web_rates = set(_RATE_RE.findall(web))
    if rag_rates and web_rates and rag_rates.isdisjoint(web_rates):
        return True
    if _PRB_MARK in rag and _PRB_MARK in web:
        rag_years = set(_YEAR_RE.findall(rag))
        web_years = set(_YEAR_RE.findall(web))
        if rag_years and web_years and rag_years.isdisjoint(web_years):
            return True
    return False


def _section_label(section_key: str) -> str:
    return TOR_SECTION_LABELS.get(section_key, section_key or "ทั่วไป")


def _findings_by_section(result: TorAnalysisResult) -> dict[str, list[tuple[str, AnalyzerFinding]]]:
    grouped: dict[str, list[tuple[str, AnalyzerFinding]]] = defaultdict(list)
    for part_key in _PART_ORDER:
        part = result.part(part_key)
        for finding in part.findings:
            if not (finding.suggested_text or "").strip() and not (finding.reason or "").strip():
                continue
            key = (finding.section_key or "").strip() or part_key
            grouped[key].append((part_key, finding))
    return dict(grouped)


def _search_query(section_key: str, findings: list[AnalyzerFinding]) -> str:
    label = _section_label(section_key)
    reasons = " ".join((item.reason or "").strip() for item in findings if item.reason)
    return (
        f"TOR จัดซื้อจัดจ้างภาครัฐ {label} {reasons} "
        f"{_PRB_MARK} การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560 "
        "ระเบียบกระทรวงการคลัง พ.ศ. 2560"
    ).strip()[:400]


def _source_count_note(count: int) -> str:
    if count <= 0:
        return "ค้นออนไลน์ไม่ได้หรือไม่พบแหล่งสำหรับหมวดนี้ (0 แหล่ง)"
    if count < HARD_MIN_RESULTS:
        return f"พบ {count} แหล่งออนไลน์ประกอบหมวดนี้ (น้อยกว่า {HARD_MIN_RESULTS} ที่ตั้งเป้า)"
    return f"พบ {count} แหล่งออนไลน์ประกอบหมวดนี้"


def _annotate_sources(sources: list[WebSource], rag_text: str) -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for source in sources[:HARD_MAX_RESULTS]:
        conflict = source_conflicts_with_legal_kb(
            f"{source.title} {source.snippet}", rag_text
        )
        payload.append(source_as_dict(source, conflicts_with_legal_kb=conflict))
    return payload


def _suggestion_payload(
    part_key: str,
    finding: AnalyzerFinding,
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "part": part_key,
        "part_label": PART_LABELS.get(part_key, part_key),
        "section_key": finding.section_key,
        "source_quote": finding.source_quote,
        "reason": finding.reason,
        "suggested_text": (finding.suggested_text or "").strip(),
        "legal_basis": finding.legal_basis,
        "sources": sources,
        "source_count": len(sources),
    }


async def collect_section_recommendations(
    result: TorAnalysisResult,
    *,
    rag_text: str = "",
) -> list[dict[str, Any]]:
    """Search 5–10 web sources per TOR section that has findings or suggestions."""
    grouped = _findings_by_section(result)
    if not grouped:
        return []

    async def _search_one(section_key: str, rows: list[tuple[str, AnalyzerFinding]]) -> dict[str, Any]:
        findings = [finding for _part, finding in rows]
        query = _search_query(section_key, findings)
        try:
            raw = await search_web(query)
        except Exception:
            logger.warning("analyze web search failed section=%s", section_key)
            raw = []
        sources = _annotate_sources(list(raw or []), rag_text)
        any_conflict = any(item.get("conflicts_with_legal_kb") for item in sources)
        count = len(sources)
        return {
            "section_key": section_key,
            "section_label": _section_label(section_key),
            "suggestions": [
                _suggestion_payload(part_key, finding, sources) for part_key, finding in rows
            ],
            "sources": sources,
            "source_count": count,
            "source_count_note": _source_count_note(count),
            "prefer_legal_corpus": any_conflict,
            "legal_corpus_note": PREFER_LEGAL_CORPUS if sources else "",
        }

    return list(
        await asyncio.gather(
            *(_search_one(section_key, rows) for section_key, rows in grouped.items())
        )
    )


def analysis_payload(result: TorAnalysisResult, recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    payload = analysis_as_dict(result)
    payload["recommendations"] = recommendations
    payload["prefer_legal_corpus_note"] = (
        PREFER_LEGAL_CORPUS
        if any(item.get("prefer_legal_corpus") for item in recommendations)
        else ""
    )
    payload["suggested_text_note"] = NO_WARM_CONTRACT_NOTE
    return payload


@router.post("")
@router.post("/")
async def analyze_tor_document(
    request: Request,
    body: AnalyzeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> JSONResponse:
    text = (body.text or "").strip()
    project = None
    user_documents = ""
    project_type: str | None = None
    document: dict[str, Any] | None = None

    if body.project_id is not None:
        project = await _get_project_with_access(body.project_id, current_user, db)
        sections = (
            await db.execute(select(TORSection).where(TORSection.project_id == project.id))
        ).scalars().all()
        document, _parents = assemble_review_document(list(sections))
        document["budget"] = project.budget
        document["project_type"] = project.project_type
        project_type = project.project_type
        user_documents = _project_requirements_text(project)

    if text:
        document = _document_from_text(text)
        if project is not None:
            document.setdefault("budget", project.budget)
            document.setdefault("project_type", project.project_type)

    if not document or not any(
        isinstance(value, str) and value.strip()
        for key, value in document.items()
        if isinstance(key, str) and key.startswith("s")
    ):
        raise ValidationError(message=ANALYZE_EMPTY_MESSAGE)

    rag_text = await _law_context(project_type)
    result = analyze_tor(document, user_documents=user_documents, rag_text=rag_text)
    try:
        recommendations = await asyncio.wait_for(
            collect_section_recommendations(result, rag_text=rag_text),
            timeout=_WEB_SEARCH_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.warning("analyze web search timed out; returning scores without sources")
        recommendations = []
    except Exception:
        logger.warning("analyze web search failed; returning scores without sources")
        recommendations = []
    return _envelope(request, analysis_payload(result, recommendations))
