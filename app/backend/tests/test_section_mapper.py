"""Section mapper incremental update with a fake LLM."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.intake_service import empty_slot_map
from app.services.section_mapper import SectionMapper, apply_incoming_slots


class FakeLLM:
    def __init__(self, content: str):
        self.content = content

    async def invoke(self, _messages, **_kwargs):
        return SimpleNamespace(content=self.content)


@pytest.mark.asyncio
async def test_incremental_append_and_preserve():
    mapper = SectionMapper(
        llm=FakeLLM('{"targets": [{"slot_key": "s1", "content": "ใหม่", "action": "append"}]}')
    )
    current = empty_slot_map()
    current["s2"] = {"content": "คงเดิม", "status": "filled", "sources": ["a"]}
    result = await mapper.incremental_update("ใหม่", current, ["ถาม s1"])
    assert "s1" in result.affected
    assert result.slot_map["s1"]["status"] == "filled"
    assert result.slot_map["s2"]["content"] == "คงเดิม"


def test_apply_incoming_ignores_unknown_keys():
    result = apply_incoming_slots(empty_slot_map(), {"nope": {"status": "filled"}})
    assert "nope" not in result
    assert len(result) == 27


def test_apply_incoming_normalizes_invalid_status():
    from app.services.section_mapper import mark_unmapped_errors

    result = apply_incoming_slots(
        empty_slot_map(),
        {"s1": {"content": "ความเป็นมา", "status": "weird", "sources": "nope"}},
    )
    assert result["s1"]["status"] == "gap"
    assert result["s1"]["sources"] == []
    marked = mark_unmapped_errors(empty_slot_map())
    assert marked["s1"]["status"] == "gap"


@pytest.mark.asyncio
async def test_map_content_retry_then_hard_fail():
    from app.services.section_mapper import SectionMapper

    calls = {"n": 0}

    class BoomLLM:
        async def invoke(self, *_args, **_kwargs):
            calls["n"] += 1
            raise RuntimeError("mapper down")

    mapper = SectionMapper(llm=BoomLLM())
    result = await mapper.map_content("เนื้อหายาวพอที่จะลดรอบสอง")
    assert result.partial is True
    assert result.error
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_map_content_success_and_incremental_empty_targets():
    from app.services.section_mapper import SectionMapper

    mapper = SectionMapper(
        llm=FakeLLM('{"slot_map": {"s1": {"content": "มา", "status": "filled"}}}')
    )
    mapped = await mapper.map_content("เอกสาร", {"name": "โครงการ"})
    assert mapped.slot_map["s1"]["status"] == "filled"

    mapper = SectionMapper(llm=FakeLLM('{"targets": []}'))
    current = empty_slot_map()
    result = await mapper.incremental_update("ไม่รู้", current, ["ถาม"])
    assert result.candidates
    assert not result.affected


@pytest.mark.asyncio
async def test_incremental_classify_error_and_replace_action():
    from app.services.section_mapper import SectionMapper

    class Boom:
        async def invoke(self, *_a, **_k):
            raise RuntimeError("classify down")

    mapper = SectionMapper(llm=Boom())
    result = await mapper.incremental_update("ใหม่", empty_slot_map(), ["ถาม"])
    assert result.error

    mapper = SectionMapper(
        llm=FakeLLM(
            '{"targets": [{"slot_key": "s1", "content": "แทนที่", "action": "replace"}]}'
        )
    )
    current = empty_slot_map()
    current["s1"] = {"content": "เดิม", "status": "filled", "sources": ["a"]}
    result = await mapper.incremental_update("แทนที่", current, ["ถาม s1"])
    assert result.slot_map["s1"]["content"] == "แทนที่"
