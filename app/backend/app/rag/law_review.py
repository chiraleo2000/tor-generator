"""Multi-query law RAG for TOR review (not a single generic พ.ร.บ. sentence)."""

from __future__ import annotations

from app.rag.hybrid import hybrid_retrieve, unpack_hybrid
from app.rag.kb_qa import draft_rag_top_k
from app.rag.retrieval import RetrievedChunk

LAW_REVIEW_QUERIES: tuple[str, ...] = (
    "พระราชบัญญัติการจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560 ระเบียบกระทรวงการคลัง",
    "วิธีประกาศเชิญชวนทั่วไป วิธีคัดเลือก วิธีเฉพาะเจาะจง วงเงิน",
    "ราคากลาง หลักเกณฑ์การคำนวณราคา ประกาศราคากลาง",
    "อัตราค่าปรับร้อยละต่อวัน การรับประกันผลงาน",
    "คุณสมบัติผู้เสนอราคา ทุนจดทะเบียน มูลค่าสุทธิกิจการ e-GP ผู้ทิ้งงาน",
    "หลักเกณฑ์การพิจารณาคัดเลือกข้อเสนอ เกณฑ์ราคา เกณฑ์คุณภาพ",
)

MAX_LAW_CHUNKS = 48
CHUNK_TEXT_CAP = 2000


def _chunk_key(chunk: RetrievedChunk) -> str:
    return str(getattr(chunk, "id", "") or "") or str(getattr(chunk, "text", "") or "")[:80]


async def collect_law_review_chunks() -> list[RetrievedChunk]:
    """Retrieve diversified law/regulation chunks across several queries."""
    per_query = max(8, min(16, draft_rag_top_k() // 2))
    seen: set[str] = set()
    out: list[RetrievedChunk] = []
    for query in LAW_REVIEW_QUERIES:
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


def format_law_chunks(chunks: list[RetrievedChunk]) -> str:
    parts: list[str] = []
    for chunk in chunks:
        source = getattr(chunk, "source_document", None) or "คลัง"
        page = getattr(chunk, "page_number", None)
        loc = f" หน้า {page}" if page is not None else ""
        text = str(getattr(chunk, "text", "") or "")[:CHUNK_TEXT_CAP]
        if text:
            parts.append(f"[{source}{loc}]\n{text}")
    return "\n\n".join(parts)


async def law_review_context() -> str:
    """Packed global พ.ร.บ./ระเบียบ excerpts for ReviewAgent and legal_basis."""
    chunks = await collect_law_review_chunks()
    return format_law_chunks(chunks)
