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
