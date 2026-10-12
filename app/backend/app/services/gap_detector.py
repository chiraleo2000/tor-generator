"""Detect TOR slot gaps and generate Thai follow-up questions."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from app.domain.slots import (
    fact_required_slots,
    intake_slot_order,
    slot_key_aliases,
    slot_label,
)
from app.providers.factory import ProviderFactory
from app.providers.structured_invoke import invoke_with_schema
from app.schemas.llm_structured import GapQuestionsResult, json_schema_for

logger = logging.getLogger("tor_app.gap_detector")

MAX_QUESTIONS_PER_ROUND = 5
QUESTION_TIMEOUT = 30


@dataclass(frozen=True)
class GapInfo:
    slot_key: str
    label: str
    critical: bool
    status: str


def _slot_filled(slot_map: dict[str, Any], key: str) -> bool:
    for alias in slot_key_aliases(key):
        slot = slot_map.get(alias) or {}
        if not isinstance(slot, dict):
            continue
        content = str(slot.get("content") or "").strip()
        if slot.get("status") == "filled" and bool(content):
            return True
    return False


def _gap_from_slot(
    key: str,
    slot_map: dict[str, Any],
    facts: frozenset[str] | set[str],
    category: str | None,
) -> GapInfo | None:
    if _slot_filled(slot_map, key):
        return None
    slot = slot_map.get(key) if isinstance(slot_map.get(key), dict) else {}
    status = str((slot or {}).get("status") or "gap")
    content = str((slot or {}).get("content") or "").strip()
    fact_required = key in facts
    is_gap = status in {"gap", "reference_only", "error"} or not content
    if not is_gap or (not fact_required and status not in {"gap", "error"}):
        return None
    visible = status if status in {"gap", "reference_only", "error"} else "gap"
    return GapInfo(
        slot_key=key,
        label=slot_label(key, category),
        critical=fact_required,
        status=visible,
    )


QUESTION_PROMPT = """สร้างคำถามภาษาไทยราชการสั้น ๆ เพื่อขอข้อมูลที่ยังขาดใน TOR
ตอบเป็น JSON: {"questions": ["..."]}
แต่ละคำถามอ้างชื่อหมวดและบอกว่าขาดอะไร จำกัดไม่เกิน 5 ข้อ
จัดกลุ่มหมวดเดียวกันไว้ด้วยกัน
"""


class GapDetector:
    """Pure gap scan plus optional LLM question generation."""

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    def detect_gaps(
        self, slot_map: dict[str, Any], category: str | None = None
    ) -> list[GapInfo]:
        critical: list[GapInfo] = []
        other: list[GapInfo] = []
        mapping = slot_map if isinstance(slot_map, dict) else {}
        facts = fact_required_slots(category)
        for key in intake_slot_order(category):
            info = _gap_from_slot(key, mapping, facts, category)
            if info is None:
                continue
            if info.critical:
                critical.append(info)
            else:
                other.append(info)
        return critical + other

    def generic_questions(self, gaps: list[GapInfo]) -> list[str]:
        questions: list[str] = []
        for gap in gaps[:MAX_QUESTIONS_PER_ROUND]:
            questions.append(
                f"กรุณาระบุข้อมูลสำหรับ {gap.label} ({gap.slot_key}) ซึ่งยังขาดอยู่"
            )
        return questions

    async def generate_questions(
        self,
        gaps: list[GapInfo],
        project_context: dict | None = None,
    ) -> list[str]:
        selected = list(gaps[:MAX_QUESTIONS_PER_ROUND])
        if not selected:
            return []
        fallback = self.generic_questions(selected)
        llm = self._llm
        if llm is None:
            try:
                llm = ProviderFactory().get_llm("structured")
            except Exception as exc:
                logger.warning("Gap question LLM unavailable: %s", exc)
                return fallback
        labels = ", ".join(f"{g.slot_key} {g.label}" for g in selected)
        meta = project_context or {}
        user = f"โครงการ: {meta.get('name', '')}\nช่องที่ขาด: {labels}"
        try:
            payload = await asyncio.wait_for(
                invoke_with_schema(
                    llm,
                    [
                        {"role": "system", "content": QUESTION_PROMPT},
                        {"role": "user", "content": user},
                    ],
                    json_schema_for(GapQuestionsResult),
                    "gap_questions",
                    temperature=0.4,
                    max_tokens=2048,
                ),
                timeout=QUESTION_TIMEOUT,
            )
        except Exception as exc:
            logger.warning("Gap question generation failed: %s", exc)
            return fallback
        raw = payload.get("questions") if isinstance(payload, dict) else None
        if not isinstance(raw, list):
            return fallback
        questions = [str(item).strip() for item in raw if str(item).strip()]
        return questions[:MAX_QUESTIONS_PER_ROUND] or fallback
