"""KB Q&A context packing and officer-style prompt."""

from __future__ import annotations

from types import SimpleNamespace

from app.rag.kb_qa import (
    CHAT_MAX_TOKENS,
    CHAT_RAG_TOP_K,
    KB_QA_SYSTEM,
    build_kb_qa_messages,
    diversify_chunks,
    pack_kb_context,
    trim_history,
)


def _chunk(text: str, source: str, *, page: int | None = 1, score: float = 0.9):
    return SimpleNamespace(
        text=text,
        source_document=source,
        page_number=page,
        section_label="ข้อ 1",
        legal_reference=None,
        score=score,
    )


def test_diversify_chunks_round_robins_sources():
    chunks = [
        _chunk("ก1", "พรบ.pdf"),
        _chunk("ก2", "พรบ.pdf"),
        _chunk("ข1", "ระเบียบ.pdf"),
    ]
    mixed = diversify_chunks(chunks)
    assert [item.source_document for item in mixed] == [
        "พรบ.pdf",
        "ระเบียบ.pdf",
        "พรบ.pdf",
    ]


def test_pack_kb_context_keeps_multiple_documents_and_stops_at_budget():
    chunks = [
        _chunk("เนื้อหาวงเงินเฉพาะเจาะจง" * 20, "กฎกระทรวง.pdf"),
        _chunk("เนื้อหางวดจ่าย" * 20, "ระเบียบคลัง.pdf"),
        _chunk("เนื้อหาค่าปรับ" * 20, "คู่มือ.pdf"),
    ]
    packed = pack_kb_context(chunks, char_budget=80_000)
    assert "กฎกระทรวง.pdf" in packed
    assert "ระเบียบคลัง.pdf" in packed
    assert "คู่มือ.pdf" in packed
    tight = pack_kb_context(chunks, char_budget=80)
    assert "กฎกระทรวง.pdf" in tight
    assert tight.count("[") == 1


def test_build_kb_qa_messages_is_officer_memo_and_uses_rag():
    chunks = [_chunk("ห้ามแบ่งซื้อแบ่งจ้าง", "พ.ร.บ.2560.pdf")]
    messages = build_kb_qa_messages(
        question="แบ่งซื้อได้หรือไม่",
        chunks=chunks,
        history=[{"role": "user", "content": "สวัสดี"}],
        degraded=True,
    )
    assert messages[0]["role"] == "system"
    assert "เจ้าหน้าที่พัสดุอาวุโส" in messages[0]["content"]
    assert "หลักกฎหมายและระเบียบที่เกี่ยวข้อง" in messages[0]["content"]
    assert "Neo4j" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "สวัสดี"
    user = messages[-1]["content"]
    assert "พ.ร.บ.2560.pdf" in user
    assert "ห้ามแบ่งซื้อแบ่งจ้าง" in user
    assert "แบ่งซื้อได้หรือไม่" in user
    assert CHAT_RAG_TOP_K >= 24
    assert CHAT_MAX_TOKENS >= 32768
    assert "ห้ามตอบสั้น" in KB_QA_SYSTEM
    assert "6144" in KB_QA_SYSTEM


def test_trim_history_caps_long_officer_answers():
    history = [
        {"role": "user", "content": "ถาม"},
        {"role": "assistant", "content": "ก" * 15000},
        {"role": "system", "content": "ignore"},
    ]
    trimmed = trim_history(history)
    assert len(trimmed) == 2
    assert trimmed[1]["content"].endswith("…")
    assert len(trimmed[1]["content"]) < 13000
