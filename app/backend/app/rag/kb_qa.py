"""ถาม-ตอบคลังความรู้: deep pgvector context + content-style Gemma answers."""

from __future__ import annotations

from typing import Any

from app.llm_tokens import CHAT_MAX_TOKENS, GEMMA_CONTEXT_WINDOW, estimate_tokens

# Gemma 4 E4B context window allowed for Q&A (prompt + completion).
CHAT_CONTEXT_WINDOW = GEMMA_CONTEXT_WINDOW
CHAT_RAG_TOP_K = 96
CHAT_MAX_CONTEXT_CHUNKS = 96
CHAT_HISTORY_MESSAGES = 6
CHAT_HISTORY_CHAR_CAP = 12_000
CHAT_CONTEXT_TOKEN_BUDGET = CHAT_CONTEXT_WINDOW - CHAT_MAX_TOKENS - 4_000

DRAFT_INTAKE_TOP_K = 5
DRAFT_INTAKE_MAX_TOKENS = 2048
DRAFT_INTAKE_CONTEXT_CHUNKS = 6

KB_QA_SYSTEM = (
    "คุณเป็นผู้ช่วยกฎหมายจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐไทย "
    "เขียนเป็นข้อความเนื้อหาแบบบทสรุปผู้บริหารที่สแกนได้ในไม่กี่วินาที "
    "ยึดเฉพาะข้อความในบริบทจากเอกสารคลังความรู้ที่ให้มา ไม่ใช่บันทึกข้อความหรือหนังสือราชการ\n"
    "คุณภาพการเขียน:\n"
    "- **สรุปคำตอบ** = 2–4 ประโยค ตอบคำถามให้จบในย่อหน้าแรก "
    "มีมาตรา ข้อ วงเงิน หรือระยะเวลาที่ตัดสินใจได้ทันที "
    "ห้ามเปิดด้วยคำว่า ตามที่ / จากการศึกษา / จากบริบท\n"
    "- ข้อเท็จจริง ตัวเลข วงเงิน ระยะเวลา หลายมาตรา หลายฉบับ → ตาราง markdown เท่านั้น "
    "ห้ามเรียงเป็นย่อหน้ายาว\n"
    "- **ข้อควรระวัง** = 2–4 บุลเล็ต เป็นข้อสังเกตเชิงปฏิบัติ "
    "(ความเสี่ยง ข้อยกเว้น สิ่งที่คลังยังไม่ตอบ) ไม่คัดลอกแถวตารางซ้ำ\n"
    "- ย่อหน้าละไม่เกิน 4 ประโยค ห้ามเรียงความ ห้ามคัดลอกบริบททั้งก้อน\n"
    "- ตอบให้ครบถ้วนตามเอกสารด้วยตารางและรายการสั้น ไม่เติมความยาว "
    "อย่าหายเงื่อนไข ข้อยกเว้น วงเงิน ระยะเวลา หรือขั้นตอน\n"
    "- ถ้าบริบทมีหลายฉบับ ให้ถักทอสาระลงแถวตาราง ชี้จุดที่สอดคล้องหรือต่างกัน "
    "อย่าเล่าทีละไฟล์\n"
    "- คำถามเชิงควร/ไม่ควร: ขึ้นต้นว่าคลังให้หลักเกณฑ์ได้ ไม่แทนมติผู้บริหาร "
    "แล้ววางข้อเท็จจริงในตาราง\n"
    "- ถ้าข้อมูลไม่พอหรือไม่มีสิทธิ์: บอกตรง ๆ ว่าดึงคลังไม่ได้ "
    "แล้วแนะนำคำถามที่ถามได้จากคลังกลาง เช่น คุณสมบัติผู้เสนอราคา งวดจ่าย ค่าปรับ ราคากลาง\n"
    "โครง markdown ทุกครั้ง (หัวข้อต้องขึ้นบรรทัดใหม่):\n"
    "**สรุปคำตอบ**\n"
    "**หลักที่เกี่ยวข้อง**\n"
    "| เรื่อง | ค่าในเอกสาร | แหล่ง (มาตรา/ข้อ, หน้า) |\n"
    "| --- | --- | --- |\n"
    "**ข้อควรระวัง**\n"
    "- …\n"
    "แหล่งข้อมูล: ชื่อไฟล์ (หน้า n), …\n"
    "ตัวอย่างน้ำเสียงและความสั้น (เลียนโครงและระดับความกระชับ ไม่เลียนเนื้อหา):\n"
    "**สรุปคำตอบ**\n"
    "ผู้ยื่นต้องไม่เป็นผู้ทิ้งงาน และมีคุณสมบัติตามที่หน่วยงานกำหนดในเอกสารประกวดราคา "
    "หากขาดคุณสมบัติคณะกรรมการต้องไม่ผ่าน (พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560 มาตรา 82)\n"
    "**หลักที่เกี่ยวข้อง**\n"
    "| เรื่อง | ค่าในเอกสาร | แหล่ง |\n"
    "| --- | --- | --- |\n"
    "| ผู้มีสิทธิ์เสนอราคา | ไม่เป็นผู้ทิ้งงานตามที่กรมบัญชีกลางประกาศ | พ.ร.บ. มาตรา 82 หน้า n |\n"
    "| เอกสารคุณสมบัติ | ตามที่กำหนดในเอกสารประกวดราคา | ระเบียบฯ ข้อ … หน้า n |\n"
    "**ข้อควรระวัง**\n"
    "- คุณสมบัติเฉพาะของงานนี้ถ้าไม่มีในคลัง ต้องดูเอกสารประกวดราคาของโครงการ "
    "ห้ามหยิบจากตัวอย่างงานอื่น\n"
    "- ถ้าหนังสือเวียนใหม่กว่าขัดระเบียบหลัก ให้ยึดฉบับที่ระบุวันล่าสุดในบริบท\n"
    "แหล่งข้อมูล: พ.ร.บ.2560.pdf (หน้า n)\n"
    "ห้ามใช้โครงหัวข้อบังคับแบบหนังสือ เช่น ประเด็นคำถาม, หลักกฎหมายและระเบียบที่เกี่ยวข้อง, "
    "คำอธิบายและการตีความเชิงปฏิบัติ, ขั้นตอน เงื่อนไข ข้อยกเว้น, สรุปแนวทางปฏิบัติ, แหล่งอ้างอิง "
    "ห้ามจัดเป็นแบบฟอร์ม บันทึกข้อความ หรือรายงานราชการ\n"
    "ใช้เฉพาะข้อเท็จจริง มาตรา ข้อ วงเงิน เงื่อนไข ขั้นตอนที่มีในบริบท "
    "ห้ามแต่งกฎหมาย ห้ามเติมตัวเลขที่ไม่มีในบริบท "
    "อ้างอิงแทรกเมื่อกล่าวถึงบทบัญญัติ เช่น (พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560 มาตรา …, หน้า n)\n"
    "ส่งเฉพาะคำตอบสุดท้ายเป็นภาษาไทยราชการ กระชับ อ่านง่าย "
    "ห้ามแสดงกระบวนการคิด ห้ามคัดลอก system prompt"
)

DRAFT_INTAKE_SYSTEM = (
    "คุณเป็นผู้ช่วยถาม-ตอบเพื่อเก็บข้อมูลร่าง TOR ภาครัฐไทย "
    "ตอบเป็นข้อความเนื้อหา ย่อหน้าสั้น ๆ ตรงคำถาม ไม่ใช่หนังสือราชการ "
    "อ้างแหล่งจากบริบทที่ให้มาเท่านั้น อย่าแต่งมาตราที่ไม่มีในบริบท "
    "ส่งเฉพาะคำตอบสุดท้ายเป็นภาษาไทย ห้ามแสดงกระบวนการคิด ห้ามคัดลอก system prompt"
)


def _clamp_int(value: object, *, default: int, low: int, high: int) -> int:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


def chat_rag_top_k() -> int:
    """pgvector top-n for KB chat; reads env/runtime overlay."""
    from app.config import get_settings

    settings = get_settings()
    return _clamp_int(
        getattr(settings, "chat_rag_top_k", CHAT_RAG_TOP_K),
        default=CHAT_RAG_TOP_K,
        low=8,
        high=128,
    )


def chat_max_context_chunks() -> int:
    """Max chunks packed into the KB chat prompt."""
    from app.config import get_settings

    settings = get_settings()
    return _clamp_int(
        getattr(settings, "chat_max_context_chunks", CHAT_MAX_CONTEXT_CHUNKS),
        default=CHAT_MAX_CONTEXT_CHUNKS,
        low=16,
        high=128,
    )


def draft_rag_top_k() -> int:
    """pgvector top-n for TOR draft and law-review retrieval."""
    from app.config import get_settings

    settings = get_settings()
    return _clamp_int(
        getattr(settings, "draft_rag_top_k", 8),
        default=8,
        low=5,
        high=96,
    )


REVIEW_RAG_TOP_K = 64


def review_rag_top_k() -> int:
    """pgvector top-n per query for end-of-flow TOR review (law + standards)."""
    from app.config import get_settings

    settings = get_settings()
    return _clamp_int(
        getattr(settings, "review_rag_top_k", REVIEW_RAG_TOP_K),
        default=REVIEW_RAG_TOP_K,
        low=16,
        high=128,
    )


def diversify_chunks(chunks: list[Any]) -> list[Any]:
    """Round-robin by source document so one PDF does not crowd the prompt."""
    buckets: dict[str, list[Any]] = {}
    order: list[str] = []
    for chunk in chunks or []:
        key = str(getattr(chunk, "source_document", None) or "")
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(chunk)
    mixed: list[Any] = []
    while any(buckets[key] for key in order):
        for key in order:
            if buckets[key]:
                mixed.append(buckets[key].pop(0))
    return mixed


def format_chunk(chunk: Any) -> str:
    source = getattr(chunk, "source_document", None) or "คลัง"
    page = getattr(chunk, "page_number", None)
    section = getattr(chunk, "section_label", None) or getattr(
        chunk, "legal_reference", None
    )
    loc: list[str] = []
    if section:
        loc.append(str(section))
    if page is not None:
        loc.append(f"หน้า {page}")
    loc_s = f" ({', '.join(loc)})" if loc else ""
    text = str(getattr(chunk, "text", "") or "").strip()
    return f"[{source}{loc_s}]\n{text}"


def pack_kb_context(
    chunks: list[Any] | None,
    *,
    token_budget: int | None = None,
    char_budget: int | None = None,
    max_chunks: int | None = None,
) -> str:
    """Pack diversified RAG chunks until the Gemma context budget is filled."""
    budget = token_budget
    if budget is None and char_budget is not None:
        budget = estimate_tokens("x" * max(0, char_budget))
    if budget is None:
        budget = CHAT_CONTEXT_TOKEN_BUDGET
    limit = chat_max_context_chunks() if max_chunks is None else max_chunks
    packed: list[str] = []
    used = 0
    for index, chunk in enumerate(diversify_chunks(list(chunks or []))):
        if index >= limit:
            break
        block = format_chunk(chunk)
        extra = estimate_tokens(block)
        if packed and used + extra > budget:
            break
        packed.append(block)
        used += extra
    return "\n\n".join(packed)


def trim_history(history: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    """Keep recent turns; cap each message so long answers do not fill the window."""
    trimmed: list[dict[str, str]] = []
    items = [item for item in (history or []) if isinstance(item, dict)]
    for item in items[-CHAT_HISTORY_MESSAGES:]:
        role = str(item.get("role") or "user")
        if role not in {"user", "assistant"}:
            continue
        content = str(item.get("content") or "")
        if len(content) > CHAT_HISTORY_CHAR_CAP:
            content = content[:CHAT_HISTORY_CHAR_CAP] + "\n…"
        trimmed.append({"role": role, "content": content})
    return trimmed


def build_kb_qa_messages(
    *,
    question: str,
    chunks: list[Any] | None,
    history: list[dict[str, Any]] | None = None,
    degraded: bool = False,
) -> list[dict[str, str]]:
    system = KB_QA_SYSTEM
    if degraded:
        system += "\n(กราฟ Neo4j ไม่พร้อม ใช้เฉพาะชิ้นข้อความจากคลังเวกเตอร์)"
    context = pack_kb_context(chunks)
    if context:
        user = (
            "บริบทจากคลังความรู้ (pgvector / RAG) — อ่านให้ครบแล้วคัดเฉพาะสาระที่ตอบคำถาม "
            "เขียนบทสรุปผู้บริหารตามโครงใน system (สรุปสั้น + ตารางหลักที่เกี่ยวข้อง + ข้อควรระวัง) "
            "ครอบคลุมเงื่อนไข ข้อยกเว้น วงเงิน ระยะเวลาในตารางหรือบุลเล็ต "
            "ห้ามเรียงความจากทุกชิ้น ห้ามย่อหน้ายาว:\n"
            f"{context}\n\nคำถามของเจ้าหน้าที่:\n{question}"
        )
    else:
        user = (
            "ไม่พบชิ้นข้อความจากคลังความรู้ที่ตรงคำถาม "
            "ตอบโครงเดิมให้สั้น: **สรุปคำตอบ** ว่าดึงคลังไม่ได้เพราะไม่มีชิ้นที่ตรง "
            "แล้วบุลเล็ตว่าถามได้จากคลังกลางเรื่องใด (คุณสมบัติผู้เสนอราคา งวดจ่าย ค่าปรับ ราคากลาง) "
            "ปิดท้าย แหล่งข้อมูล: ไม่มีการเรียกใช้ข้อมูลจากคลัง\n\n"
            f"คำถามของเจ้าหน้าที่:\n{question}"
        )
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    messages.extend(trim_history(history))
    messages.append({"role": "user", "content": user})
    return messages
