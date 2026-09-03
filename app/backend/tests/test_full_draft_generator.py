"""Unit tests for FullDraftGenerator helpers and RAG unpack."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.retrieval import RetrievalResult, RetrievedChunk
from app.domain.slots import FACT_REQUIRED_SLOTS
from app.services.full_draft_generator import (
    RAG_TOP_K,
    DraftResult,
    FullDraftGenerator,
    _warn_missing_facts,
    mean_quality,
    slot_user_input,
)


def test_mean_quality_empty_and_clamp() -> None:
    assert mean_quality({}) == 0.0
    assert mean_quality({"s1": 150, "s2": -10}) == 50.0


def test_slot_user_input_s4_subsections() -> None:
    payload = slot_user_input(
        {
            "s4": {"content": "ขอบเขต", "sources": ["a"]},
            "s4.1": {"content": "ย่อย"},
        },
        "s4",
    )
    assert payload["content"] == "ขอบเขต"
    assert payload["scope_subsections"]["s4.1"] == "ย่อย"


def test_warn_missing_facts_appends() -> None:
    result = DraftResult()
    _warn_missing_facts({}, result)
    assert result.warnings


@pytest.mark.asyncio
async def test_generator_uses_cache_and_mcp_unpack() -> None:
    cache = MagicMock()
    cache.get_draft = AsyncMock(return_value="ร่างจากแคช")
    cache.set_draft = AsyncMock()

    async def fake_retrieve(*_args, **_kwargs):
        chunk = RetrievedChunk(id="1", text="ก", score=0.9, source_document="ด")
        return RetrievalResult(chunks=[chunk], query="q", top_k=1, actual_count=1), [], False, True

    gen = FullDraftGenerator(llm=MagicMock(), cache=cache, retrieve=fake_retrieve)
    with patch(
        "app.services.full_draft_generator.TOR_SECTION_ORDER",
        ["s1"],
    ):
        result = await gen.generate_all({}, project_id="p1", user_id="u1")
    assert result.section_drafts["s1"] == "ร่างจากแคช"
    assert result.draft_quality_scores["s1"] == 70.0


@pytest.mark.asyncio
async def test_generator_rag_filters_low_score() -> None:
    async def fake_retrieve(*_args, **_kwargs):
        low = RetrievedChunk(id="1", text="ต่ำ", score=0.1)
        high = RetrievedChunk(id="2", text="สูง", score=0.9, source_document="ด")
        return RetrievalResult(chunks=[low, high], query="q", top_k=2, actual_count=2), [], True, False

    gen = FullDraftGenerator(llm=object(), retrieve=fake_retrieve)
    chunks, warning = await gen._rag("s1", "u1")
    assert [item["id"] for item in chunks] == ["2"]
    assert warning == "GraphRAG ลดระดับเหลือ pgvector"


@pytest.mark.asyncio
async def test_generator_rag_failure_returns_warning() -> None:
    async def boom(*_args, **_kwargs):
        raise RuntimeError("down")

    gen = FullDraftGenerator(retrieve=boom)
    chunks, warning = await gen._rag("s1", None)
    assert chunks == []
    assert warning is not None


def test_auto_correct_stops_at_max() -> None:
    gen = FullDraftGenerator()
    import inspect

    assert inspect.iscoroutinefunction(gen.auto_correct)


@pytest.mark.asyncio
async def test_auto_correct_returns_original_when_attempts_exhausted() -> None:
    gen = FullDraftGenerator()
    assert await gen.auto_correct("s1", "เดิม", [], {}, 3) == "เดิม"


@pytest.mark.asyncio
async def test_generator_drafts_when_cache_empty() -> None:
    cache = MagicMock()
    cache.get_draft = AsyncMock(return_value=None)
    cache.set_draft = AsyncMock()
    agent = MagicMock()
    agent.draft = AsyncMock(return_value="ก" * 50)

    async def fake_retrieve(*_args, **_kwargs):
        chunk = RetrievedChunk(id="1", text="ก", score=0.9, source_document="ด")
        return RetrievalResult(chunks=[chunk], query="q", top_k=1, actual_count=1), [], False, False

    gen = FullDraftGenerator(llm=MagicMock(), cache=cache, retrieve=fake_retrieve)
    with (
        patch("app.services.full_draft_generator.TOR_SECTION_ORDER", ["s1"]),
        patch("app.services.full_draft_generator.get_agent_for_section", return_value=agent),
    ):
        result = await gen.generate_all({"s1": {"content": "มี", "status": "filled"}}, project_id="p1")
    assert "ก" in result.section_drafts["s1"]
    cache.set_draft.assert_awaited()


@pytest.mark.asyncio
async def test_generator_marks_pending_when_agent_missing() -> None:
    cache = MagicMock()
    cache.get_draft = AsyncMock(return_value=None)
    cache.set_draft = AsyncMock()

    async def fake_retrieve(*_args, **_kwargs):
        return RetrievalResult(chunks=[], query="q", top_k=1, actual_count=0), [], False, False

    gen = FullDraftGenerator(llm=MagicMock(), cache=cache, retrieve=fake_retrieve)
    with (
        patch("app.services.full_draft_generator.TOR_SECTION_ORDER", ["s1"]),
        patch("app.services.full_draft_generator.get_agent_for_section", return_value=None),
    ):
        result = await gen.generate_all({}, project_id="p1")
    assert "s1" in result.sections_pending


@pytest.mark.asyncio
async def test_generator_handles_draft_exception() -> None:
    cache = MagicMock()
    cache.get_draft = AsyncMock(return_value=None)
    agent = MagicMock()
    agent.draft = AsyncMock(side_effect=RuntimeError("llm down"))

    async def fake_retrieve(*_args, **_kwargs):
        chunk = RetrievedChunk(id="1", text="ก", score=0.9)
        return RetrievalResult(chunks=[chunk], query="q", top_k=1, actual_count=1), [], False, False

    gen = FullDraftGenerator(llm=MagicMock(), cache=cache, retrieve=fake_retrieve)
    with (
        patch("app.services.full_draft_generator.TOR_SECTION_ORDER", ["s1"]),
        patch("app.services.full_draft_generator.get_agent_for_section", return_value=agent),
    ):
        result = await gen.generate_all({})
    assert "s1" in result.sections_pending
    assert any("ไม่สำเร็จ" in item for item in result.warnings)


@pytest.mark.asyncio
async def test_auto_correct_redrafts() -> None:
    agent = MagicMock()
    agent.draft = AsyncMock(return_value="แก้แล้ว" * 10)

    async def fake_retrieve(*_args, **_kwargs):
        chunk = RetrievedChunk(id="1", text="ก", score=0.9)
        return RetrievalResult(chunks=[chunk], query="q", top_k=1, actual_count=1), [], False, False

    gen = FullDraftGenerator(llm=MagicMock(), retrieve=fake_retrieve)
    with patch("app.services.full_draft_generator.get_agent_for_section", return_value=agent):
        text = await gen.auto_correct(
            "s1",
            "เดิม",
            [{"message": "สั้นไป", "affected_section": "s1"}],
            {},
            0,
        )
    assert "แก้แล้ว" in text


def test_validate_document_passes_budget() -> None:
    engine = MagicMock()
    engine.validate.return_value = SimpleNamespace(findings=[], quality_score=80)
    gen = FullDraftGenerator()
    with patch("app.services.full_draft_generator._create_rule_engine", return_value=engine):
        result = gen.validate_document({"s1": "ร่าง"}, {"budget": 1, "project_type": "it"})
    assert result.quality_score == 80
    document = engine.validate.call_args.args[0]
    assert document["budget"] == 1
    assert document["project_type"] == "it"


def test_mean_quality_average() -> None:
    assert mean_quality({"s1": 40, "s2": 80}) == 60.0


def test_slot_user_input_plain_and_non_dict() -> None:
    assert slot_user_input("nope", "s1") == {}
    payload = slot_user_input({"s1": {"content": "ความเป็นมา", "sources": ["ผู้ใช้"]}}, "s1")
    assert payload["content"] == "ความเป็นมา"
    assert payload["sources"] == ["ผู้ใช้"]
    assert "scope_subsections" not in payload


def test_warn_missing_facts_skips_filled() -> None:
    result = DraftResult()
    filled = {key: {"status": "filled", "content": "มีข้อมูล"} for key in FACT_REQUIRED_SLOTS}
    _warn_missing_facts(filled, result)
    assert result.warnings == []


@pytest.mark.asyncio
async def test_generator_rag_unpacks_mcp_and_three_tuple() -> None:
    async def mcp_retrieve(*_args, **_kwargs):
        chunk = RetrievedChunk(id="m", text="จาก MCP", score=0.8, source_document="ด")
        return RetrievalResult(chunks=[chunk], query="q", top_k=1, actual_count=1), [], False, True

    gen = FullDraftGenerator(retrieve=mcp_retrieve)
    chunks, warning = await gen._rag("s1", "u1")
    assert chunks[0]["id"] == "m"
    assert warning is None

    async def three_tuple(*_args, **_kwargs):
        return RetrievalResult(chunks=[], query="q", top_k=1, actual_count=0), [], True

    gen = FullDraftGenerator(retrieve=three_tuple)
    chunks, warning = await gen._rag("s2", None)
    assert chunks == []
    assert warning == "ไม่พบเอกสารกฎหมายที่เกี่ยวข้องเพียงพอสำหรับหมวดนี้"


@pytest.mark.asyncio
async def test_generator_rag_caps_top_k() -> None:
    async def many(*_args, **_kwargs):
        rows = [RetrievedChunk(id=str(index), text="ก", score=0.9) for index in range(RAG_TOP_K + 5)]
        return RetrievalResult(chunks=rows, query="q", top_k=len(rows), actual_count=len(rows)), [], False, False

    gen = FullDraftGenerator(retrieve=many)
    chunks, warning = await gen._rag("s1", None)
    assert len(chunks) == RAG_TOP_K
    assert warning is None


@pytest.mark.asyncio
async def test_generator_short_and_blank_drafts() -> None:
    cache = MagicMock()
    cache.get_draft = AsyncMock(return_value=None)
    cache.set_draft = AsyncMock()
    short_agent = MagicMock()
    short_agent.draft = AsyncMock(return_value="สั้น")

    async def fake_retrieve(*_args, **_kwargs):
        chunk = RetrievedChunk(id="1", text="ก", score=0.9)
        return RetrievalResult(chunks=[chunk], query="q", top_k=1, actual_count=1), [], False, False

    gen = FullDraftGenerator(llm=MagicMock(), cache=cache, retrieve=fake_retrieve)
    with (
        patch("app.services.full_draft_generator.TOR_SECTION_ORDER", ["s1"]),
        patch("app.services.full_draft_generator.get_agent_for_section", return_value=short_agent),
    ):
        short = await gen.generate_all({}, project_id="p1")
    assert short.draft_quality_scores["s1"] == 50.0
    cache.set_draft.assert_awaited()

    cache.set_draft.reset_mock()
    blank_agent = MagicMock()
    blank_agent.draft = AsyncMock(return_value="   ")
    with (
        patch("app.services.full_draft_generator.TOR_SECTION_ORDER", ["s1"]),
        patch("app.services.full_draft_generator.get_agent_for_section", return_value=blank_agent),
    ):
        blank = await gen.generate_all({})
    assert "s1" in blank.sections_pending
    cache.set_draft.assert_not_awaited()


@pytest.mark.asyncio
async def test_generator_timeout_marks_remaining_pending() -> None:
    gen = FullDraftGenerator(llm=MagicMock())
    with (
        patch("app.services.full_draft_generator.TOR_SECTION_ORDER", ["s1", "s2"]),
        patch("app.services.full_draft_generator.time.monotonic", side_effect=[0.0, 999999.0]),
    ):
        result = await gen.generate_all({})
    assert "s1" in result.sections_pending
    assert "s2" in result.sections_pending
    assert any("หมดเวลา" in item for item in result.warnings)


def test_llm_client_copies_deployment_mode() -> None:
    gen = FullDraftGenerator()
    gen._deployment_mode = "cloud"
    settings = MagicMock()
    settings.model_copy.return_value = settings
    with (
        patch("app.services.full_draft_generator.get_settings", return_value=settings),
        patch("app.services.full_draft_generator.ProviderFactory") as factory,
    ):
        factory.return_value.get_llm.return_value = "llm"
        assert gen._llm_client() == "llm"
    settings.model_copy.assert_called_once_with(update={"deployment_mode": "cloud"})
    factory.return_value.get_llm.assert_called_once_with("draft")


@pytest.mark.asyncio
async def test_auto_correct_keeps_original_when_redraft_empty() -> None:
    agent = MagicMock()
    agent.draft = AsyncMock(return_value="")

    async def fake_retrieve(*_args, **_kwargs):
        return RetrievalResult(chunks=[], query="q", top_k=1, actual_count=0), [], False, False

    gen = FullDraftGenerator(llm=MagicMock(), retrieve=fake_retrieve)
    with patch("app.services.full_draft_generator.get_agent_for_section", return_value=agent):
        text = await gen.auto_correct(
            "s1",
            "เดิม",
            [{"message": "แก้", "affected_section": ""}],
            {},
            0,
        )
    assert text == "เดิม"


def test_validate_document_without_budget_meta() -> None:
    engine = MagicMock()
    engine.validate.return_value = SimpleNamespace(findings=[], quality_score=10)
    gen = FullDraftGenerator()
    with patch("app.services.full_draft_generator._create_rule_engine", return_value=engine):
        gen.validate_document({"s1": "ร่าง"}, {"name": "โครงการ"})
    document = engine.validate.call_args.args[0]
    assert "budget" not in document
    assert "project_type" not in document
    assert document["s1"] == "ร่าง"
