"""Intake analysis, coverage, gap questions, and ready-to-compose checks."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.slots import FACT_REQUIRED_SLOTS, INTAKE_SLOT_LABELS, INTAKE_SLOT_ORDER
from app.domain.tor_sections import SCOPE_SUBSECTIONS, TOR_SECTION_ORDER
from app.models.project import Project
from app.models.tor_section import TORSection
from app.providers.factory import ProviderFactory
from app.rag.graph_extract import parse_json_lenient
from app.rag.hybrid import hybrid_retrieve

logger = logging.getLogger(__name__)

ANALYZE_PROMPT = """คุณเป็นผู้ช่วยจัดทำ TOR ภาครัฐไทย
จัดข้อความจากเอกสารโครงการเข้าช่องตามรหัสที่กำหนด แล้วตอบเป็น JSON เท่านั้น:

{
  "slot_map": {
    "s1": {"content": "...", "status": "filled", "sources": ["ชื่อไฟล์"]},
    "s4.1": {"content": "...", "status": "gap", "sources": []}
  },
  "gap_questions": ["คำถามที่ยังขาดข้อมูลข้อเท็จจริง"]
}

status ได้เฉพาะ filled | gap | reference_only
รหัสช่อง: s1-s13 และ s4.1-s4.14
ถ้าไม่พบข้อมูลของช่อง ให้ status=gap และ content ว่าง
อย่าสวมข้อความกฎหมายเป็นข้อเท็จจริงของโครงการ — กฎหมายใส่ reference_only
"""


def empty_slot_map() -> dict[str, dict[str, Any]]:
    return {
        key: {"content": "", "status": "gap", "sources": []}
        for key in INTAKE_SLOT_ORDER
    }


def coverage_table(slot_map: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key in INTAKE_SLOT_ORDER:
        slot = slot_map.get(key) or {}
        status = slot.get("status") or "gap"
        rows.append(
            {
                "key": key,
                "label": INTAKE_SLOT_LABELS.get(key, key),
                "status": status,
                "filled": status == "filled",
                "fact_required": key in FACT_REQUIRED_SLOTS,
            }
        )
    return rows


def ready_criteria_met(slot_map: dict[str, Any]) -> bool:
    for key in FACT_REQUIRED_SLOTS:
        slot = slot_map.get(key) or {}
        status = slot.get("status")
        content = str(slot.get("content") or "").strip()
        if status != "filled" or not content:
            return False
    return True


def _analysis_dict(project: Project) -> dict[str, Any]:
    raw = project.analysis_json
    return raw if isinstance(raw, dict) else {}


def _extracted_dict(project: Project) -> dict[str, Any]:
    raw = project.extracted_fields
    return raw if isinstance(raw, dict) else {}


def slot_map_of(project: Project) -> dict[str, Any]:
    raw = _analysis_dict(project).get("slot_map") or {}
    return raw if isinstance(raw, dict) else {}


def has_intake_material(project: Project) -> bool:
    """True when the officer uploaded files, pasted text, or filled a slot."""
    texts = _extracted_dict(project).get("intake_texts") or []
    if isinstance(texts, list):
        for item in texts:
            if isinstance(item, dict) and str(item.get("text") or "").strip():
                return True
    files = _analysis_dict(project).get("intake_files") or []
    if isinstance(files, list) and files:
        return True
    for slot in slot_map_of(project).values():
        if not isinstance(slot, dict):
            continue
        if slot.get("status") == "filled" and str(slot.get("content") or "").strip():
            return True
    return False


def is_ready_to_compose(project: Project) -> bool:
    if not _analysis_dict(project).get("ready_to_compose"):
        return False
    return ready_criteria_met(slot_map_of(project))


def intake_unlocked_phase(project: Project) -> int:
    """Highest intake phase allowed: 0 empty, 1 has material, 2 confirmed ready."""
    if is_ready_to_compose(project):
        return 2
    if has_intake_material(project):
        return 1
    return 0


def can_set_phase(project: Project, target: int) -> bool:
    if target < 0 or target > 4:
        return False
    current = int(project.current_phase or 0)
    if target <= current:
        return True
    unlocked = intake_unlocked_phase(project)
    if target <= unlocked:
        return True
    return bool(unlocked >= 2 and target == current + 1)


def clamp_draft_phase(project: Project) -> bool:
    """Pull a draft back from Phase 2+ when intake is still empty. Returns True if changed."""
    if str(project.status or "") != "draft":
        return False
    current = int(project.current_phase or 0)
    unlocked = intake_unlocked_phase(project)
    if current <= unlocked:
        return False
    if current >= 2 and unlocked < 2:
        project.current_phase = unlocked
        return True
    if current == 1 and unlocked < 1:
        project.current_phase = 0
        return True
    return False


def append_intake_text(project: Project, name: str, text: str, file_status: str = "ok") -> None:
    analysis = dict(_analysis_dict(project))
    intake_files = list(analysis.get("intake_files") or [])
    intake_files.append({"name": name, "chars": len(text), "status": file_status})
    analysis["intake_files"] = intake_files
    project.analysis_json = analysis
    fields = dict(_extracted_dict(project))
    pack = list(fields.get("intake_texts") or [])
    pack.append({"name": name, "text": text[:20000]})
    fields["intake_texts"] = pack
    project.extracted_fields = fields


def merge_analysis(existing: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing or {})
    merged.update(patch)
    return merged


async def analyze_pack(project: Project, pack_text: str, filenames: list[str]) -> dict[str, Any]:
    llm = ProviderFactory().get_llm()
    user = (
        f"ไฟล์: {', '.join(filenames)}\n\n"
        f"เนื้อหาที่สกัด (ตัดความยาว):\n{pack_text[:24000]}"
    )
    response = await llm.invoke(
        [
            {"role": "system", "content": ANALYZE_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=4096,
    )
    slot_map = empty_slot_map()
    gap_questions: list[str] = []
    try:
        payload = parse_json_lenient(response.content)
        incoming = payload.get("slot_map") if isinstance(payload.get("slot_map"), dict) else {}
        for key, value in incoming.items():
            if key not in slot_map or not isinstance(value, dict):
                continue
            slot_map[key] = {
                "content": str(value.get("content") or ""),
                "status": value.get("status") if value.get("status") in {"filled", "gap", "reference_only"} else "gap",
                "sources": value.get("sources") if isinstance(value.get("sources"), list) else [],
            }
        raw_q = payload.get("gap_questions")
        if isinstance(raw_q, list):
            gap_questions = [str(item) for item in raw_q if str(item).strip()]
    except ValueError:
        logger.warning("intake analyze JSON parse failed for project %s", project.id)
        gap_questions = ["จัดช่องไม่สำเร็จ กรุณาตอบในแชทว่าโครงการนี้คืออะไร และวงเงินเท่าใด"]
    if not gap_questions:
        for key in FACT_REQUIRED_SLOTS:
            if (slot_map.get(key) or {}).get("status") != "filled":
                gap_questions.append(f"ขอข้อมูลสำหรับ {INTAKE_SLOT_LABELS.get(key, key)} ({key})")
    return {
        "slot_map": slot_map,
        "gap_questions": gap_questions,
        "ready_to_compose": False,
    }


async def fill_reference_slot(
    slot_key: str,
    user_id: UUID,
) -> dict[str, Any]:
    query = INTAKE_SLOT_LABELS.get(slot_key, slot_key)
    result, citations, degraded = await hybrid_retrieve(
        query,
        user_id=user_id,
        search_scope="global",
        section_relevance=slot_key if slot_key.startswith("s") else None,
        top_k=5,
    )
    texts = [chunk.text for chunk in result.chunks[:4]]
    sources = [c.get("label") for c in citations if c.get("label")]
    content = "\n\n".join(texts)[:4000]
    return {
        "content": content,
        "status": "reference_only",
        "sources": sources,
        "citations": citations,
        "graph_degraded": degraded,
    }


async def load_project(db: AsyncSession, project_id: UUID) -> Project | None:
    return (
        await db.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()


async def _upsert_section_text(
    db: AsyncSession,
    project_id: UUID,
    section_key: str,
    sub_key: str | None,
    text: str,
) -> None:
    stripped = text.strip()
    if not stripped:
        return
    stmt = select(TORSection).where(
        TORSection.project_id == project_id,
        TORSection.section_key == section_key,
    )
    if sub_key:
        stmt = stmt.where(TORSection.sub_key == sub_key)
    else:
        stmt = stmt.where(TORSection.sub_key.is_(None))
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row:
        if not (row.content or "").strip():
            row.content = stripped
        return
    db.add(
        TORSection(
            project_id=project_id,
            section_key=section_key,
            sub_key=sub_key,
            content=stripped,
            version=1,
        )
    )


async def apply_slot_map_to_sections(
    db: AsyncSession,
    project_id: UUID,
    slot_map: dict[str, Any],
) -> None:
    """Copy filled intake slots into TOR sections so Phase 2/3/review have real text."""
    for key in TOR_SECTION_ORDER:
        if key == "s4":
            continue
        slot = slot_map.get(key) or {}
        if isinstance(slot, dict):
            await _upsert_section_text(db, project_id, key, None, str(slot.get("content") or ""))
    parts: list[str] = []
    for sub_key, title in SCOPE_SUBSECTIONS.items():
        slot = slot_map.get(sub_key) or {}
        text = str(slot.get("content") or "") if isinstance(slot, dict) else ""
        if not text.strip():
            continue
        await _upsert_section_text(db, project_id, "s4", sub_key, text)
        parts.append(f"{title}: {text.strip()}")
    if parts:
        await _upsert_section_text(db, project_id, "s4", None, "\n\n".join(parts))
