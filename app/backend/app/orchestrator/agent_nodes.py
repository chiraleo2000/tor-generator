"""LangGraph node implementations for the agent TOR workflow."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.config import get_settings
from app.domain.tor_sections import MANDATORY_HUMAN_REVIEW_SECTIONS, TOR_SECTION_ORDER
from app.orchestrator.agent_state import AgentWorkflowState
from app.services.agent_intake_service import IntakeIngestionService
from app.services.coverage import build_coverage_map, compute_readiness_score, compute_ready
from app.services.full_draft_generator import FullDraftGenerator, mean_quality
from app.services.gap_detector import GapDetector
from app.services.section_mapper import SectionMapper
from app.services.session_cache import SessionCacheService

logger = logging.getLogger("tor_app.agent_nodes")

MAX_GAP_ITERATIONS = 20
MAX_CORRECTIONS = 3


def _warnings(state: AgentWorkflowState) -> list[str]:
    current = state.get("warnings") or []
    return list(current)


def _with_coverage(slot_map: dict) -> dict[str, Any]:
    return {
        "slot_map": slot_map,
        "coverage_map": build_coverage_map(slot_map),
        "readiness_score": compute_readiness_score(slot_map),
        "ready": compute_ready(slot_map),
    }


async def ingest_node(state: AgentWorkflowState) -> dict[str, Any]:
    warnings = _warnings(state)
    files = state.get("pending_files") or []
    free_text = state.get("free_text") or ""
    text = str(free_text).strip()
    if not files and not state.get("intake_texts") and len(text) < 50:
        return {
            "phase": "error",
            "error": "ต้องอัปโหลดเอกสารหรือวางข้อความอย่างน้อย 50 ตัวอักษร",
            "warnings": warnings,
            "pending_files": [],
        }
    if state.get("intake_texts") and not files:
        texts = list(state.get("intake_texts") or [])
        total = sum(len(str(item.get("text") or "")) for item in texts if isinstance(item, dict))
        return {
            "phase": "mapping",
            "intake_texts": texts,
            "total_chars": total,
            "pending_files": [],
            "error": None,
        }
    service = IntakeIngestionService()
    try:
        result = await service.process_batch(
            project_id=UUID(str(state["project_id"])),
            files=files,
            free_text=free_text or None,
            storage_backend=state.get("storage_backend") or "minio",
        )
    except Exception as exc:
        logger.warning("Ingest failed: %s", exc)
        return {
            "phase": "error",
            "error": str(exc),
            "warnings": warnings,
            "pending_files": [],
        }
    file_rows = [
        {
            "name": item.name,
            "size": item.size,
            "content_hash": item.content_hash,
            "status": item.status,
            "chars": item.chars,
            "error": item.error,
        }
        for item in result.files
    ]
    if result.timed_out:
        warnings.append("การสกัดเอกสารหมดเวลา คืนผลบางส่วน")
    return {
        "phase": "mapping",
        "intake_files": file_rows,
        "intake_texts": result.texts,
        "total_chars": result.total_chars,
        "pending_files": [],
        "warnings": warnings,
        "error": None,
    }


async def map_sections_node(state: AgentWorkflowState) -> dict[str, Any]:
    warnings = _warnings(state)
    parts = [
        str(item.get("text") or "")
        for item in (state.get("intake_texts") or [])
        if isinstance(item, dict)
    ]
    content = "\n\n".join(parts)
    mapper = SectionMapper()
    mapping = await mapper.map_content(content, state.get("project_metadata") or {})
    if mapping.error:
        warnings.append(f"การจัดช่องไม่สมบูรณ์: {mapping.error}")
    patch = _with_coverage(mapping.slot_map)
    cache = SessionCacheService()
    await cache.set_slot_map(state["project_id"], mapping.slot_map)
    patch.update({"phase": "gap_filling", "error": None, "warnings": warnings})
    return patch


async def detect_gaps_node(state: AgentWorkflowState) -> dict[str, Any]:
    slot_map = state.get("slot_map") or {}
    detector = GapDetector()
    gaps = detector.detect_gaps(slot_map)
    iteration = int(state.get("gap_iteration") or 0)
    max_iter = int(state.get("max_gap_iterations") or MAX_GAP_ITERATIONS)
    patch = _with_coverage(slot_map)
    if iteration >= max_iter:
        patch.update(
            {
                "phase": "confirming",
                "gap_questions": [],
                "warnings": _warnings(state)
                + ["ถึงจำนวนรอบถามสูงสุดแล้ว สามารถยืนยันข้อมูลที่มีเพื่อร่าง TOR ได้"],
            }
        )
        return patch
    if not gaps or compute_ready(slot_map):
        patch.update({"phase": "confirming", "gap_questions": []})
        return patch
    questions = await detector.generate_questions(gaps, state.get("project_metadata") or {})
    patch.update({"phase": "gap_filling", "gap_questions": questions})
    return patch


async def fill_slot_node(state: AgentWorkflowState) -> dict[str, Any]:
    answer = str(state.get("last_answer") or "").strip()
    slot_map = dict(state.get("slot_map") or {})
    if not answer:
        return {"phase": "gap_filling", "error": "ไม่มีคำตอบ"}
    mapper = SectionMapper()
    result = await mapper.incremental_update(
        answer, slot_map, list(state.get("gap_questions") or [])
    )
    patch = _with_coverage(result.slot_map)
    cache = SessionCacheService()
    await cache.set_slot_map(state["project_id"], result.slot_map)
    messages = list(state.get("messages") or [])
    messages.append({"role": "user", "content": answer})
    if result.affected:
        summary = "อัปเดตช่อง: " + ", ".join(result.affected)
        messages.append({"role": "assistant", "content": summary})
    patch.update(
        {
            "phase": "gap_filling",
            "gap_iteration": int(state.get("gap_iteration") or 0) + 1,
            "last_answer": "",
            "messages": messages,
            "error": result.error,
        }
    )
    return patch


def confirm_node(state: AgentWorkflowState) -> dict[str, Any]:
    if not state.get("user_confirmed"):
        return {"phase": "confirming"}
    return {"phase": "drafting", "error": None}


async def draft_all_node(state: AgentWorkflowState) -> dict[str, Any]:
    generator = FullDraftGenerator()
    result = await generator.generate_all(
        state.get("slot_map") or {},
        state.get("project_metadata") or {},
        deployment_mode=state.get("deployment_mode") or get_settings().deployment_mode,
        project_id=state.get("project_id"),
        user_id=state.get("user_id"),
    )
    warnings = _warnings(state) + result.warnings
    return {
        "phase": "validating",
        "section_drafts": result.section_drafts,
        "sections_pending": result.sections_pending,
        "draft_quality_scores": result.draft_quality_scores,
        "overall_quality_score": result.overall_quality_score,
        "warnings": warnings,
        "error": None,
    }


async def validate_draft_node(state: AgentWorkflowState) -> dict[str, Any]:
    generator = FullDraftGenerator()
    drafts = dict(state.get("section_drafts") or {})
    attempts = dict(state.get("correction_attempts") or {})
    validation = generator.validate_document(drafts, state.get("project_metadata"))
    from app.rule_engine.engine import finding_as_dict

    findings = [finding_as_dict(finding) for finding in validation.findings]
    errors = [item for item in findings if item["severity"] == "error"]
    need_retry = False
    for item in errors:
        section = item.get("affected_section") or ""
        if section not in TOR_SECTION_ORDER:
            continue
        used = int(attempts.get(section) or 0)
        if used >= MAX_CORRECTIONS:
            continue
        need_retry = True
        attempts[section] = used + 1
        drafts[section] = await generator.auto_correct(
            section,
            drafts.get(section) or "",
            [item],
            state.get("slot_map") or {},
            used,
            state.get("project_metadata"),
            state.get("user_id"),
        )
    scores = dict(state.get("draft_quality_scores") or {})
    overall = float(validation.quality_score)
    if scores:
        overall = mean_quality(scores)
    phase = "drafting" if need_retry else "human_review"
    return {
        "phase": phase,
        "section_drafts": drafts,
        "validation_findings": findings,
        "correction_attempts": attempts,
        "overall_quality_score": overall,
        "mandatory_review_sections": sorted(MANDATORY_HUMAN_REVIEW_SECTIONS),
        "error": None,
    }


def human_review_node(state: AgentWorkflowState) -> dict[str, Any]:
    if state.get("human_approved"):
        acknowledged = list(state.get("sections_acknowledged") or [])
        for key in sorted(MANDATORY_HUMAN_REVIEW_SECTIONS):
            if key not in acknowledged:
                acknowledged.append(key)
        return {
            "phase": "exporting",
            "sections_acknowledged": acknowledged,
            "error": None,
        }
    feedback = str(state.get("human_feedback") or "").strip()
    if feedback:
        return {"phase": "drafting", "human_feedback": feedback}
    return {
        "phase": "human_review",
        "mandatory_review_sections": sorted(MANDATORY_HUMAN_REVIEW_SECTIONS),
    }


async def export_node(state: AgentWorkflowState) -> dict[str, Any]:
    required = set(MANDATORY_HUMAN_REVIEW_SECTIONS)
    acknowledged = set(state.get("sections_acknowledged") or [])
    if not required.issubset(acknowledged):
        return {
            "phase": "human_review",
            "error": "ต้องยืนยันหมวดที่ต้องตรวจก่อนส่งออก",
        }
    from app.services.agent_export import persist_and_export

    try:
        urls = await persist_and_export(state)
    except Exception as exc:
        logger.warning("Export failed: %s", exc)
        return {"phase": "error", "error": str(exc), "warnings": _warnings(state)}
    return {
        "phase": "complete",
        "export_docx_url": urls.get("docx"),
        "export_pdf_url": urls.get("pdf"),
        "error": None,
    }


def handle_error_node(state: AgentWorkflowState) -> dict[str, Any]:
    return {"phase": "error", "error": state.get("error") or "เกิดข้อผิดพลาด"}
