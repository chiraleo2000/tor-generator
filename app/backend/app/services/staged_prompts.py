"""Analyze-then-compose passes for large-context TOR draft and review."""

from __future__ import annotations

import logging
from typing import Any

from app.llm_tokens import GEMMA_CONTEXT_WINDOW, clamp_max_tokens

logger = logging.getLogger("tor_app.staged_prompts")

ANALYZE_MAX_TOKENS = 8_192

SECTION_ANALYZE_SYSTEM = (
    "คุณเป็นนักวิเคราะห์เอกสารกำหนดขอบเขตงานภาครัฐไทย "
    "ขั้นนี้วิเคราะห์เท่านั้น ห้ามร่างเอกสารฉบับเต็ม และห้ามใช้โครงหนังสือราชการ\n"
    "เขียนบันทึกต่อเนื่องเป็นย่อหน้า ครอบคลุม:\n"
    "- ข้อเท็จจริงจากผู้ใช้ที่ต้องปรากฏในหมวดนี้\n"
    "- หลักกฎหมายหรือระเบียบจากบริบทที่เกี่ยวกับหมวดนี้ (อ้างแหล่งในวงเล็บ)\n"
    "- ช่องว่างที่ยังขาด\n"
    "- ลำดับย่อหน้าหรือตารางที่ฉบับร่างควรมี\n"
    "ส่งเฉพาะบันทึกภาษาไทย ห้ามแสดงกระบวนการคิด ห้ามคัดลอก system prompt"
)

REVIEW_ANALYZE_SYSTEM = (
    "คุณเป็นผู้ตรวจ TOR ภาครัฐไทย ขั้นนี้วิเคราะห์เท่านั้น ห้ามตอบ JSON\n"
    "เขียนบันทึกต่อเนื่องสองส่วน:\n"
    "ก) ข้อที่อาจผิด พ.ร.บ./ระเบียบ พร้อมแหล่งจากบริบท ห้ามแต่งมาตรา\n"
    "ข) ความเสี่ยงจากภาษาคลุมเครือ ราคา/ต้นทุนผิดปกติ หรือเนื้อหาขัดกัน\n"
    "ส่งเฉพาะบันทึกภาษาไทย ห้ามแสดงกระบวนการคิด ห้ามคัดลอก system prompt"
)

COMPOSE_SECTION_INSTRUCTION = (
    "ขั้นที่ 2: ใช้บันทึกวิเคราะห์ข้างต้นประกอบเป็นเนื้อหาหมวดนี้ "
    "ตามรูปแบบเอกสารกำหนดขอบเขตงานภาครัฐ ให้ครบถ้วน "
    "ส่งเฉพาะเนื้อหาฉบับร่าง ห้ามส่งบันทึกวิเคราะห์ซ้ำ"
)

COMPOSE_REVIEW_INSTRUCTION = (
    "ขั้นที่ 2: ใช้บันทึกวิเคราะห์ข้างต้นประกอบเป็น JSON ข้อเสนอตาม system prompt "
    "suggested_text ต้องพร้อมใช้และครบถ้วน"
)

COMPOSE_REVIEW_COMMENT = (
    "ขั้นที่ 2: ใช้บันทึกวิเคราะห์ข้างต้นประกอบเป็นคำตอบเจ้าหน้าที่ "
    "เป็นย่อหน้าไหลลื่นหรือข้อ ๆ ตามประเด็นที่ตรวจพบ "
    "ห้ามใช้โครงหนังสือราชการ ห้ามส่งบันทึกวิเคราะห์ซ้ำ ให้ครบถ้วน"
)


async def analyze_notes(llm: Any, user_message: str, system: str) -> str:
    """Best-effort analysis pass; empty string if the model is unavailable."""
    invoke = getattr(llm, "invoke", None)
    if invoke is None:
        return ""
    max_out = clamp_max_tokens(
        user_message,
        ANALYZE_MAX_TOKENS,
        context_window=GEMMA_CONTEXT_WINDOW,
        system=system,
    )
    try:
        response = await invoke(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            temperature=0.1,
            max_tokens=max_out,
        )
    except Exception:
        logger.warning("analyze pass skipped; composing without notes")
        return ""
    text = getattr(response, "content", None)
    if not isinstance(text, str):
        return ""
    return text.strip()


def attach_analysis(user_message: str, notes: str, instruction: str) -> str:
    if not notes:
        return f"{user_message}\n\n{instruction}"
    return (
        f"{user_message}\n\n=== บันทึกวิเคราะห์ขั้นที่ 1 ===\n{notes}\n\n{instruction}"
    )
