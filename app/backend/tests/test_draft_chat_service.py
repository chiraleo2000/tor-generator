"""Unit tests for Phase 3 draft-chat intent parsing and edit prompts."""

from unittest.mock import MagicMock, patch

import pytest

from app.api.v1.endpoints.draft_chat import _section_done_event, _sse
from app.services.draft_chat_service import (
    edit_section_draft,
    parse_draft_message_intent,
)


def test_parse_accept():
    intent, key, _ = parse_draft_message_intent("ยอมรับ")
    assert intent == "accept"
    assert key is None


def test_parse_redraft_section_13_not_1():
    intent, key, _ = parse_draft_message_intent("ร่างใหม่ หมวด 13")
    assert intent == "redraft"
    assert key == "s13"


def test_parse_edit_by_label():
    intent, key, _ = parse_draft_message_intent("แก้ความเป็นมาให้สั้นลง")
    assert intent == "edit"
    assert key == "s1"


def test_parse_edit_prefix():
    intent, key, _ = parse_draft_message_intent("แก้ไขหมวด 6 ให้ระบุแหล่งงบ")
    assert intent == "edit"
    assert key == "s6"


def test_parse_freeform_with_section():
    intent, key, _ = parse_draft_message_intent("วงเงินงบประมาณให้ระบุแหล่งงบด้วย")
    assert intent == "freeform"
    assert key == "s6"


@pytest.mark.asyncio
async def test_edit_section_draft_includes_intake_slot():
    mock_llm = MagicMock()

    async def fake_stream(messages, **_kwargs):
        user = messages[1]["content"]
        assert "กรมบัญชีกลาง" in user
        assert "ให้สั้นลง" in user
        yield "ร่างใหม่"

    mock_llm.stream = fake_stream
    with patch(
        "app.services.draft_chat_service.ProviderFactory.get_llm",
        return_value=mock_llm,
    ):
        tokens = [
            token
            async for token in edit_section_draft(
                "s1",
                "ร่างเดิมยาว",
                "ให้สั้นลง",
                {"s1": {"content": "กรมบัญชีกลางจัดซื้อระบบ", "status": "filled"}},
            )
        ]
    assert tokens == ["ร่างใหม่"]


@pytest.mark.asyncio
async def test_draft_single_section_falls_back_on_timeout():
    from app.services.draft_chat_service import draft_single_section, fallback_section_prose

    mock_llm = MagicMock()

    async def boom(*_args, **_kwargs):
        raise TimeoutError("LM Studio did not respond within 180s")
        yield "x"

    mock_llm.stream = boom
    expected = fallback_section_prose(
        "s1", {"s1": {"content": "กรมบัญชีกลางจัดซื้อระบบ", "status": "filled"}}
    )
    with patch(
        "app.services.draft_chat_service.ProviderFactory.get_llm",
        return_value=mock_llm,
    ), patch(
        "app.services.draft_chat_service.hybrid_retrieve",
        side_effect=RuntimeError("no rag"),
    ):
        tokens = [
            token
            async for token in draft_single_section(
                "s1",
                {"s1": {"content": "กรมบัญชีกลางจัดซื้อระบบ", "status": "filled"}},
            )
        ]
    assert tokens == [expected]
    assert "พ.ศ. 2560" in expected


def test_fallback_section_prose_uses_slot_facts():
    from app.services.draft_chat_service import fallback_section_prose

    text = fallback_section_prose("s6", {"s6": {"content": "2,500,000 บาท", "status": "filled"}})
    assert "2,500,000" in text
    assert len(text) > 40


def test_section_done_sse_includes_count_and_label():
    payload = _section_done_event("s1", "ความเป็นมา", "เนื้อหาร่าง", 4)
    assert payload.startswith("event: section_done")
    assert "ความเป็นมา" in payload
    assert _sse("ping", {"ok": True}).startswith("event: ping")
