"""Detect TOR slot gaps and generate Thai follow-up questions."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from app.domain.slots import FACT_REQUIRED_SLOTS, INTAKE_SLOT_LABELS, INTAKE_SLOT_ORDER
from app.providers.factory import ProviderFactory

logger = logging.getLogger("tor_app.gap_detector")

MAX_QUESTIONS_PER_ROUND = 5
QUESTION_TIMEOUT = 30


@dataclass(frozen=True)
class GapInfo:
    slot_key: str
    label: str
    critical: bool
    status: str


QUESTION_PROMPT = """สร้างคำถามภาษาไทยราชการสั้น ๆ เพื่อขอข้อมูลที่ยังขาดใน TOR
ตอบเป็น JSON: {"questions": ["..."]}
แต่ละคำถามอ้างชื่อหมวดและบอกว่าขาดอะไร จำกัดไม่เกิน 5 ข้อ
จัดกลุ่มหมวดเดียวกันไว้ด้วยกัน
"""


class GapDetector:
    """Pure gap scan plus optional LLM question generation."""

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    def detect_gaps(self, slot_map: dict[str, Any]) -> list[GapInfo]:
        critical: list[GapInfo] = []
        other: list[GapInfo] = []
        mapping = slot_map if isinstance(slot_map, dict) else {}
        for key in INTAKE_SLOT_ORDER:
            slot = mapping.get(key) if isinstance(mapping.get(key), dict) else {}
            status = str(slot.get("status") or "gap")
            content = str(slot.get("content") or "").strip()
            filled = status == "filled" and bool(content)
            if filled:
                continue
            fact_required = key in FACT_REQUIRED_SLOTS
            is_gap = status in {"gap", "reference_only", "error"} or not content
            if not is_gap:
                continue
            if not fact_required and status not in {"gap", "error"}:
                continue
            info = GapInfo(
                slot_key=key,
                label=INTAKE_SLOT_LABELS.get(key, key),
                critical=fact_required,
                status=status if status in {"gap", "reference_only", "error"} else "gap",
            )
            if fact_required:
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
                llm = ProviderFactory().get_llm()
            except Exception as exc:
                logger.warning("Gap question LLM unavailable: %s", exc)
                return fallback
        labels = ", ".join(f"{g.slot_key} {g.label}" for g in selected)
        meta = project_context or {}
        user = f"โครงการ: {meta.get('name', '')}\nช่องที่ขาด: {labels}"
        try:
            response = await asyncio.wait_for(
                llm.invoke(
                    [
                        {"role": "system", "content": QUESTION_PROMPT},
                        {"role": "user", "content": user},
                    ],
                    temperature=0.4,
                    max_tokens=2048,
                ),
                timeout=QUESTION_TIMEOUT,
            )
        except Exception as exc:
            logger.warning("Gap question generation failed: %s", exc)
            return fallback
        from app.rag.graph_extract import parse_json_lenient

        try:
            payload = parse_json_lenient(getattr(response, "content", "") or "")
        except ValueError:
            return fallback
        raw = payload.get("questions") if isinstance(payload, dict) else None
        if not isinstance(raw, list):
            return fallback
        questions = [str(item).strip() for item in raw if str(item).strip()]
        return questions[:MAX_QUESTIONS_PER_ROUND] or fallback
