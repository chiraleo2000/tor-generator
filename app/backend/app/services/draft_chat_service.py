"""Chat-driven TOR drafting service (Phase 3).

Auto-drafts all 13 sections using slot_map + RAG, then supports
conversational editing through accept/edit/redraft commands.
For s4, drafts into s4.1–s4.14 directly; top-level s4 keeps a short overview.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator
from uuid import UUID

from app.domain.tor_sections import SCOPE_SUBSECTIONS, TOR_SECTION_LABELS
from app.llm_tokens import (
    DRAFT_MAX_TOKENS,
    GEMMA_CONTEXT_WINDOW,
    SCOPE_SUB_MAX_TOKENS,
    SECTION_MAX_TOKENS,
    clamp_max_tokens,
)
from app.providers.factory import ProviderFactory
from app.rag.kb_qa import draft_rag_top_k
from app.rag.hybrid import hybrid_retrieve, unpack_hybrid
from app.services.intake_service import resolve_draft_section_key, slot_content
from app.services.thai_draft import (
    LENGTH_RULES,
    TABLE_FORMAT_HINT,
    THAI_ONLY_RULES,
    merge_scope_from_subs,
    scope_overview_from_subs,
    scope_sub_prompt,
)

logger = logging.getLogger("tor_app.draft_chat")

DRAFT_SYSTEM_PROMPT = (
    "คุณเป็นผู้เชี่ยวชาญร่างเอกสารกำหนดขอบเขตงานภาครัฐไทย "
    "ร่างเป็นภาษาราชการ ชัดเจน ครบถ้วน ตามโครงสร้าง "
    "พระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. ๒๕๖๐ "
    "ใช้ข้อมูลจากช่องข้อมูลและบริบทกฎหมายที่ให้มาเท่านั้น "
    "ห้ามแต่งมาตราที่ไม่มีในบริบท "
    "ให้ครบด้านวิธีจัดซื้อ ราคากลาง คุณสมบัติ ขอบเขต SLA งวดงาน ค่าปรับ "
    "เกณฑ์คัดเลือก เอกสารยื่น และเงื่อนไขลิขสิทธิ์/ความลับ ตามแนวทางตัวอย่าง TOR "
    "ขั้นที่ 2 ส่งเฉพาะเนื้อหาหมวดฉบับสมบูรณ์ตามรูปแบบเอกสารกำหนดขอบเขตงาน "
    "ห้ามส่งบันทึกวิเคราะห์ ห้ามย่อจนขาดสาระ\n"
    f"{THAI_ONLY_RULES}"
    f"{LENGTH_RULES}"
)

EDIT_SYSTEM_PROMPT = (
    "คุณเป็นผู้เชี่ยวชาญร่างเอกสารกำหนดขอบเขตงานภาครัฐไทย "
    "แก้ไขร่างตามข้อเสนอแนะของผู้ใช้ รักษาภาษาราชการ "
    "ห้ามเปลี่ยนข้อเท็จจริงที่ให้มาแล้ว ห้ามแต่งมาตราใหม่ "
    "คงความครบถ้วนและความยาวตามเอกสารตัวอย่าง เว้นแต่ผู้ใช้สั่งให้ย่อ\n"
    f"{THAI_ONLY_RULES}"
    f"{LENGTH_RULES}"
)


def _section_prompt_context(
    section_key: str,
    slot_map: dict[str, Any],
    rag_context: str,
) -> str:
    """Build user prompt for drafting a single section."""
    label = TOR_SECTION_LABELS.get(section_key, section_key)
    content = slot_content(slot_map, section_key)
    sub_content = ""
    if section_key == "s4":
        subs = [
            f"- {k} {SCOPE_SUBSECTIONS.get(k, k)}: {slot_content(slot_map, k)}"
            for k in SCOPE_SUBSECTIONS
            if slot_content(slot_map, k)
        ]
        sub_content = "\n".join(subs)

    parts = [
        f"ร่างหมวดที่ {section_key.replace('s', '')} ({label})",
        "",
        THAI_ONLY_RULES,
        TABLE_FORMAT_HINT,
    ]
    intake = slot_content(slot_map, "_project_intake").strip()
    if intake:
        parts.append(
            "เอกสารขั้นที่ ๐ ของโครงการนี้เท่านั้น (ห้ามใช้เอกสารโครงการอื่น):\n"
            + intake[:5000]
        )
    if content:
        parts.append(f"ข้อมูลที่มีจากขั้นวิเคราะห์:\n{content}")
    if sub_content:
        parts.append(f"\nรายละเอียดขอบเขตงาน:\n{sub_content}")
    if rag_context:
        parts.append(f"\nบริบทกฎหมาย/ระเบียบจากคลังความรู้:\n{rag_context}")
    if section_key == "s4":
        parts.append(
            "\nหมวดนี้ต้องร่างลงหัวข้อย่อย ๔.๑–๔.๑๔ โดยตรง "
            "ขึ้นต้นแต่ละหัวข้อด้วย ### s4.N ตามที่มีข้อมูล "
            "ห้ามรวมเป็นก้อนเดียวโดยไม่มี ###"
        )
    else:
        from app.domain.section_fields import field_prompt_block

        field_block = field_prompt_block(section_key)
        if field_block:
            parts.append(
                "\nร่างเป็นภาษาไทยเท่านั้น ใส่เนื้อหาลงหัวข้อย่อยตามรหัส ### "
                "ห้ามรวมเป็นก้อนเดียว และห้ามสร้างช่องรวม"
            )
            parts.append(field_block)
        else:
            parts.append(
                "\nร่างเนื้อหาเต็มสำหรับหมวดนี้เป็นภาษาไทยเท่านั้น "
                "ให้ยาวและครบถ้วนเทียบเอกสารตัวอย่าง ไม่ต้องใส่หัวข้อหมวดซ้ำ"
            )
    parts.append(LENGTH_RULES)
    return "\n".join(parts)


def fallback_section_text(section_key: str, slot_map: dict[str, Any]) -> str:
    """Thai draft from intake slots when the LLM returns nothing or times out."""
    from app.domain.section_fields import SECTION_FIELDS

    label = TOR_SECTION_LABELS.get(section_key, section_key)
    facts = slot_content(slot_map, section_key).strip()
    intake = slot_content(slot_map, "_project_intake").strip()
    body = facts or intake[:1200]
    rows = SECTION_FIELDS.get(section_key) or []
    if not rows:
        return body or (
            f"หมวด{label} ใช้ข้อมูลจากเอกสารขั้นที่ ๐ ของโครงการนี้ "
            "เจ้าหน้าที่ควรตรวจและเติมรายละเอียดก่อนประกาศ"
        )
    chunks: list[str] = []
    for key, thai in rows:
        chunks.append(f"### {key}")
        chunks.append(f"({thai})")
        chunks.append(
            body or f"ให้ระบุ{thai}ตามเอกสารอนุมัติและขอบเขตงานของโครงการนี้"
        )
    return "\n".join(chunks)


def fallback_scope_subsection(sub_key: str, slot_map: dict[str, Any]) -> str:
    """Fill one s4.x block from slots when the model skips or hangs."""
    title = SCOPE_SUBSECTIONS.get(sub_key, sub_key)
    facts = slot_content(slot_map, sub_key).strip()
    parent = slot_content(slot_map, "s4").strip()
    intake = slot_content(slot_map, "_project_intake").strip()
    return facts or parent[:800] or intake[:800] or (
        f"{title}: ใช้ข้อมูลจากเอกสารขั้นที่ ๐ ของโครงการนี้ "
        "เจ้าหน้าที่ควรตรวจและเติมรายละเอียดก่อนประกาศ"
    )


_s4_rag_pack: dict[str, str] = {}


def clear_s4_rag_cache() -> None:
    """Drop the shared s4 hybrid pack (call at the start of a sequential job)."""
    _s4_rag_pack.clear()


async def _hybrid_rag_pack(
    query: str,
    *,
    user_id: UUID | str | None,
    section_relevance: str,
    top_k: int,
    chunk_n: int,
    chunk_chars: int,
) -> str:
    result, _citations, _degraded, _mcp = unpack_hybrid(
        await hybrid_retrieve(
            query,
            user_id=user_id,
            search_scope="global",
            section_relevance=section_relevance,
            top_k=top_k,
        )
    )
    return "\n".join(c.text[:chunk_chars] for c in result.chunks[:chunk_n])


async def _s4_shared_rag(user_id: UUID | str | None) -> str:
    key = str(user_id or "anon")
    cached = _s4_rag_pack.get(key)
    if cached is not None:
        return cached
    try:
        pack = await _hybrid_rag_pack(
            "ขอบเขตงาน จัดซื้อจัดจ้างภาครัฐ พ.ร.บ. 2560",
            user_id=user_id,
            section_relevance="s4",
            top_k=max(6, draft_rag_top_k() // 2),
            chunk_n=8,
            chunk_chars=800,
        )
    except Exception:
        pack = ""
    _s4_rag_pack[key] = pack
    return pack


async def _stream_llm_prompt(
    system: str, user_prompt: str, *, max_tokens: int = DRAFT_MAX_TOKENS
) -> AsyncIterator[str]:
    """Stream one compose pass from the configured LLM (no analyze-then-compose)."""
    llm = ProviderFactory().get_llm("draft")  # NOSONAR python:S930
    max_out = clamp_max_tokens(
        user_prompt,
        max_tokens,
        context_window=GEMMA_CONTEXT_WINDOW,
        system=system,
    )
    async for token in llm.stream(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=max_out,
        disable_thinking=True,
    ):
        yield token


async def draft_single_section(
    section_key: str,
    slot_map: dict[str, Any],
    user_id: UUID | str | None = None,
) -> AsyncIterator[str]:
    """Draft one section using LLM + RAG. Yields tokens from the model only."""
    label = TOR_SECTION_LABELS.get(section_key, section_key)
    slot_facts = slot_content(slot_map, section_key).strip()
    query = f"ขอบเขตของงาน {label} {slot_facts[:200]}"
    try:
        rag_context = await _hybrid_rag_pack(
            query,
            user_id=user_id,
            section_relevance=section_key,
            top_k=draft_rag_top_k(),
            chunk_n=8,
            chunk_chars=800,
        )
    except Exception:
        logger.warning("RAG failed for %s, proceeding without context", section_key)
        rag_context = ""

    user_prompt = _section_prompt_context(section_key, slot_map, rag_context)
    async for token in _stream_llm_prompt(
        DRAFT_SYSTEM_PROMPT,
        user_prompt,
        max_tokens=SECTION_MAX_TOKENS,
    ):
        yield token


async def draft_scope_subsection(
    sub_key: str,
    slot_map: dict[str, Any],
    user_id: UUID | str | None = None,
) -> AsyncIterator[str]:
    """Draft one s4.x subsection from the LLM into its own content block."""
    rag_context = await _s4_shared_rag(user_id)
    prompt = scope_sub_prompt(sub_key, slot_map, rag_context)
    async for token in _stream_llm_prompt(
        DRAFT_SYSTEM_PROMPT, prompt, max_tokens=SCOPE_SUB_MAX_TOKENS
    ):
        yield token


async def collect_scope_subsection_drafts(
    slot_map: dict[str, Any],
    user_id: UUID | str | None = None,
    *,
    only_missing: bool = False,
    existing: dict[str, str] | None = None,
) -> dict[str, str]:
    """Draft s4.1–s4.14 one LM Studio call at a time; skip only prior LLM drafts."""
    out: dict[str, str] = {}
    for sub_key in SCOPE_SUBSECTIONS:
        prior = str((existing or {}).get(sub_key) or "").strip()
        if only_missing and prior:
            out[sub_key] = prior
            continue
        parts: list[str] = []
        async for token in draft_scope_subsection(sub_key, slot_map, user_id=user_id):
            parts.append(token)
        text = "".join(parts).strip()
        if text:
            out[sub_key] = text
    return out


def build_merged_scope(subs: dict[str, str]) -> str:
    return merge_scope_from_subs(subs)


def build_scope_overview(subs: dict[str, str]) -> str:
    return scope_overview_from_subs(subs)


async def edit_section_draft(
    section_key: str,
    current_draft: str,
    feedback: str,
    slot_map: dict[str, Any],
) -> AsyncIterator[str]:
    """Re-draft a section with user feedback. Yields tokens."""
    label = TOR_SECTION_LABELS.get(section_key, section_key)
    intake = slot_content(slot_map, section_key).strip()
    intake_block = f"\n\nข้อมูลจากขั้นวิเคราะห์:\n{intake[:8000]}" if intake else ""
    s4_hint = ""
    if section_key == "s4":
        s4_hint = " คงรูปแบบ ### s4.N และใส่เนื้อหาลงหัวข้อย่อยโดยตรง"
    user_prompt = (
        f"หมวด {section_key.replace('s', '')} ({label})\n\n"
        f"ร่างปัจจุบัน:\n{current_draft[:24000]}"
        f"{intake_block}\n\n"
        f"ข้อเสนอแนะจากผู้ใช้:\n{feedback}\n\n"
        f"{THAI_ONLY_RULES}\n"
        "กรุณาแก้ไขร่างตามข้อเสนอแนะ คืนร่างใหม่ทั้งหมดเป็นภาษาไทยเท่านั้น "
        f"(ไม่ต้องใส่หัวข้อหมวดซ้ำ){s4_hint}"
    )
    from app.domain.section_fields import field_prompt_block

    field_block = field_prompt_block(section_key)
    if field_block:
        user_prompt += "\n\nคงการแยกหัวข้อย่อย:\n" + field_block
    async for token in _stream_llm_prompt(
        EDIT_SYSTEM_PROMPT, user_prompt, max_tokens=DRAFT_MAX_TOKENS
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
