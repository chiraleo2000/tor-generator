"""Integration tests for agent graph, cache, RAG degradation, and KB ACL."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.slots import FACT_REQUIRED_SLOTS
from app.services.agent_workflow import (
    default_state,
    run_answer,
    run_confirm,
    run_review,
    run_start,
)
from app.services.full_draft_generator import FullDraftGenerator
from app.services.intake_service import empty_slot_map
from app.services.kb_chat_service import KnowledgeChatService
from app.services.session_cache import SessionCacheService, extraction_key

PROJECT_ID = uuid.UUID("abcdefab-abcd-abcd-abcd-abcdefabcdef")
USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
SESSION_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


def _filled_map():
    slot_map = empty_slot_map()
    for key in FACT_REQUIRED_SLOTS:
        slot_map[key] = {
            "content": "ข้อมูลโครงการ",
            "status": "filled",
            "sources": ["user"],
        }
    return slot_map


class FakeLLM:
    def __init__(self, content: str):
        self.content = content

    async def invoke(self, _messages, **_kwargs):
        return SimpleNamespace(content=self.content)


def _patch_workflow():
    mapped = MagicMock(slot_map=_filled_map(), error=None, partial=False)
    updated = MagicMock(slot_map=_filled_map(), affected=["s6"], error=None)
    draft_patch = {
        "phase": "validating",
        "section_drafts": {"s1": "ร่าง"},
        "draft_quality_scores": {"s1": 80},
        "overall_quality_score": 80,
        "sections_pending": [],
        "warnings": [],
    }
    validate_patch = {
        "phase": "human_review",
        "validation_findings": [],
        "section_drafts": {"s1": "ร่าง"},
        "overall_quality_score": 80,
        "mandatory_review_sections": ["s3"],
    }
    return (
        patch(
            "app.orchestrator.agent_nodes.SectionMapper.map_content",
            new=AsyncMock(return_value=mapped),
        ),
        patch(
            "app.orchestrator.agent_nodes.SectionMapper.incremental_update",
            new=AsyncMock(return_value=updated),
        ),
        patch(
            "app.orchestrator.agent_nodes.GapDetector.generate_questions",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.services.agent_workflow.draft_all_node",
            new=AsyncMock(return_value=draft_patch),
        ),
        patch(
            "app.services.agent_workflow.validate_draft_node",
            new=AsyncMock(return_value=validate_patch),
        ),
        patch(
            "app.orchestrator.agent_nodes.SessionCacheService.set_slot_map",
            new=AsyncMock(),
        ),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graph_state_transitions_mocked_llm():
    state = default_state(SESSION_ID, PROJECT_ID, USER_ID, {"name": "ทดสอบ"})
    state["intake_texts"] = [{"name": "t.txt", "text": "ก" * 80}]
    patches = _patch_workflow()
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:
        started = await run_start(state)
        assert started["phase"] in {"confirming", "gap_filling"}
        answered = await run_answer(started, "งบ 5 ล้านบาท ระยะเวลา 180 วัน")
        assert "slot_map" in answered
        confirmed = await run_confirm({**answered, "slot_map": _filled_map()}, True)
        assert confirmed["phase"] in {"human_review", "validating", "drafting"}
        with patch(
            "app.services.agent_export.persist_and_export",
            new=AsyncMock(return_value={"docx": "https://x/a.docx", "pdf": "https://x/a.pdf"}),
        ):
            exported = await run_review(
                confirmed, True, None, ["s3", "s6", "s8", "s10", "s13"]
            )
        assert exported["phase"] == "complete"
        assert exported["export_docx_url"] == "https://x/a.docx"
        assert exported["export_pdf_url"] == "https://x/a.pdf"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_cache_hit_miss_and_write_failure():
    stored: dict[str, str] = {}
    ttls: dict[str, int | None] = {}

    class Redis:
        async def get(self, key):
            if ttls.get(key) == 0:
                return None
            return stored.get(key)

        async def set(self, key, value, ex=None):
            stored[key] = value
            ttls[key] = ex

        async def delete(self, *keys):
            for key in keys:
                stored.pop(key, None)
                ttls.pop(key, None)

    cache = SessionCacheService(redis=Redis())
    assert await cache.get_extraction(PROJECT_ID, "abc") is None
    await cache.set_extraction(PROJECT_ID, "abc", {"text": "cached"})
    hit = await cache.get_extraction(PROJECT_ID, "abc")
    assert hit["text"] == "cached"
    assert ttls[extraction_key(PROJECT_ID, "abc")] == 24 * 3600

    key = extraction_key(PROJECT_ID, "abc")
    ttls[key] = 0
    stored.pop(key, None)
    assert await cache.get_extraction(PROJECT_ID, "abc") is None

    broken = MagicMock()
    broken.set = AsyncMock(side_effect=OSError("fail"))
    broken.get = AsyncMock(return_value=None)
    await SessionCacheService(redis=broken).set_slot_map(PROJECT_ID, {})


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_degradation_still_drafts():
    async def empty_retrieve(*_args, **_kwargs):
        return SimpleNamespace(chunks=[]), [], False

    async def error_retrieve(*_args, **_kwargs):
        raise ConnectionError("neo4j down")

    llm = FakeLLM("ร่างส่วนความเป็นมาของโครงการทดสอบ")
    agent = MagicMock()
    agent.draft = AsyncMock(return_value="ร่างส่วนความเป็นมาของโครงการทดสอบ")
    with patch(
        "app.services.full_draft_generator.get_agent_for_section",
        return_value=agent,
    ):
        gen = FullDraftGenerator(llm=llm, retrieve=empty_retrieve)
        empty_result = await gen.generate_all(
            _filled_map(), {"name": "t"}, project_id=str(PROJECT_ID)
        )
        assert empty_result.warnings
        gen_err = FullDraftGenerator(llm=llm, retrieve=error_retrieve)
        err_result = await gen_err.generate_all(_filled_map(), {"name": "t"})
        has_warning = bool(err_result.warnings) or bool(err_result.section_drafts)
        assert has_warning


@pytest.mark.asyncio
async def test_generate_all_uses_cached_section_draft():
    cache = MagicMock()
    cache.get_draft = AsyncMock(return_value="ร่างจากแคชที่ยาวพอ")
    cache.set_draft = AsyncMock()
    gen = FullDraftGenerator(llm=MagicMock(), cache=cache, retrieve=AsyncMock())
    result = await gen.generate_all(_filled_map(), project_id=str(PROJECT_ID))
    assert result.section_drafts["s1"] == "ร่างจากแคชที่ยาวพอ"
    assert result.draft_quality_scores["s1"] == 70.0
    cache.set_draft.assert_not_awaited()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_kb_chat_acl_and_threshold():
    user_id = USER_ID
    other = uuid.uuid4()
    seen = {}

    async def retrieve(query, **kwargs):
        del query
        seen["user_id"] = kwargs.get("user_id")
        seen["scope"] = kwargs.get("search_scope")
        return SimpleNamespace(chunks=[]), [], False

    with patch("app.services.kb_chat_service.hybrid_retrieve", new=retrieve):
        service = KnowledgeChatService(llm=FakeLLM("ไม่ควรถูกเรียก"))
        response = await service.answer(SESSION_ID, user_id, "ถาม", [])
        assert response.no_results is True
        assert seen["scope"] == "both"
        assert seen["user_id"] == user_id

    async def retrieve_low(query, **kwargs):
        del query, kwargs
        chunk = SimpleNamespace(
            text="กฎหมาย",
            score=0.1,
            source_document="x",
            page_number=1,
            section_label="s1",
            metadata={},
        )
        return SimpleNamespace(chunks=[chunk]), [], False

    with patch("app.services.kb_chat_service.hybrid_retrieve", new=retrieve_low):
        low = await KnowledgeChatService(llm=FakeLLM("ใช้ชิ้นคะแนนต่ำ")).answer(
            SESSION_ID, user_id, "ถาม", []
        )
        assert low.no_results is False
        assert "คะแนนต่ำ" in low.answer

    async def retrieve_hit(query, **kwargs):
        del query, kwargs
        chunk = SimpleNamespace(
            text="วิธีเฉพาะเจาะจงใช้วงเงินไม่เกินห้าแสนบาท",
            score=0.4,
            source_document="กฎกระทรวงวงเงิน.pdf",
            page_number=1,
            section_label="s6",
            metadata={"document_name": "กฎกระทรวงวงเงิน.pdf"},
        )
        return SimpleNamespace(chunks=[chunk]), [], False

    with patch("app.services.kb_chat_service.hybrid_retrieve", new=retrieve_hit):
        hit = await KnowledgeChatService(llm=FakeLLM("วงเงินไม่เกินห้าแสนบาท")).answer(
            SESSION_ID, user_id, "วงเงินเท่าใด", []
        )
        assert hit.no_results is False
        assert "ห้าแสน" in hit.answer
        assert hit.citations[0]["document"] == "กฎกระทรวงวงเงิน.pdf"

    other_row = MagicMock()
    other_row.user_id = other
    other_row.last_active_at = datetime.now(timezone.utc)
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = other_row
    db.execute = AsyncMock(return_value=result)
    denied = await KnowledgeChatService().load_session(db, SESSION_ID, user_id)
    assert denied is None
