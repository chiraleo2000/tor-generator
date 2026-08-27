"""Tests for structured LLM invoke retry."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.providers.structured_invoke import invoke_with_schema


@pytest.mark.asyncio
async def test_invoke_with_schema_retries_then_succeeds():
    llm = MagicMock()
    llm.invoke = AsyncMock(
        side_effect=[
            MagicMock(content="not-json"),
            MagicMock(content='{"ok": true}'),
        ]
    )
    payload = await invoke_with_schema(
        llm,
        [{"role": "user", "content": "x"}],
        {"type": "object"},
        "sample",
        attempts=2,
        temperature=0.1,
    )
    assert payload["ok"] is True
    assert llm.invoke.await_count == 2
    retry_messages = llm.invoke.await_args_list[1].args[0]
    assert retry_messages[-1]["content"].startswith("ตอบเป็น JSON")


@pytest.mark.asyncio
async def test_invoke_with_schema_wraps_suggestion_array():
    llm = MagicMock()
    llm.invoke = AsyncMock(
        return_value=MagicMock(
            content='[{"category":"clarity","section_key":"s1","current_text":"a","suggested_text":"b","predicted_score_improvement":1}]'
        )
    )
    payload = await invoke_with_schema(
        llm,
        [{"role": "user", "content": "x"}],
        {"type": "object", "properties": {"suggestions": {"type": "array"}}},
        "review_suggestions",
        attempts=1,
    )
    assert len(payload["suggestions"]) == 1
    assert payload["suggestions"][0]["section_key"] == "s1"


@pytest.mark.asyncio
async def test_invoke_with_schema_raises_after_retries():
    llm = MagicMock()
    llm.invoke = AsyncMock(return_value=MagicMock(content="nope"))
    with pytest.raises(ValueError, match="sample"):
        await invoke_with_schema(
            llm,
            [{"role": "user", "content": "x"}],
            {"type": "object"},
            "sample",
            attempts=2,
        )
