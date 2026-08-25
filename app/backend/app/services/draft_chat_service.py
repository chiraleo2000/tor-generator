"""Chat-driven TOR drafting service (Phase 3).

Auto-drafts all 13 sections using slot_map + RAG, then supports
conversational editing through accept/edit/redraft commands.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator
from uuid import UUID

from app.domain.tor_sections import TOR_SECTION_LABELS
from app.providers.factory import ProviderFactory
from app.rag.hybrid import hybrid_retrieve
from app.services.intake_service import resolve_draft_section_key, slot_content

logger = logging.getLogger("tor_app.draft_chat")

DRAFT_STREAM_TIMEOUT_SEC = 90

DRAFT_SYSTEM_PROMPT = (
    "คุณเป็นผู้เชี่ยวชาญร่าง TOR (Terms of Reference) ภาครัฐไทย "
    "ร่างเป็นภาษาราชการ กระชับ ชัดเจน ตามโครงสร้าง พ.ร.บ. การจัดซื้อจัดจ้างฯ 2560 "
    "ใช้ข้อมูลจาก slot_map และบริบทกฎหมายที่ให้มาเท่านั้น "
    "ห้ามแต่งมาตราที่ไม่มีในบริบท"
)

EDIT_SYSTEM_PROMPT = (
    "คุณเป็นผู้เชี่ยวชาญร่าง TOR ภาครัฐไทย "
    "แก้ไขร่างตามข้อเสนอแนะของผู้ใช้ รักษาภาษาราชการ "
    "ห้ามเปลี่ยนข้อเท็จจริงที่ให้มาแล้ว ห้ามแต่งมาตราใหม่"
)


def _section_prompt_context(
    section_key: str,
    slot_map: dict[str, Any],
    rag_context: str,
) -> str:
    """Build user prompt for drafting a single section."""
    label = TOR_SECTION_LABELS.get(section_key, section_key)
    content = slot_content(slot_map, section_key)
    # Also include related sub-keys for s4
    sub_content = ""
    if section_key == "s4":
        subs = [
            f"- {k}: {slot_content(slot_map, k)}"
            for k in slot_map
            if k.startswith("s4.") and slot_content(slot_map, k)
        ]
        sub_content = "\n".join(subs)

    parts = [
        f"ร่างหมวดที่ {section_key.replace('s', '')} ({label})",
        "",
    ]
    if content:
        parts.append(f"ข้อมูลที่มีจาก intake:\n{content}")
    if sub_content:
        parts.append(f"\nรายละเอียดขอบเขตงาน:\n{sub_content}")
    if rag_context:
        parts.append(f"\nบริบทกฎหมาย/ระเบียบจากคลังความรู้:\n{rag_context}")
    parts.append(
        "\nร่างเนื้อหาเต็มสำหรับหมวดนี้เป็นภาษาราชการ "
        "ความยาว 100-500 คำ ไม่ต้องใส่หัวข้อหมวดซ้ำ"
    )
    return "\n".join(parts)


def fallback_section_prose(section_key: str, slot_map: dict[str, Any]) -> str:
    """Official-language fallback when the local LLM stream times out."""
    label = TOR_SECTION_LABELS.get(section_key, section_key)
    facts = slot_content(slot_map, section_key).strip()
    if not facts:
        facts = "ใช้ข้อมูลจากเอกสารโครงการที่รับเข้าในขั้นตอนวิเคราะห์ความต้องการ"
    return (
        f"{label} กำหนดไว้ดังนี้ {facts} "
        "ให้ดำเนินการให้ถูกต้องตามพระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ "
        "พ.ศ. 2560 และระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ "
        "พ.ศ. 2560 รวมทั้งหนังสือเวียนกรมบัญชีกลางที่เกี่ยวข้อง"
    )


async def draft_single_section(
    section_key: str,
    slot_map: dict[str, Any],
    user_id: UUID | str | None = None,
) -> AsyncIterator[str]:
    """Draft one section using LLM + RAG. Yields tokens."""
    label = TOR_SECTION_LABELS.get(section_key, section_key)
    # Retrieve RAG context for this section
    query = f"TOR {label} {slot_content(slot_map, section_key)[:200]}"
    try:
        result, _citations, _degraded = await hybrid_retrieve(
            query,
            user_id=user_id,
            search_scope="global",
            section_relevance=section_key,
            top_k=3,
        )
        rag_context = "\n".join(c.text[:400] for c in result.chunks[:3])
    except Exception:
        logger.warning("RAG failed for %s, proceeding without context", section_key)
        rag_context = ""

    user_prompt = _section_prompt_context(section_key, slot_map, rag_context)
    llm = ProviderFactory().get_llm("draft")
    yielded = False
    try:
        async with asyncio.timeout(DRAFT_STREAM_TIMEOUT_SEC):
            async for token in llm.stream(
                [
                    {"role": "system", "content": DRAFT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=2048,
                disable_thinking=True,
            ):
                yielded = True
                yield token
    except OSError:
        # TimeoutError and ConnectionError are OSError subclasses on Python 3.
        logger.warning("draft stream failed for %s; using slot fallback", section_key)
        if not yielded:
            yield fallback_section_prose(section_key, slot_map)


async def edit_section_draft(
    section_key: str,
    current_draft: str,
    feedback: str,
    slot_map: dict[str, Any],
) -> AsyncIterator[str]:
    """Re-draft a section with user feedback. Yields tokens."""
    label = TOR_SECTION_LABELS.get(section_key, section_key)
    intake = slot_content(slot_map, section_key).strip()
    intake_block = f"\n\nข้อมูลจาก intake:\n{intake[:1500]}" if intake else ""
    user_prompt = (
        f"หมวด {section_key.replace('s', '')} ({label})\n\n"
        f"ร่างปัจจุบัน:\n{current_draft[:3000]}"
        f"{intake_block}\n\n"
        f"ข้อเสนอแนะจากผู้ใช้:\n{feedback}\n\n"
        "กรุณาแก้ไขร่างตามข้อเสนอแนะ คืนร่างใหม่ทั้งหมด (ไม่ต้องใส่หัวข้อหมวดซ้ำ)"
    )
    llm = ProviderFactory().get_llm("draft")
    async for token in llm.stream(
        [
            {"role": "system", "content": EDIT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=2048,
        disable_thinking=True,
    ):
        yield token


def parse_draft_message_intent(
    message: str,
) -> tuple[str, str | None, str]:
    """Parse user message intent for draft chat.

    Returns: (intent, section_key, detail)
    intent: "accept" | "edit" | "redraft" | "freeform"
    """
    raw = message.strip()
    lower = raw.lower()
    key = resolve_draft_section_key(raw)
    if lower in ("ดี", "โอเค", "ok", "ยอมรับ", "ผ่าน", "ใช้ได้"):
        return "accept", key, message
    if "ร่างใหม่" in lower:
        return "redraft", key, message
    if lower.startswith(("แก้ไข", "แก้")):
        return "edit", key, message
    return "freeform", key, message
