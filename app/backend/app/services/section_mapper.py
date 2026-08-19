"""Map extracted content onto the 27 TOR slots via a single LLM pass."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from app.domain.slots import INTAKE_SLOT_ORDER
from app.providers.factory import ProviderFactory
from app.rag.graph_extract import parse_json_lenient
from app.services.intake_service import ANALYZE_PROMPT, empty_slot_map

logger = logging.getLogger("tor_app.section_mapper")

ANALYSIS_TIMEOUT = 90
INCREMENTAL_TIMEOUT = 5
RETRY_REDUCTION = 0.5
VALID_STATUSES = {"filled", "gap", "reference_only"}

INCREMENTAL_PROMPT = """คุณเป็นผู้ช่วยจัดทำ TOR ภาครัฐไทย
จำแนกคำตอบของผู้ใช้เข้าช่อง TOR แล้วตอบเป็น JSON เท่านั้น:

{
  "targets": [
    {"slot_key": "s1", "content": "ข้อความที่ใช้", "action": "append"}
  ]
}

action ได้เฉพาะ append หรือ replace
ใช้ replace เมื่อคำตอบชัดเจนว่าแก้/แทนที่ของเดิม หรืออ้างชื่อหมวดโดยตรง
slot_key ต้องเป็นหนึ่งใน s1-s13 หรือ s4.1-s4.14
ถ้าไม่มั่นใจ ให้เลือกไม่เกิน 5 ช่องที่เป็นไปได้
"""


@dataclass
class MappingResult:
    slot_map: dict[str, dict[str, Any]]
    partial: bool = False
    error: str | None = None


@dataclass
class IncrementalUpdateResult:
    slot_map: dict[str, dict[str, Any]]
    affected: list[str] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)
    error: str | None = None


def _normalize_slot(value: dict[str, Any]) -> dict[str, Any]:
    status = value.get("status")
    if status not in VALID_STATUSES:
        status = "gap"
    sources = value.get("sources")
    return {
        "content": str(value.get("content") or ""),
        "status": status,
        "sources": sources if isinstance(sources, list) else [],
    }


def apply_incoming_slots(
    base: dict[str, dict[str, Any]], incoming: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    slot_map = dict(base)
    for key, value in incoming.items():
        if key not in slot_map or not isinstance(value, dict):
            continue
        slot_map[key] = _normalize_slot(value)
    return slot_map


def mark_unmapped_errors(slot_map: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    updated = dict(slot_map)
    for key in INTAKE_SLOT_ORDER:
        slot = updated.get(key) or {}
        if slot.get("status") == "gap" and not str(slot.get("content") or "").strip():
            # leave gaps; errors are for failed mapping of remaining keys after hard fail
            continue
        updated.setdefault(key, {"content": "", "status": "gap", "sources": []})
    return updated


class SectionMapper:
    """Single-pass slot mapping and incremental answer updates."""

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    def _llm_client(self) -> Any:
        if self._llm is not None:
            return self._llm
        return ProviderFactory().get_llm()

    async def map_content(
        self,
        content: str,
        project_metadata: dict | None = None,
    ) -> MappingResult:
        slot_map = empty_slot_map()
        text = content or ""
        try:
            parsed = await self._analyze(text, project_metadata)
            slot_map = apply_incoming_slots(slot_map, parsed)
            return MappingResult(slot_map=slot_map)
        except Exception as exc:
            logger.warning("Section mapping failed, retrying reduced content: %s", exc)
        reduced = text[: max(1, int(len(text) * RETRY_REDUCTION))]
        try:
            parsed = await self._analyze(reduced, project_metadata)
            slot_map = apply_incoming_slots(slot_map, parsed)
            return MappingResult(slot_map=slot_map, partial=True, error="retry_reduced")
        except Exception as exc:
            logger.warning("Section mapping retry failed: %s", exc)
            for key, slot in slot_map.items():
                if slot.get("status") == "gap" and not str(slot.get("content") or ""):
                    slot_map[key] = {**slot, "status": "error"}
            return MappingResult(slot_map=slot_map, partial=True, error=str(exc))

    async def _analyze(self, content: str, project_metadata: dict | None) -> dict[str, Any]:
        meta = project_metadata or {}
        user = (
            f"โครงการ: {meta.get('name', '')}\n"
            f"กระทรวง: {meta.get('ministry', '')}\n"
            f"งบประมาณ: {meta.get('budget', '')}\n\n"
            f"{content}"
        )
        llm = self._llm_client()
        response = await asyncio.wait_for(
            llm.invoke(
                [
                    {"role": "system", "content": ANALYZE_PROMPT},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                max_tokens=8192,
            ),
            timeout=ANALYSIS_TIMEOUT,
        )
        payload = parse_json_lenient(getattr(response, "content", "") or "")
        incoming = payload.get("slot_map") if isinstance(payload, dict) else None
        return incoming if isinstance(incoming, dict) else {}

    async def incremental_update(
        self,
        answer_text: str,
        current_slot_map: dict[str, Any],
        context_questions: list[str] | None = None,
    ) -> IncrementalUpdateResult:
        slot_map = {key: dict(value) if isinstance(value, dict) else value
                    for key, value in (current_slot_map or empty_slot_map()).items()}
        for key in INTAKE_SLOT_ORDER:
            slot_map.setdefault(key, {"content": "", "status": "gap", "sources": []})
        try:
            targets = await self._classify(answer_text, context_questions or [])
        except Exception as exc:
            logger.warning("Incremental classify failed: %s", exc)
            return IncrementalUpdateResult(slot_map=slot_map, error=str(exc))
        if not targets:
            return IncrementalUpdateResult(
                slot_map=slot_map,
                candidates=list(INTAKE_SLOT_ORDER[:5]),
            )
        affected: list[str] = []
        for item in targets:
            key = str(item.get("slot_key") or "")
            if key not in slot_map:
                continue
            content = str(item.get("content") or answer_text).strip()
            if not content:
                continue
            action = item.get("action") if item.get("action") in {"append", "replace"} else "append"
            existing = str((slot_map[key] or {}).get("content") or "")
            merged = content if action == "replace" or not existing else f"{existing}\n{content}"
            sources = list((slot_map[key] or {}).get("sources") or [])
            sources.append("ผู้ใช้ตอบในแชท")
            slot_map[key] = {
                "content": merged.strip(),
                "status": "filled",
                "sources": sources,
            }
            affected.append(key)
        return IncrementalUpdateResult(slot_map=slot_map, affected=affected)

    async def _classify(self, answer_text: str, questions: list[str]) -> list[dict[str, Any]]:
        llm = self._llm_client()
        user = f"คำถามล่าสุด: {questions}\n\nคำตอบ: {answer_text}"
        response = await asyncio.wait_for(
            llm.invoke(
                [
                    {"role": "system", "content": INCREMENTAL_PROMPT},
                    {"role": "user", "content": user},
                ],
                temperature=0.2,
                max_tokens=2048,
            ),
            timeout=INCREMENTAL_TIMEOUT,
        )
        payload = parse_json_lenient(getattr(response, "content", "") or "")
        targets = payload.get("targets") if isinstance(payload, dict) else None
        if not isinstance(targets, list):
            return []
        return [item for item in targets if isinstance(item, dict)]
