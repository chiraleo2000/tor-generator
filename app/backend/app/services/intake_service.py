"""Intake analysis, coverage, gap questions, and ready-to-compose checks."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.slots import FACT_REQUIRED_SLOTS, INTAKE_SLOT_LABELS, INTAKE_SLOT_ORDER
from app.domain.tor_sections import SCOPE_SUBSECTIONS, TOR_SECTION_LABELS, TOR_SECTION_ORDER
from app.models.project import Project
from app.models.tor_section import TORSection
from app.providers.factory import ProviderFactory
from app.providers.structured_invoke import invoke_with_schema
from app.schemas.llm_structured import IntakeAnalyzeResult, json_schema_for
from app.rag.hybrid import hybrid_retrieve
from app.services.intake_heuristic import (
    extract_slot_contents,
    facts_are_complete,
    overlay_filled_slots,
)

logger = logging.getLogger(__name__)

ANALYZE_LLM_TIMEOUT_SEC = 55
ANALYZE_MAX_TOKENS = 2048
FILL_REFERENCES_TOTAL_SEC = 40.0
FILL_ONE_REFERENCE_SEC = 8.0

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


CHAT_USER_SOURCE = "ผู้ใช้ตอบในแชท"

INTAKE_CHAT_SYSTEM = (
    "คุณเป็นเจ้าหน้าที่พี่เลี้ยงร่าง TOR ภาครัฐ คุยภาษาไทยสุภาพ กระชับ เหมือนคุยกับคน "
    "มีผลวิเคราะห์ Phase 1 แล้ว ห้ามถามซ้ำช่องที่ได้แล้ว "
    "ถามทีละช่องตามที่ระบบระบุว่ากำลังถาม อย่าถามหลายเรื่องในครั้งเดียว "
    "เมื่อผู้ใช้ตอบ ให้ทวนสั้น ๆ ว่าบันทึกช่องนั้นแล้ว แล้วถามช่องถัดไปที่ระบบระบุ "
    "ถ้าข้อเท็จจริงครบแล้ว บอกว่าพร้อมไปร่าง TOR ได้ "
    "กฎหมายจากคลังเป็นอ้างอิง ห้ามสวมเป็นวงเงินหรือชื่อโครงการ "
    "ห้ามตอบเป็นตารางช่องทั้งหมด"
)


def coverage_table(slot_map: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key in INTAKE_SLOT_ORDER:
        slot = slot_map.get(key) or {}
        status = slot.get("status") or "gap"
        content = str(slot.get("content") or "").strip()
        rows.append(
            {
                "key": key,
                "label": INTAKE_SLOT_LABELS.get(key, key),
                "status": status,
                "filled": status == "filled",
                "fact_required": key in FACT_REQUIRED_SLOTS,
                "preview": content[:180],
            }
        )
    return rows


def _slot_is_filled(slot_map: dict[str, Any], key: str) -> bool:
    slot = slot_map.get(key) or {}
    if not isinstance(slot, dict):
        return False
    content = str(slot.get("content") or "").strip()
    return slot.get("status") == "filled" and bool(content)


def _write_chat_slot(slot_map: dict[str, Any], key: str, answer: str) -> None:
    slot = slot_map.get(key)
    if not isinstance(slot, dict):
        slot = {"content": "", "status": "gap", "sources": []}
        slot_map[key] = slot
    slot["content"] = answer
    slot["status"] = "filled"
    sources = slot.get("sources")
    if isinstance(sources, list):
        if CHAT_USER_SOURCE not in sources:
            sources.append(CHAT_USER_SOURCE)
    else:
        slot["sources"] = [CHAT_USER_SOURCE]


def missing_fact_keys(slot_map: dict[str, Any]) -> list[str]:
    return [
        key for key in INTAKE_SLOT_ORDER
        if key in FACT_REQUIRED_SLOTS and not _slot_is_filled(slot_map, key)
    ]


# ---------------------------------------------------------------------------
# Sequential Q&A helpers (Phase 2 smart slot routing)
# ---------------------------------------------------------------------------

SLOT_QUESTIONS: dict[str, str] = {
    "s1": "กรุณาบอกชื่อโครงการและความเป็นมา เช่น เหตุผลที่ต้องจัดซื้อ/จัดจ้าง",
    "s2": "วัตถุประสงค์หลักของโครงการนี้คืออะไร? (เพื่ออะไร ผลที่คาดว่าจะได้รับ)",
    "s5": "ระยะเวลาดำเนินการกี่วัน/เดือน? นับจากเมื่อไร?",
    "s6": "วงเงินงบประมาณเท่าไร? (จำนวนเงิน + แหล่งงบ)",
    "s7": "สถานที่ดำเนินการหรือส่งมอบอยู่ที่ไหน?",
    "s4.1": "ขอบเขตงานหลัก — ต้องทำอะไรบ้าง? (สรุปภาพรวม)",
}


def next_asking_slot(slot_map: dict[str, Any], current: str | None = None) -> str | None:
    """First empty fact slot. `current` is ignored after fill (it is no longer missing)."""
    missing = missing_fact_keys(slot_map)
    if not missing:
        return None
    if current and current in missing:
        return current
    return missing[0]


def build_slot_question(slot_key: str) -> str:
    label = INTAKE_SLOT_LABELS.get(slot_key, slot_key)
    question = SLOT_QUESTIONS.get(slot_key, f"กรุณาให้ข้อมูลสำหรับ {label}")
    return f"ขอข้อมูล {label} ({slot_key}): {question}"


def append_next_slot_question(reply: str, slot_key: str | None) -> str:
    if not slot_key:
        return reply
    question = build_slot_question(slot_key)
    if question in reply:
        return reply
    return f"{reply.rstrip()}\n\n{question}"


_CHAT_SKIP_ANSWERS = {
    "สวัสดี",
    "ครับ",
    "ค่ะ",
    "ok",
    "โอเค",
    "ใช่",
    "ไม่",
    "ได้",
    "ครับผม",
}
REFERENCE_BLOCK = "\n\n--- อ้างอิงกฎหมาย ---\n"


def is_fill_reference_request(text: str) -> bool:
    raw = text.strip()
    return "ดึงอ้างอิง" in raw or "อ้างอิงกฎหมาย" in raw


def parse_fill_reference_request(text: str) -> str | None:
    if not is_fill_reference_request(text):
        return None
    lowered = text.strip().lower()
    for key in sorted(INTAKE_SLOT_LABELS, key=len, reverse=True):
        if key.lower() in lowered:
            return key
    return resolve_draft_section_key(text)


def fill_current_slot(
    slot_map: dict[str, Any],
    current_slot: str,
    answer: str,
) -> bool:
    """Fill the slot currently being asked. Never writes into a legal/reference gap."""
    text = answer.strip()
    if len(text) < 2:
        return False
    if text.lower() in _CHAT_SKIP_ANSWERS:
        return False
    if is_fill_reference_request(text):
        return False
    if current_slot not in FACT_REQUIRED_SLOTS:
        return False
    _write_chat_slot(slot_map, current_slot, text)
    return True


def apply_chat_answer_to_slots(slot_map: dict[str, Any], user_text: str) -> list[str]:
    """Sequential: the spoken answer fills the next empty fact slot only."""
    target = next_asking_slot(slot_map)
    if not target or not fill_current_slot(slot_map, target, user_text):
        return []
    return [target]


def slot_map_for_prompt(slot_map: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in INTAKE_SLOT_ORDER:
        slot = slot_map.get(key) or {}
        if not isinstance(slot, dict):
            continue
        label = INTAKE_SLOT_LABELS.get(key, key)
        content = str(slot.get("content") or "").strip()[:200]
        if _slot_is_filled(slot_map, key):
            lines.append(f"{key} {label} [ได้แล้ว]: {content}")
            continue
        if key in FACT_REQUIRED_SLOTS:
            lines.append(f"{key} {label} [ยังขาด]")
    return "\n".join(lines)


def build_phase2_opening(slot_map: dict[str, Any], gap_questions: list[str]) -> str:
    filled_lines: list[str] = []
    for key in INTAKE_SLOT_ORDER:
        if key not in FACT_REQUIRED_SLOTS:
            continue
        label = INTAKE_SLOT_LABELS.get(key, key)
        slot = slot_map.get(key) or {}
        content = str(slot.get("content") or "").strip() if isinstance(slot, dict) else ""
        if _slot_is_filled(slot_map, key):
            filled_lines.append(f"- {label}: {content[:160]}")
    parts = ["สวัสดีครับ ผมอ่านเอกสารจาก Phase 1 แล้ว สรุปให้ฟังสั้น ๆ นะครับ"]
    if filled_lines:
        parts.append("ข้อมูลที่จัดเข้าช่องได้แล้ว:")
        parts.extend(filled_lines)
    nxt = next_asking_slot(slot_map)
    if nxt:
        parts.append("ยังขาดข้อเท็จจริง — จะถามทีละช่อง")
        parts.append(build_slot_question(nxt))
        parts.append("ตอบช่องนี้ก่อนได้เลยครับ ไม่ต้องกรอกตาราง")
    else:
        parts.append(
            "ข้อเท็จจริงหลักครบแล้วครับ ถ้าไม่มีอะไรแก้ กดปุ่มยืนยันด้านบนเพื่อไปร่าง TOR ได้เลย"
        )
    extra = [str(item).strip() for item in gap_questions if str(item).strip()]
    if extra and nxt:
        parts.append("คำถามจากระบบวิเคราะห์: " + extra[0])
    return "\n".join(parts)


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


def slot_content(slot_map: dict[str, Any], key: str) -> str:
    slot = slot_map.get(key)
    if not isinstance(slot, dict):
        return ""
    return str(slot.get("content") or "")


def _has_pasted_text(project: Project) -> bool:
    texts = _extracted_dict(project).get("intake_texts") or []
    if not isinstance(texts, list):
        return False
    return any(isinstance(item, dict) and str(item.get("text") or "").strip() for item in texts)


def _has_intake_files(project: Project) -> bool:
    files = _analysis_dict(project).get("intake_files") or []
    return isinstance(files, list) and bool(files)


def _has_filled_slot(project: Project) -> bool:
    for slot in slot_map_of(project).values():
        if not isinstance(slot, dict):
            continue
        if slot.get("status") == "filled" and str(slot.get("content") or "").strip():
            return True
    return False


def has_intake_material(project: Project) -> bool:
    """True when the officer uploaded files, pasted text, or filled a slot."""
    return _has_pasted_text(project) or _has_intake_files(project) or _has_filled_slot(project)


def is_ready_to_compose(project: Project) -> bool:
    if not _analysis_dict(project).get("ready_to_compose"):
        return False
    return ready_criteria_met(slot_map_of(project))


def has_been_analyzed(project: Project) -> bool:
    analysis = _analysis_dict(project)
    if analysis.get("analyzed") is True:
        return True
    slot_map = analysis.get("slot_map")
    return isinstance(slot_map, dict) and bool(slot_map)


def is_phase4_confirmed(project: Project) -> bool:
    return bool(_analysis_dict(project).get("phase4_confirmed"))


def intake_unlocked_phase(project: Project) -> int:
    """Highest selectable phase: 0 upload-only, 2 analyzed, 3 compose, 4 confirmed."""
    if is_phase4_confirmed(project):
        return 4
    if is_ready_to_compose(project):
        return 3
    if has_been_analyzed(project):
        return 2
    return 0


def can_set_phase(project: Project, target: int) -> bool:
    if target < 0 or target > 4:
        return False
    current = int(project.current_phase or 0)
    if target <= current:
        return True
    return target <= intake_unlocked_phase(project)


def clamp_draft_phase(project: Project) -> bool:
    """Pull a draft back when the unlocked phase is lower. Returns True if changed."""
    if str(project.status or "") != "draft":
        return False
    current = int(project.current_phase or 0)
    unlocked = intake_unlocked_phase(project)
    if current <= unlocked:
        return False
    project.current_phase = unlocked
    return True


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


def _slot_map_from_paste(pack_text: str, filenames: list[str]) -> dict[str, Any]:
    slot_map = empty_slot_map()
    source = filenames[0] if filenames else "เอกสาร"
    for key, content in extract_slot_contents(pack_text).items():
        if key not in slot_map:
            continue
        slot_map[key] = {
            "content": content,
            "status": "filled",
            "sources": [source],
        }
    return slot_map


def _slot_map_from_llm_payload(payload: dict[str, Any]) -> dict[str, Any]:
    slot_map = empty_slot_map()
    incoming = payload.get("slot_map") if isinstance(payload.get("slot_map"), dict) else {}
    for key, value in incoming.items():
        if key not in slot_map or not isinstance(value, dict):
            continue
        status = value.get("status")
        if status not in {"filled", "gap", "reference_only"}:
            status = "gap"
        sources = value.get("sources")
        slot_map[key] = {
            "content": str(value.get("content") or ""),
            "status": status,
            "sources": sources if isinstance(sources, list) else [],
        }
    return slot_map


def _gap_questions_from_slots(
    slot_map: dict[str, Any], extra: list[str] | None = None
) -> list[str]:
    questions = [item for item in (extra or []) if item]
    if questions:
        return questions
    for key in FACT_REQUIRED_SLOTS:
        if (slot_map.get(key) or {}).get("status") != "filled":
            questions.append(f"ขอข้อมูลสำหรับ {INTAKE_SLOT_LABELS.get(key, key)} ({key})")
    return questions


async def _llm_analyze_slot_map(
    pack_text: str,
    filenames: list[str],
) -> tuple[dict[str, Any], list[str]]:
    llm = ProviderFactory().get_llm("structured")
    user = (
        f"ไฟล์: {', '.join(filenames)}\n\n"
        f"เนื้อหาที่สกัด (ตัดความยาว):\n{pack_text[:24000]}"
    )
    try:
        payload = await invoke_with_schema(
            llm,
            [
                {"role": "system", "content": ANALYZE_PROMPT},
                {"role": "user", "content": user},
            ],
            json_schema_for(IntakeAnalyzeResult),
            "intake_analyze",
            temperature=0.1,
            max_tokens=ANALYZE_MAX_TOKENS,
        )
    except (ValueError, OSError):
        # TimeoutError is an OSError subclass on Python 3.
        logger.warning("intake analyze JSON parse failed")
        return empty_slot_map(), [
            "จัดช่องจากโมเดลไม่สำเร็จ กรุณาตอบในแชทว่าโครงการนี้คืออะไร และวงเงินเท่าใด"
        ]
    extra: list[str] = []
    raw_q = payload.get("gap_questions")
    if isinstance(raw_q, list):
        extra = [str(item) for item in raw_q if str(item).strip()]
    return _slot_map_from_llm_payload(payload), extra


async def analyze_pack(project: Project, pack_text: str, filenames: list[str]) -> dict[str, Any]:
    slot_map = _slot_map_from_paste(pack_text, filenames)
    llm_gaps: list[str] = []
    if not facts_are_complete(slot_map):
        try:
            llm_map, llm_gaps = await asyncio.wait_for(
                _llm_analyze_slot_map(pack_text, filenames),
                timeout=ANALYZE_LLM_TIMEOUT_SEC,
            )
            slot_map = overlay_filled_slots(slot_map, llm_map)
        except TimeoutError:
            logger.warning("intake analyze LLM timed out for project %s", project.id)
        except OSError as exc:
            logger.warning("intake analyze LLM unavailable: %s", exc)
    return {
        "slot_map": slot_map,
        "gap_questions": _gap_questions_from_slots(slot_map, llm_gaps),
        "ready_to_compose": False,
        "analyzed": True,
    }


def _copy_slot_map(raw: dict[str, Any] | None) -> dict[str, Any]:
    source = raw or empty_slot_map()
    copied: dict[str, Any] = {}
    for key, value in source.items():
        copied[key] = dict(value) if isinstance(value, dict) else value
    return copied


def _merge_slot_sources(slot: dict[str, Any], incoming_sources: list) -> None:
    sources = list(slot.get("sources") or [])
    for item in incoming_sources:
        if item not in sources:
            sources.append(item)
    slot["sources"] = sources


def apply_reference_to_slot(
    slot_map: dict[str, Any],
    slot_key: str,
    filled: dict[str, Any],
    *,
    force_append: bool = False,
) -> str:
    """Merge RAG text into one slot. Never downgrade a filled fact slot.

    Returns: skipped | appended | filled
    """
    slot = slot_map.get(slot_key)
    if not isinstance(slot, dict):
        slot = {"content": "", "status": "gap", "sources": []}
        slot_map[slot_key] = slot
    content = str(slot.get("content") or "").strip()
    incoming = str(filled.get("content") or "").strip()
    incoming_sources = filled.get("sources") if isinstance(filled.get("sources"), list) else []
    if slot.get("status") != "filled" or not content:
        slot_map[slot_key] = {
            "content": incoming,
            "status": "reference_only",
            "sources": list(incoming_sources),
        }
        return "filled"
    if slot_key in FACT_REQUIRED_SLOTS and not force_append:
        return "skipped"
    if incoming and incoming not in content:
        slot["content"] = content + REFERENCE_BLOCK + incoming
    _merge_slot_sources(slot, incoming_sources)
    return "appended"


async def fill_non_fact_reference_slots(
    project: Project,
    user_id: UUID,
) -> dict[str, Any]:
    """Pull regulation excerpts into non-fact gap slots without clobbering facts."""
    filled_keys: list[str] = []
    last_map = _copy_slot_map(_analysis_dict(project).get("slot_map"))
    deadline = time.monotonic() + FILL_REFERENCES_TOTAL_SEC
    for key in INTAKE_SLOT_ORDER:
        if key in FACT_REQUIRED_SLOTS:
            continue
        remaining = deadline - time.monotonic()
        if remaining <= 0 or len(filled_keys) >= 8:
            break
        analysis = dict(_analysis_dict(project))
        slot_map = _copy_slot_map(analysis.get("slot_map"))
        slot = slot_map.get(key) or {}
        if not isinstance(slot, dict) or slot.get("status") != "gap":
            last_map = slot_map
            continue
        try:
            filled = await asyncio.wait_for(
                fill_reference_slot(key, user_id),
                timeout=min(FILL_ONE_REFERENCE_SEC, remaining),
            )
        except TimeoutError:
            last_map = slot_map
            continue
        if apply_reference_to_slot(slot_map, key, filled) != "filled":
            last_map = slot_map
            continue
        analysis["slot_map"] = slot_map
        project.analysis_json = analysis
        filled_keys.append(key)
        last_map = slot_map
    return {"filled_keys": filled_keys, "slot_map": last_map}


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
    if not row:
        db.add(
            TORSection(
                project_id=project_id,
                section_key=section_key,
                sub_key=sub_key,
                content=stripped,
                version=1,
            )
        )
        return
    if not (row.content or "").strip():
        row.content = stripped


async def apply_slot_map_to_sections(
    db: AsyncSession,
    project_id: UUID,
    slot_map: dict[str, Any],
) -> None:
    """Copy filled intake slots into TOR sections so Phase 2/3/review have real text."""
    for key in TOR_SECTION_ORDER:
        if key == "s4":
            continue
        await _upsert_section_text(db, project_id, key, None, slot_content(slot_map, key))
    parts: list[str] = []
    for sub_key, title in SCOPE_SUBSECTIONS.items():
        text = slot_content(slot_map, sub_key)
        if not text.strip():
            continue
        await _upsert_section_text(db, project_id, "s4", sub_key, text)
        parts.append(f"{title}: {text.strip()}")
    if parts:
        await _upsert_section_text(db, project_id, "s4", None, "\n\n".join(parts))


def resolve_draft_section_key(text: str) -> str | None:
    """Map a spoken Phase 3 request onto s1–s13. Longer numbers first."""
    raw = text.strip()
    if not raw:
        return None
    lowered = raw.lower()
    for key in TOR_SECTION_ORDER:
        label = TOR_SECTION_LABELS.get(key, "")
        if key in lowered or (label and label in raw):
            return key
    for number in range(13, 0, -1):
        if f"หมวด {number}" in raw or f"หมวดที่ {number}" in raw:
            return f"s{number}"
    return None


def build_phase3_opening() -> str:
    return (
        "ข้อมูลจาก Phase 1–2 ถูกจัดเข้าหมวดแล้วครับ "
        "ผมจะร่างเนื้อหา TOR ทั้ง 13 หมวดให้จากข้อมูลนั้น "
        "ถ้าต้องการแก้หมวดใด พิมพ์เป็นภาษาพูดได้เลย เช่น "
        "แก้ความเป็นมาให้เน้น พ.ร.บ. 2560 หรือ ร่างวงเงินใหม่"
    )
