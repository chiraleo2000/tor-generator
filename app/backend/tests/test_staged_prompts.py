"""Analyze-then-compose helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.providers.base import LLMResponse
from app.services.staged_prompts import (
    COMPOSE_SECTION_INSTRUCTION,
    SECTION_ANALYZE_SYSTEM,
    analyze_notes,
    attach_analysis,
)


@pytest.mark.asyncio
async def test_analyze_notes_returns_model_text():
    llm = MagicMock()
    llm.invoke = AsyncMock(
        return_value=LLMResponse(
            content="  บันทึก  ",
            model="fake",
            usage={"total_tokens": 1},
        )
    )
    notes = await analyze_notes(llm, "ข้อมูลผู้ใช้", SECTION_ANALYZE_SYSTEM)
    assert notes == "บันทึก"
    assert llm.invoke.await_count == 1
    system = llm.invoke.await_args.args[0][0]["content"]
    assert "วิเคราะห์เท่านั้น" in system


@pytest.mark.asyncio
async def test_analyze_notes_empty_on_failure_or_non_string():
    missing = MagicMock(spec=[])
    assert await analyze_notes(missing, "x", SECTION_ANALYZE_SYSTEM) == ""

    llm = MagicMock()
    llm.invoke = AsyncMock(side_effect=RuntimeError("down"))
    assert await analyze_notes(llm, "x", SECTION_ANALYZE_SYSTEM) == ""

    llm.invoke = AsyncMock(return_value=MagicMock(content=None))
    assert await analyze_notes(llm, "x", SECTION_ANALYZE_SYSTEM) == ""


def test_attach_analysis_includes_compose_instruction():
    bare = attach_analysis("ต้นทาง", "", COMPOSE_SECTION_INSTRUCTION)
    assert "ต้นทาง" in bare
    assert "ขั้นที่ 2" in bare
    filled = attach_analysis("ต้นทาง", "ช่องว่างเรื่องค่าปรับ", COMPOSE_SECTION_INSTRUCTION)
    assert "บันทึกวิเคราะห์ขั้นที่ 1" in filled
    assert "ช่องว่างเรื่องค่าปรับ" in filled
