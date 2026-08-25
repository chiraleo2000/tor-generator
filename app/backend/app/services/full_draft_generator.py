"""Generate all 13 TOR sections with RAG, specialized agents, and auto-correct."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from app.config import get_settings
from app.domain.slots import FACT_REQUIRED_SLOTS, INTAKE_SLOT_LABELS
from app.domain.tor_sections import TOR_SECTION_ORDER
from app.orchestrator.agents.registry import get_agent_for_section
from app.orchestrator.graph import _create_rule_engine
from app.orchestrator.state import RAGChunk
from app.providers.factory import ProviderFactory
from app.rag.hybrid import hybrid_retrieve
from app.services.session_cache import SessionCacheService

logger = logging.getLogger("tor_app.full_draft")

TOTAL_TIMEOUT = 900
MAX_CORRECTIONS_PER_SECTION = 3
RAG_THRESHOLD = 0.5
RAG_TOP_K = 5


@dataclass
class DraftResult:
    section_drafts: dict[str, str] = field(default_factory=dict)
    draft_quality_scores: dict[str, float] = field(default_factory=dict)
    overall_quality_score: float = 0.0
    validation_findings: list[dict[str, Any]] = field(default_factory=list)
    sections_pending: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    correction_attempts: dict[str, int] = field(default_factory=dict)


def mean_quality(scores: dict[str, float]) -> float:
    if not scores:
        return 0.0
    values = [max(0.0, min(100.0, float(value))) for value in scores.values()]
    return sum(values) / len(values)


def slot_user_input(slot_map: dict[str, Any], section_key: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    slot = slot_map.get(section_key) if isinstance(slot_map, dict) else None
    if isinstance(slot, dict):
        payload["content"] = str(slot.get("content") or "")
        payload["sources"] = slot.get("sources") or []
    if section_key == "s4":
        subs = {
            key: str((slot_map.get(key) or {}).get("content") or "")
            for key in slot_map
            if str(key).startswith("s4.")
        }
        payload["scope_subsections"] = subs
    return payload


class FullDraftGenerator:
    """Draft s1–s13 using section agents and hybrid RAG."""

    def __init__(
        self,
        llm: Any | None = None,
        cache: SessionCacheService | None = None,
        retrieve=hybrid_retrieve,
    ) -> None:
        self._llm = llm
        self._cache = cache or SessionCacheService()
        self._retrieve = retrieve
        self._deployment_mode: str | None = None

    def _llm_client(self) -> Any:
        if self._llm is not None:
            return self._llm
        settings = get_settings()
        mode = self._deployment_mode
        if mode:
            settings = settings.model_copy(update={"deployment_mode": mode})
        return ProviderFactory(settings).get_llm("draft")

    async def generate_all(
        self,
        slot_map: dict[str, Any],
        project_metadata: dict | None = None,
        deployment_mode: str = "on_prem",
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> DraftResult:
        self._deployment_mode = deployment_mode
        result = DraftResult()
        for key in FACT_REQUIRED_SLOTS:
            slot = (slot_map or {}).get(key) or {}
            if slot.get("status") == "filled" and str(slot.get("content") or "").strip():
                continue
            label = INTAKE_SLOT_LABELS.get(key, key)
            result.warnings.append(f"ยังขาดข้อเท็จจริงใน {label} ({key})")
        deadline = time.monotonic() + TOTAL_TIMEOUT
        meta = project_metadata or {}
        for section_key in TOR_SECTION_ORDER:
            if time.monotonic() >= deadline:
                result.sections_pending.extend(
                    key for key in TOR_SECTION_ORDER if key not in result.section_drafts
                )
                result.warnings.append("หมดเวลาสร้างร่าง TOR ทั้งฉบับ คืนเฉพาะส่วนที่เสร็จแล้ว")
                break
            cached = None
            if project_id:
                cached = await self._cache.get_draft(project_id, section_key)
            if isinstance(cached, str) and cached.strip():
                result.section_drafts[section_key] = cached
                result.draft_quality_scores[section_key] = 70.0
                continue
            draft, warnings, score = await self._draft_section(
                section_key, slot_map, meta, user_id
            )
            result.warnings.extend(warnings)
            if not draft:
                result.sections_pending.append(section_key)
                continue
            result.section_drafts[section_key] = draft
            result.draft_quality_scores[section_key] = score
            if project_id:
                await self._cache.set_draft(project_id, section_key, draft)
        result.overall_quality_score = mean_quality(result.draft_quality_scores)
        return result

    async def _draft_section(
        self,
        section_key: str,
        slot_map: dict[str, Any],
        meta: dict[str, Any],
        user_id: str | None,
        findings: list | None = None,
        extra_feedback: str | None = None,
    ) -> tuple[str, list[str], float]:
        warnings: list[str] = []
        chunks, retrieve_warning = await self._rag(section_key, user_id)
        if retrieve_warning:
            warnings.append(retrieve_warning)
        user_input = slot_user_input(slot_map, section_key)
        user_input.update({k: v for k, v in meta.items() if v is not None})
        agent = get_agent_for_section(section_key)
        llm = self._llm_client()
        try:
            if agent is None:
                return "", warnings + [f"ไม่มี agent สำหรับ {section_key}"], 0.0
            text = await agent.draft(
                llm,
                user_input,
                rag_chunks=chunks,
                template=None,
                validation_findings=findings or [],
                human_feedback=extra_feedback,
                temperature=0.3,
                max_tokens=4096,
            )
        except Exception as exc:
            logger.warning("Draft failed for %s: %s", section_key, exc)
            return "", warnings + [f"ร่าง {section_key} ไม่สำเร็จ: {exc}"], 0.0
        score = 80.0 if chunks else 65.0
        if not (text or "").strip():
            return "", warnings, 0.0
        if len(text) < 40:
            score = min(score, 50.0)
        return text, warnings, score

    async def _rag(
        self, section_key: str, user_id: str | None
    ) -> tuple[list[RAGChunk], str | None]:
        try:
            result, _citations, degraded = await self._retrieve(
                INTAKE_SLOT_LABELS.get(section_key, section_key),
                user_id=user_id,
                search_scope="both",
                top_k=RAG_TOP_K,
                section_relevance=section_key,
            )
        except Exception as exc:
            logger.warning("RAG failed for %s: %s", section_key, exc)
            return [], "ไม่สามารถดึงเอกสารกฎหมายได้ จึงร่างจากข้อมูลที่ผู้ใช้ให้เท่านั้น"
        chunks: list[RAGChunk] = []
        for chunk in getattr(result, "chunks", []) or []:
            score = float(getattr(chunk, "score", 0) or 0)
            if score < RAG_THRESHOLD:
                continue
            chunks.append(
                {
                    "id": str(getattr(chunk, "id", "")),
                    "text": getattr(chunk, "text", "") or "",
                    "score": score,
                    "source_document": getattr(chunk, "source_document", None),
                    "section_label": getattr(chunk, "section_label", None),
                    "page_number": getattr(chunk, "page_number", None),
                }
            )
            if len(chunks) >= RAG_TOP_K:
                break
        if not chunks:
            return [], "ไม่พบเอกสารกฎหมายที่เกี่ยวข้องเพียงพอสำหรับหมวดนี้"
        warning = "GraphRAG ลดระดับเหลือ pgvector" if degraded else None
        return chunks, warning

    async def auto_correct(
        self,
        section_key: str,
        draft: str,
        findings: list[dict],
        slot_map: dict[str, Any],
        attempt: int,
        project_metadata: dict | None = None,
        user_id: str | None = None,
    ) -> str:
        if attempt >= MAX_CORRECTIONS_PER_SECTION:
            return draft
        feedback = "\n".join(
            str(item.get("message") or item.get("recommended_correction") or "")
            for item in findings
            if (item.get("affected_section") or "") in {section_key, ""}
        )
        text, _warnings, _score = await self._draft_section(
            section_key,
            slot_map,
            project_metadata or {},
            user_id,
            findings=findings,
            extra_feedback=feedback or draft,
        )
        return text or draft

    def validate_document(
        self,
        section_drafts: dict[str, str],
        project_metadata: dict | None = None,
    ):
        engine = _create_rule_engine()
        document = dict(section_drafts)
        meta = project_metadata or {}
        if "budget" in meta:
            document["budget"] = meta["budget"]
        if "project_type" in meta:
            document["project_type"] = meta["project_type"]
        return engine.validate(document)
