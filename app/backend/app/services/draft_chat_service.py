"""Chat-driven TOR drafting service (Phase 3).

Auto-drafts all 13 sections using slot_map + RAG, then supports
conversational editing through accept/edit/redraft commands.
For s4, drafts into s4.1–s4.14 directly; top-level s4 keeps a short overview.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator
from uuid import UUID

from app.domain.section_profile import profile_for_project, subsection_title
from app.domain.tor_sections import TOR_SECTION_LABELS
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
    SUBSTANCE_RULES,
    THAI_ONLY_RULES,
    attach_thai_only,
    detect_unauthorized_english,
    merge_scope_from_subs,
    official_tor_style_block,
    scope_overview_from_subs,
    scope_sub_prompt,
    section_boundary_hint,
)

logger = logging.getLogger("tor_app.draft_chat")

DRAFT_SYSTEM_PROMPT = (
    "คุณเป็นผู้เชี่ยวชาญร่างเอกสารกำหนดขอบเขตงานภาครัฐไทย "
    "ร่างเป็นภาษาราชการ ชัดเจน ครบถ้วน ตามโครงสร้าง "
    "พระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. ๒๕๖๐ "
    "ใช้ข้อมูลจากช่องข้อมูลและบริบทกฎหมายที่ให้มาเท่านั้น "
    "ห้ามแต่งมาตราที่ไม่มีในบริบท "
    "ให้ครบด้านวิธีจัดซื้อ ราคากลาง คุณสมบัติ ขอบเขตระดับการให้บริการ งวดงาน ค่าปรับ "
    "เกณฑ์คัดเลือก เอกสารยื่น และเงื่อนไขลิขสิทธิ์หรือความลับ ตามแนวทางตัวอย่าง "
    "ก่อนร่างแต่ละหัวข้อ จำแนกสาระจากเอกสารต้นทางว่าเป็นของหัวข้อนั้นจริงหรือไม่ "
    "ห้ามยกทั้งหมวดหรือทั้งตารางไปวางผิดหัวข้อ "
    "ขั้นที่ 2 ส่งเฉพาะเนื้อหาหมวดฉบับสมบูรณ์ตามรูปแบบเอกสารกำหนดขอบเขตงาน "
    "ห้ามส่งบันทึกวิเคราะห์ ห้ามย่อจนขาดสาระ "
    "ห้ามพิมพ์เลขนำหน้าชื่อหมวดหรือข้อย่อย (ทั้งเลขไทยและอารบิก เช่น ๘.๑ 8.1.2) "
    "— ระบบส่งออกเป็นผู้ใส่หัวข้อ "
    "ตัวเลขในเนื้อหา วันที่ และตารางใช้เลขไทยได้ "
    "ตารางใช้มาร์กดาวน์คอลัมน์เดียวชุด ห้ามพิมพ์ [Table N] ห้ามซ้ำแถวหัวตาราง "
    "ห้ามพิมพ์ป้ายช่องข้อมูลหรือรหัสภาษาอังกฤษเป็นหัวข้อ\n"
    f"{THAI_ONLY_RULES}"
    f"{SUBSTANCE_RULES}"
)

EDIT_SYSTEM_PROMPT = (
    "คุณเป็นผู้เชี่ยวชาญร่างเอกสารกำหนดขอบเขตงานภาครัฐไทย "
    "แก้ไขร่างตามข้อเสนอแนะของผู้ใช้ รักษาภาษาราชการ "
    "ห้ามเปลี่ยนข้อเท็จจริงที่ให้มาแล้ว ห้ามแต่งมาตราใหม่ "
    "คงสาระครบถ้วนตามข้อมูลที่มี ห้ามเติมน้ำหรือซ้ำข้ามหมวด เว้นแต่ผู้ใช้สั่งให้ย่อ\n"
    f"{THAI_ONLY_RULES}"
    f"{SUBSTANCE_RULES}"
)


def _section_prompt_context(
    section_key: str,
    slot_map: dict[str, Any],
    rag_context: str,
    category: str | None = None,
) -> str:
    """Build user prompt for drafting a single section."""
    profile = profile_for_project(category)
    label = next(
        (item.title for item in profile.main_sections if item.storage_key == section_key),
        TOR_SECTION_LABELS.get(section_key, section_key),
    )
    content = slot_content(slot_map, section_key)
    sub_content = ""
    if section_key == "s4":
        subs = [
            f"- {item.storage_key} {item.title}: {slot_content(slot_map, item.storage_key)}"
            for item in profile.scope_subsections
            if slot_content(slot_map, item.storage_key)
        ]
        sub_content = "\n".join(subs)

    parts = [
        f"ร่างหมวด ({label}) ประเภทงาน {profile.label}",
        "",
        THAI_ONLY_RULES,
        official_tor_style_block(category, section_key),
    ]
    boundary = section_boundary_hint(section_key)
    if boundary:
        parts.append(boundary)
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
        listed = "\n".join(f"- {item.title}" for item in profile.scope_subsections)
        parts.append(
            "\nหมวดนี้ต้องร่างตามหัวข้อย่อยของประเภทงาน "
            "ใช้ชื่อหัวข้อย่อยตามรายการต่อไปนี้ ห้ามใส่เลขนำหน้าชื่อหัวข้อ "
            "ห้ามใช้รหัสภาษาอังกฤษเป็นหัวข้อ:\n"
            f"{listed}\n"
            "ห้ามรวมเป็นก้อนเดียวโดยไม่มีหัวข้อย่อย และห้ามใส่หัวข้อที่ไม่อยู่ในรายการ"
        )
    else:
        from app.domain.section_fields import field_prompt_block

        field_block = field_prompt_block(section_key)
        if field_block:
            parts.append(
                "\nร่างเป็นภาษาไทยราชการด้วยหัวข้อตามสาระของหมวด "
                "ห้ามพิมพ์เลขนำหน้าชื่อหมวด ห้ามพิมพ์รหัสภาษาอังกฤษหรือป้ายช่องข้อมูลเป็นหัวข้อ"
            )
            parts.append(field_block)
        else:
            parts.append(
                "\nร่างเนื้อหาสำหรับหมวดนี้เป็นภาษาไทยเท่านั้น "
                "ให้ครบสาระตามข้อมูลที่มี ไม่เติมน้ำ ไม่ซ้ำหมวดอื่น "
                "ไม่ต้องใส่หัวข้อหมวดซ้ำ"
            )
    parts.append(SUBSTANCE_RULES)
    return "\n".join(parts)


def fallback_section_text(section_key: str, slot_map: dict[str, Any]) -> str:
    """Thai draft from intake slots when the LLM returns nothing or times out."""
    label = TOR_SECTION_LABELS.get(section_key, section_key)
    facts = slot_content(slot_map, section_key).strip()
    intake = slot_content(slot_map, "_project_intake").strip()
    body = facts or intake[:1200]
    return body or (
        f"หมวด{label} ใช้ข้อมูลจากเอกสารขั้นที่ ๐ ของโครงการนี้ "
        "เจ้าหน้าที่ควรตรวจและเติมรายละเอียดก่อนประกาศ"
    )


def fallback_scope_subsection(
    sub_key: str, slot_map: dict[str, Any], category: str | None = None
) -> str:
    """Fill one scope subsection from slots when the model skips or hangs."""
    title = subsection_title(sub_key, category, sub_key)
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


async def _collect_llm_text(
    system: str, user_prompt: str, *, max_tokens: int
) -> str:
    llm = ProviderFactory().get_llm("draft")  # NOSONAR python:S930
    max_out = clamp_max_tokens(
        user_prompt,
        max_tokens,
        context_window=GEMMA_CONTEXT_WINDOW,
        system=system,
    )
    parts: list[str] = []
    async for token in llm.stream(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=max_out,
        enable_thinking=True,
    ):
        parts.append(token)
    return "".join(parts)


async def _stream_llm_prompt(
    system: str, user_prompt: str, *, max_tokens: int = DRAFT_MAX_TOKENS
) -> AsyncIterator[str]:
    """Stream one compose pass from the configured LLM (no analyze-then-compose)."""
    from app.services.thai_draft import sanitize_unauthorized_english, thai_char_count

    system = attach_thai_only(system)
    user_prompt = attach_thai_only(user_prompt)
    text = await _collect_llm_text(system, user_prompt, max_tokens=max_tokens)
    if detect_unauthorized_english(text):
        logger.warning("draft contained unauthorized English; retrying once")
        text = await _collect_llm_text(system, user_prompt, max_tokens=max_tokens)
        if detect_unauthorized_english(text):
            cleaned = sanitize_unauthorized_english(text)
            if thai_char_count(cleaned) >= 40:
                logger.warning(
                    "draft retry still had English; using sanitized Thai (%s chars)",
                    len(cleaned),
                )
                text = cleaned
            else:
                logger.warning(
                    "draft retry still contained unauthorized English; dropping"
                )
                return
    if text:
        yield text


async def draft_single_section(
    section_key: str,
    slot_map: dict[str, Any],
    user_id: UUID | str | None = None,
    category: str | None = None,
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

    user_prompt = _section_prompt_context(section_key, slot_map, rag_context, category)
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
    category: str | None = None,
    *,
    current_draft: str | None = None,
    user_feedback: str | None = None,
) -> AsyncIterator[str]:
    """Draft one scope subsection from the LLM into its own content block."""
    rag_context = await _s4_shared_rag(user_id)
    prompt = scope_sub_prompt(
        sub_key,
        slot_map,
        rag_context,
        category,
        current_draft=current_draft,
        user_feedback=user_feedback,
    )
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
    category: str | None = None,
) -> dict[str, str]:
    """Draft profile scope subsections one LLM call at a time."""
    out: dict[str, str] = {}
    for item in profile_for_project(category).scope_subsections:
        sub_key = item.storage_key
        prior = str((existing or {}).get(sub_key) or "").strip()
        if only_missing and prior:
            out[sub_key] = prior
            continue
        parts: list[str] = []
        async for token in draft_scope_subsection(
            sub_key, slot_map, user_id=user_id, category=category
        ):
            parts.append(token)
        text = "".join(parts).strip()
        if text:
            from app.services.thai_draft import polish_scope_subsection_draft

            out[sub_key] = polish_scope_subsection_draft(text, sub_key)
    return out


def build_merged_scope(subs: dict[str, str], category: str | None = None) -> str:
    return merge_scope_from_subs(subs, category)


def build_scope_overview(subs: dict[str, str], category: str | None = None) -> str:
    return scope_overview_from_subs(subs, category)


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
        s4_hint = " คงหัวข้อย่อยตามโปรไฟล์โดยไม่ใส่เลขนำหน้าชื่อ และใส่เนื้อหาลงหัวข้อย่อยโดยตรง"
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
        user_prompt += "\n\n" + official_tor_style_block(None, section_key)
        user_prompt += "\n\nสาระที่ต้องคงไว้ในเนื้อหา:\n" + field_block
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
