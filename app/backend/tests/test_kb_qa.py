"""KB Q&A context packing and adaptive prompt with web sources."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.rag.kb_qa import (
    CHAT_MAX_TOKENS,
    CHAT_RAG_TOP_K,
    KB_QA_SYSTEM,
    build_kb_qa_messages,
    pin_rate_catalog_chunks,
    question_asks_rate_catalog,
    rate_catalog_instruction,
    chat_context_token_budget,
    chat_rag_fallback_top_n,
    chat_rag_pack_cap_tokens,
    chat_rag_score_threshold,
    chat_rag_top_k,
    diversify_chunks,
    normalize_kb_qa_answer,
    pack_kb_context,
    prepare_kb_qa_messages,
    select_rag_chunks_for_qa,
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


def _web(*, title: str, url: str, snippet: str = "ข้อความสั้น", published: str = "2024-05-01"):
    return SimpleNamespace(title=title, url=url, snippet=snippet, published=published)


def test_select_rag_chunks_threshold_or_fallback_top_n():
    strong = _chunk("แรง", "a.pdf", score=0.8)
    weak = [_chunk(f"อ่อน{i}", f"w{i}.pdf", score=0.05 - i * 0.001) for i in range(8)]
    assert select_rag_chunks_for_qa([strong, weak[0]]) == [strong]
    picked = select_rag_chunks_for_qa(weak)
    assert len(picked) == chat_rag_fallback_top_n()
    assert picked[0].score >= picked[-1].score


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


def test_build_kb_qa_messages_is_adaptive_and_uses_rag():
    chunks = [_chunk("ห้ามแบ่งซื้อแบ่งจ้าง", "พ.ร.บ.2560.pdf")]
    messages = build_kb_qa_messages(
        question="แบ่งซื้อได้หรือไม่",
        chunks=chunks,
        history=[{"role": "user", "content": "สวัสดี"}],
        degraded=True,
        web_sources=[],
    )
    assert messages[0]["role"] == "system"
    assert "ภาษาพัสดุ" in messages[0]["content"]
    assert "ห้ามบังคับหัวข้อตายตัว" in messages[0]["content"]
    assert "ห้ามใช้โครงหัวข้อบังคับ" in messages[0]["content"]
    assert "ประเด็นคำถาม" in messages[0]["content"]
    assert "หัวข้อบังคับต้องตรงอักษร" not in messages[0]["content"]
    assert "**สรุปคำตอบ**" not in messages[0]["content"]
    assert "**หลักที่เกี่ยวข้อง**" not in messages[0]["content"]
    assert "**ข้อควรระวัง**" not in messages[0]["content"]
    assert "ตอบให้ครบถ้วนตามเอกสาร" in messages[0]["content"]
    assert "Neo4j" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "สวัสดี"
    user = messages[-1]["content"]
    assert "พ.ร.บ.2560.pdf" in user
    assert "ห้ามแบ่งซื้อแบ่งจ้าง" in user
    assert "แบ่งซื้อได้หรือไม่" in user
    assert "ครอบคลุม" in user
    assert "แหล่งออนไลน์ที่ค้นได้: 0 แหล่ง" in user
    assert "หัวข้อบังคับ" not in user
    # Catalog defaults only; live values come from Settings/env.
    assert CHAT_RAG_TOP_K == 48
    assert 3 <= chat_rag_top_k() <= 128
    assert CHAT_MAX_TOKENS == 32_768
    assert chat_rag_score_threshold() == 0.25
    assert chat_rag_fallback_top_n() == 5
    assert chat_rag_pack_cap_tokens() == 80_000
    assert chat_context_token_budget() <= chat_rag_pack_cap_tokens()
    assert "ตอบให้ครบถ้วนตามเอกสาร" in KB_QA_SYSTEM
    assert "ถักทอสาระ" in KB_QA_SYSTEM
    assert "6144" not in KB_QA_SYSTEM
    assert "ห้ามบังคับหัวข้อตายตัว" in KB_QA_SYSTEM


def test_normalize_kb_qa_answer_does_not_force_headings():
    raw = "**สรุปตอบ**\nข้อความ\n**หลักที่เกี่ยวข้อง**\n| a | b | c |"
    assert normalize_kb_qa_answer(raw) == raw
    already = "วิธีเฉพาะเจาะจงใช้ได้เมื่อวงเงินไม่เกินตามระเบียบ"
    assert normalize_kb_qa_answer(already) == already
    assert normalize_kb_qa_answer("") == ""


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


@pytest.mark.asyncio
async def test_prepare_kb_qa_messages_includes_rag_and_web_sources():
    chunks = [_chunk("ห้ามแบ่งซื้อแบ่งจ้าง", "พ.ร.บ.2560.pdf", page=12)]
    web = [
        _web(
            title="หนังสือเวียนกรมบัญชีกลาง",
            url="https://cgd.go.th/a",
            snippet="ห้ามแบ่งซื้อแบ่งจ้างเพื่อเลี่ยงวิธีประกวดราคา",
        ),
        _web(title="ระเบียบพัสดุ", url="https://www.gprocurement.go.th/b"),
        _web(title="คู่มือวิธีจัดซื้อ", url="https://www.cgd.go.th/c"),
        _web(title="มาตรา 55", url="https://www.ratchakitcha.soc.go.th/d"),
        _web(title="แนวปฏิบัติวงเงิน", url="https://www.cgd.go.th/e"),
        _web(title="ซ้ำ", url="https://cgd.go.th/a"),
    ]
    with patch("app.rag.kb_qa.search_web", new=AsyncMock(return_value=web)) as mocked:
        messages = await prepare_kb_qa_messages(
            question="แบ่งซื้อได้หรือไม่",
            chunks=chunks,
        )
        mocked.assert_awaited()
    system = messages[0]["content"]
    user = messages[-1]["content"]
    assert "ห้ามบังคับหัวข้อตายตัว" in system
    assert "**สรุปคำตอบ**" not in system
    assert "**หลักที่เกี่ยวข้อง**" not in system
    assert "**ข้อควรระวัง**" not in system
    assert "พ.ร.บ.2560.pdf" in user
    assert "ห้ามแบ่งซื้อแบ่งจ้าง" in user
    assert "หนังสือเวียนกรมบัญชีกลาง" in user
    assert "https://cgd.go.th/a" in user
    assert "แหล่งออนไลน์ที่ค้นได้: 5 แหล่ง" in user
    assert "หัวข้อบังคับ" not in user


@pytest.mark.asyncio
async def test_prepare_kb_qa_messages_states_actual_web_count_when_below_five():
    chunks = [_chunk("วางหลักประกันสัญญาก่อนจ่ายงวด", "ระเบียบพัสดุ.pdf", page=8)]
    web = [
        _web(title="กรมบัญชีกลาง", url="https://www.cgd.go.th/one"),
        _web(title="ประกาศเพิ่มเติม", url="https://www.cgd.go.th/two"),
    ]
    with patch("app.rag.kb_qa.search_web", new=AsyncMock(return_value=web)):
        messages = await prepare_kb_qa_messages(
            question="ต้องวางหลักประกันเมื่อใด",
            chunks=chunks,
        )
    user = messages[-1]["content"]
    assert "ระเบียบพัสดุ.pdf" in user
    assert "แหล่งออนไลน์ที่ค้นได้: 2 แหล่ง" in user
    assert "น้อยกว่า 5 แหล่ง" in user
    assert "https://www.cgd.go.th/one" in user
    assert "**สรุปคำตอบ**" not in messages[0]["content"]


@pytest.mark.asyncio
async def test_load_rate_catalog_chunks_prefers_graduate_rows(monkeypatch):
    from app.rag.hybrid import load_rate_catalog_chunks
    from app.rag import hybrid as hybrid_mod

    row = (
        "id-1",
        "30,090 ค่าอาหาร สถานที่เอกชน",
        18,
        "ตาราง",
        "อัตราค่าจ้างที่ปรึกษา ประชาสัมพันธ์ อบรม .pdf",
    )

    class _Result:
        def all(self):
            return [row]

    class _Session:
        async def execute(self, *_args, **_kwargs):
            return _Result()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(hybrid_mod.runtime, "session_factory", lambda: _Session())
    chunks = await load_rate_catalog_chunks(limit=1)
    assert chunks[0].source_document.startswith("อัตราค่าจ้างที่ปรึกษา")
    assert chunks[0].page_number == 18
    assert chunks[0].score == 0.99
    monkeypatch.setattr(hybrid_mod.runtime, "session_factory", None)
    assert await load_rate_catalog_chunks() == []


def test_rate_question_pins_the_rate_pdf_ahead_of_other_guidelines():
    question = "อัตราค่าจ้างที่ปรึกษาภาคเอกชน ปริญญาโท อายุงาน 2 ปี ใช้แถวใด"
    assert question_asks_rate_catalog(question) is True
    assert question_asks_rate_catalog("หนังสือ ว126 เหตุบอกเลิกสัญญา") is False
    catalog = _chunk("30,090 บาท", "อัตราค่าจ้างที่ปรึกษา ประชาสัมพันธ์ อบรม .pdf", score=0.99)
    catalog.id = "rate-1"
    other = _chunk("เริ่มที่ 5 ปี", "กวจ_ว1203_แนวทางการจ้างที่ปรึกษา.pdf", score=0.8)
    other.id = "other-1"
    pinned = pin_rate_catalog_chunks([other], [catalog])
    assert pinned[0].source_document.startswith("อัตราค่าจ้างที่ปรึกษา")
    assert rate_catalog_instruction(pinned)
    messages = build_kb_qa_messages(question=question, chunks=pinned, web_sources=[])
    body = messages[-1]["content"]
    assert "อัตราค่าจ้างที่ปรึกษา" in body
    assert "30,090" in body
