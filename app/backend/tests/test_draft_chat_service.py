"""Unit tests for Phase 3 draft-chat intent parsing and edit prompts."""

from unittest.mock import MagicMock, patch

import pytest

from app.api.v1.endpoints.draft_chat import _section_done_event, _sse
from app.services.draft_chat_service import (
    DRAFT_MAX_TOKENS,
    _section_prompt_context,
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


def test_section_prompt_includes_this_project_intake_only():
    prompt = _section_prompt_context(
        "s1",
        {
            "_project_intake": {"content": "เอกสารขั้นศูนย์ของโครงการนี้", "status": "filled"},
            "s1": {"content": "ความเป็นมา", "status": "filled"},
        },
        "พ.ร.บ. การจัดซื้อจัดจ้าง",
    )
    assert "เอกสารขั้นที่ ๐ ของโครงการนี้เท่านั้น" in prompt
    assert "เอกสารขั้นศูนย์ของโครงการนี้" in prompt
    assert "พ.ร.บ. การจัดซื้อจัดจ้าง" in prompt
    assert "6144" in prompt
    assert "หนึ่งร้อยถึงห้าร้อยคำ" not in prompt


@pytest.mark.asyncio
async def test_edit_section_draft_includes_intake_slot():
    mock_llm = MagicMock()

    async def fake_stream(messages, **kwargs):
        assert kwargs["max_tokens"] == DRAFT_MAX_TOKENS
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
async def test_draft_single_section_streams_llm_tokens():
    from app.services.draft_chat_service import draft_single_section

    mock_llm = MagicMock()

    async def fake_stream(_messages, **kwargs):
        assert kwargs["max_tokens"] == DRAFT_MAX_TOKENS
        yield "ร่าง"
        yield "จาก"
        yield "LM Studio"

    mock_llm.stream = fake_stream
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
    assert tokens == ["ร่าง", "จาก", "LM Studio"]


@pytest.mark.asyncio
async def test_draft_scope_subsection_streams_llm_tokens():
    from app.services.draft_chat_service import draft_scope_subsection

    mock_llm = MagicMock()

    async def fake_stream(_messages, **kwargs):
        assert kwargs["max_tokens"] == DRAFT_MAX_TOKENS
        yield "ตารางผลงานส่งมอบ"

    mock_result = MagicMock()
    mock_result.chunks = [MagicMock(text="พ.ร.บ. การจัดซื้อจัดจ้าง")]

    async def fake_retrieve(*_args, **_kwargs):
        return mock_result, [], False

    mock_llm.stream = fake_stream
    with patch(
        "app.services.draft_chat_service.ProviderFactory.get_llm",
        return_value=mock_llm,
    ), patch(
        "app.services.draft_chat_service.hybrid_retrieve",
        side_effect=fake_retrieve,
    ):
        tokens = [
            token
            async for token in draft_scope_subsection(
                "s4.8",
                {"s4.8": {"content": "ส่งมอบคู่มือ", "status": "filled"}},
            )
        ]
    assert tokens == ["ตารางผลงานส่งมอบ"]


@pytest.mark.asyncio
async def test_draft_single_section_propagates_llm_timeout():
    from app.services.draft_chat_service import draft_single_section

    mock_llm = MagicMock()

    async def boom(*_args, **_kwargs):
        raise TimeoutError("LM Studio did not respond within 180s")
        yield "x"

    mock_llm.stream = boom
    with patch(
        "app.services.draft_chat_service.ProviderFactory.get_llm",
        return_value=mock_llm,
    ), patch(
        "app.services.draft_chat_service.hybrid_retrieve",
        side_effect=RuntimeError("no rag"),
    ):
        with pytest.raises(TimeoutError, match="LM Studio"):
            [
                token
                async for token in draft_single_section(
                    "s1",
                    {"s1": {"content": "กรมบัญชีกลางจัดซื้อระบบ", "status": "filled"}},
                )
            ]


@pytest.mark.asyncio
async def test_collect_scope_subsection_drafts_calls_llm_in_order():
    from app.domain.tor_sections import SCOPE_SUBSECTIONS
    from app.services.draft_chat_service import collect_scope_subsection_drafts

    calls: list[str] = []

    async def fake_sub(sub_key, *_args, **_kwargs):
        calls.append(sub_key)
        yield f"ร่างจากโมเดล {sub_key}"

    with patch(
        "app.services.draft_chat_service.draft_scope_subsection",
        side_effect=fake_sub,
    ):
        out = await collect_scope_subsection_drafts({})

    assert calls == list(SCOPE_SUBSECTIONS)
    assert out == {key: f"ร่างจากโมเดล {key}" for key in SCOPE_SUBSECTIONS}


@pytest.mark.asyncio
async def test_collect_scope_skips_prior_then_drafts_rest_in_order():
    from app.domain.tor_sections import SCOPE_SUBSECTIONS
    from app.services.draft_chat_service import collect_scope_subsection_drafts

    keys = list(SCOPE_SUBSECTIONS)
    calls: list[str] = []

    async def fake_sub(sub_key, *_args, **_kwargs):
        calls.append(sub_key)
        yield f"llm-{sub_key}"

    with patch(
        "app.services.draft_chat_service.draft_scope_subsection",
        side_effect=fake_sub,
    ):
        out = await collect_scope_subsection_drafts(
            {},
            only_missing=True,
            existing={keys[0]: "ร่างเดิมจากโมเดล"},
        )

    assert calls == keys[1:]
    assert out[keys[0]] == "ร่างเดิมจากโมเดล"
    assert out[keys[1]] == f"llm-{keys[1]}"


def test_section_done_sse_includes_count_and_label():
    payload = _section_done_event("s1", "ความเป็นมา", "เนื้อหาร่าง", 4)
    assert payload.startswith("event: section_done")
    assert "ความเป็นมา" in payload
    assert _sse("ping", {"ok": True}).startswith("event: ping")
