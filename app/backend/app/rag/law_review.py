"""Multi-query law + standards RAG for TOR review (deep end-of-flow check)."""

from __future__ import annotations

from app.llm_tokens import REVIEW_LEGAL_CONTEXT_CHARS
from app.rag.hybrid import hybrid_retrieve, unpack_hybrid
from app.rag.kb_qa import review_rag_top_k
from app.rag.retrieval import RetrievedChunk

# Core procurement law / procedure queries.
LAW_REVIEW_QUERIES: tuple[str, ...] = (
    "พระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560 ระเบียบกระทรวงการคลัง",
    "วิธีประกาศเชิญชวนทั่วไป วิธีคัดเลือก วิธีเฉพาะเจาะจง วงเงิน",
    "ราคากลาง หลักเกณฑ์การคำนวณราคา ประกาศราคากลาง",
    "อัตราค่าปรับร้อยละต่อวัน การรับประกันผลงาน หลักประกันสัญญา",
    "คุณสมบัติผู้เสนอราคา ทุนจดทะเบียน มูลค่าสุทธิกิจการ e-GP ผู้ทิ้งงาน",
    "หลักเกณฑ์การพิจารณาคัดเลือกข้อเสนอ เกณฑ์ราคา เกณฑ์คุณภาพ",
    "ขอบเขตของงาน TOR ข้อกำหนดคุณลักษณะเฉพาะ การจัดทำเอกสารประกวดราคา",
    "การตรวจรับพัสดุ คณะกรรมการตรวจรับ การส่งมอบงาน",
    "สัญญาจ้าง สัญญาซื้อขาย เงื่อนไขสัญญาแบบมาตรฐาน",
)

# Technical / ICT / privacy standards commonly needed in TOR review.
STANDARDS_REVIEW_QUERIES: tuple[str, ...] = (
    "เกณฑ์กลางครุภัณฑ์คอมพิวเตอร์ เกณฑ์กลาง ICT ตารางคุณลักษณะ",
    "มาตรฐานเว็บไซต์ภาครัฐ WCAG การเข้าถึงได้",
    "ISO/IEC 27001 ความมั่นคงปลอดภัยสารสนเทศ นโยบายความปลอดภัย",
    "OWASP Top 10 การทดสอบช่องโหว่ ตรวจสอบความมั่นคงปลอดภัย",
    "พระราชบัญญัติคุ้มครองข้อมูลส่วนบุคคล PDPA ข้อมูลส่วนบุคคล",
    "มาตรฐานการเชื่อมโยงระบบราชการ API ข้อมูลเปิดภาครัฐ",
    "แผนทดสอบระบบ UAT เกณฑ์การยอมรับ การตรวจรับระบบสารสนเทศ",
    "การสำรองข้อมูล กู้คืนระบบ BCP DR Disaster Recovery",
    "ลิขสิทธิ์ซอฟต์แวร์ ครุภัณฑ์คอมพิวเตอร์ จำนวนสิทธิ์ใช้งาน",
    "มาตรฐานการพัฒนาซอฟต์แวร์ภาครัฐ การส่งมอบซอร์สโค้ด เอกสารระบบ",
)

TYPE_EXTRA_QUERIES: dict[str, tuple[str, ...]] = {
    "hire_develop": (
        "จ้างพัฒนาระบบสารสนเทศ ข้อกำหนดหน้าที่การทำงาน การเชื่อมโยงระบบ",
        "การทดสอบหน่วย บูรณาการ ประสิทธิภาพ ความมั่นคงปลอดภัย UAT",
        "บุคลากรประจำโครงการ man-day ระดับการให้บริการ SLA รับประกัน",
    ),
    "hire_maintain": (
        "จ้างบำรุงรักษาระบบ PM CM SLA เวลาตอบสนอง เวลาแก้ไข",
        "อะไหล่ ศูนย์รับแจ้งเหตุ สำรองข้อมูล กู้คืนระบบ",
    ),
    "buy_goods": (
        "จัดซื้อครุภัณฑ์ คุณลักษณะเฉพาะ การติดตั้ง การรับประกัน",
        "เกณฑ์กลางครุภัณฑ์ การตรวจรับ การฝึกอบรม",
    ),
    "lease_service": (
        "เช่าใช้บริการ ความพร้อมใช้งาน เส้นทางสำรอง ศูนย์ NOC",
        "รายงานปริมาณการใช้งาน การบำรุงรักษาตลอดอายุสัญญาเช่า",
    ),
    "hire_service": (
        "จ้างบริการ ปริมาณงาน มาตรฐานคุณภาพ การรายงานความคืบหน้า",
    ),
    "hire_consult": (
        "จ้างที่ปรึกษา ระเบียบวิธี รายงานขั้น ขนาดตัวอย่าง",
    ),
    "construction": (
        "งานก่อสร้าง แบบรูปรายการ มาตรฐานวัสดุ ความปลอดภัยในการทำงาน",
    ),
}

MAX_LAW_CHUNKS = 120
CHUNK_TEXT_CAP = 4_500


def _chunk_key(chunk: RetrievedChunk) -> str:
    return str(getattr(chunk, "id", "") or "") or str(getattr(chunk, "text", "") or "")[:80]


def _queries_for(project_type: str | None = None) -> tuple[str, ...]:
    queries = list(LAW_REVIEW_QUERIES) + list(STANDARDS_REVIEW_QUERIES)
    key = (project_type or "").strip()
    if key in TYPE_EXTRA_QUERIES:
        queries.extend(TYPE_EXTRA_QUERIES[key])
    # Preserve order while dropping exact duplicates.
    seen: set[str] = set()
    out: list[str] = []
    for query in queries:
        if query in seen:
            continue
        seen.add(query)
        out.append(query)
    return tuple(out)


async def collect_law_review_chunks(
    project_type: str | None = None,
) -> list[RetrievedChunk]:
    """Retrieve diversified law/regulation/standards chunks across many queries."""
    top_k = review_rag_top_k()
    per_query = max(12, min(24, top_k // 2))
    seen: set[str] = set()
    out: list[RetrievedChunk] = []
    for query in _queries_for(project_type):
        try:
            result, _, _, _ = unpack_hybrid(
                await hybrid_retrieve(
                    query,
                    search_scope="global",
                    top_k=per_query,
                )
            )
        except Exception:
            continue
        for chunk in result.chunks:
            key = _chunk_key(chunk)
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(chunk)
            if len(out) >= MAX_LAW_CHUNKS:
                return out
    return out


def format_law_chunks(
    chunks: list[RetrievedChunk],
    *,
    char_cap: int = REVIEW_LEGAL_CONTEXT_CHARS,
) -> str:
    parts: list[str] = []
    used = 0
    limit = max(8_000, int(char_cap or REVIEW_LEGAL_CONTEXT_CHARS))
    for chunk in chunks:
        source = getattr(chunk, "source_document", None) or "คลัง"
        page = getattr(chunk, "page_number", None)
        loc = f" หน้า {page}" if page is not None else ""
        text = str(getattr(chunk, "text", "") or "")[:CHUNK_TEXT_CAP]
        if not text:
            continue
        block = f"[{source}{loc}]\n{text}"
        if used + len(block) + 2 > limit and parts:
            break
        parts.append(block)
        used += len(block) + 2
    return "\n\n".join(parts)


async def law_review_context(project_type: str | None = None) -> str:
    """Packed global พ.ร.บ./ระเบียบ/มาตรฐาน excerpts for ReviewAgent."""
    chunks = await collect_law_review_chunks(project_type)
    return format_law_chunks(chunks)
