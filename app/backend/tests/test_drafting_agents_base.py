"""Base drafting agent with a fake LLM provider."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.orchestrator.agents.background_agent import BackgroundDraftingAgent
from app.orchestrator.agents.base import THAI_FORMAL_REGISTER_PREAMBLE, BaseDraftingAgent
from app.orchestrator.agents.registry import (
    get_agent_for_section,
    get_review_agent,
    list_available_agents,
)
from app.providers.base import LLMResponse


class _TinyAgent(BaseDraftingAgent):
    section_key = "s1"
    section_name_th = "ความเป็นมา"
    section_name_en = "Background"

    def get_system_prompt(self) -> str:
        return "system-prompt"


@pytest.mark.asyncio
async def test_draft_invokes_fake_llm_with_rag_and_feedback():
    llm = AsyncMock()
    llm.invoke = AsyncMock(
        return_value=LLMResponse(
            content="ร่างความเป็นมา",
            model="fake-llm",
            usage={"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
        )
    )
    text = await _TinyAgent().draft(
        llm,
        {"project_name": "โครงการทดสอบ"},
        rag_chunks=[{"text": "พ.ร.บ. การจัดซื้อจัดจ้าง", "source_document": "พรบ2560"}],
        template={"placeholder_guidance": {"s1": "อธิบายความเป็นมา"}},
        validation_findings=[
            {
                "severity": "warning",
                "message": "ยังไม่ระบุภารกิจ",
                "recommended_correction": "เพิ่มภารกิจหน่วยงาน",
            }
        ],
        human_feedback="โปรดกระชับย่อหน้าแรก",
    )
    assert text == "ร่างความเป็นมา"
    messages = llm.invoke.await_args.args[0]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == "system-prompt"
    user = messages[1]["content"]
    assert "โครงการทดสอบ" in user
    assert "พ.ร.บ. การจัดซื้อจัดจ้าง" in user
    assert "ยังไม่ระบุภารกิจ" in user
    assert "โปรดกระชับย่อหน้าแรก" in user


def test_background_agent_prompt_uses_thai_preamble():
    prompt = BackgroundDraftingAgent().get_system_prompt()
    assert prompt.startswith(THAI_FORMAL_REGISTER_PREAMBLE)
    assert "ความเป็นมา" in prompt


def test_format_user_input_handles_empty_and_nested():
    agent = _TinyAgent()
    assert agent._format_user_input({}) == "(ไม่มีข้อมูลจากผู้ใช้)"
    text = agent._format_user_input(
        {"items": ["ก", "ข"], "meta": {"budget": 1000}, "name": "โครงการ"}
    )
    assert "ก" in text
    assert "budget" in text
    assert "โครงการ" in text


def test_registry_prompts_and_unknown_section():
    listed = list_available_agents()
    assert len(listed) == 14
    assert get_agent_for_section("s1") is not None
    assert get_agent_for_section("unknown") is None
    assert get_review_agent() is not None
    for item in listed:
        if item["section_key"] == "review":
            continue
        agent = get_agent_for_section(item["section_key"])
        assert agent is not None
        prompt = agent.get_system_prompt()
        assert THAI_FORMAL_REGISTER_PREAMBLE[:20] in prompt or len(prompt) > 20
        message = agent.build_user_message(
            {
                "project_name": "โครงการทดสอบ",
                "budget": 5_000_000,
                "installments": 4,
                "penalty_rate": 0.5,
                "duration": 90,
            },
            [],
        )
        assert "โครงการทดสอบ" in message or "ข้อมูลจากผู้ใช้" in message


def test_specialized_agents_add_constraint_notes():
    from app.orchestrator.agents.budget_agent import BudgetDraftingAgent
    from app.orchestrator.agents.payment_agent import PaymentDraftingAgent
    from app.orchestrator.agents.penalties_agent import PenaltiesDraftingAgent
    from app.orchestrator.agents.qualifications_agent import QualificationsDraftingAgent
    from app.orchestrator.agents.timeline_agent import TimelineDraftingAgent

    payment = PaymentDraftingAgent().build_user_message(
        {"budget": 8_000_000, "installments": 4},
        [],
    )
    assert "100%" in payment
    assert "4 งวด" in payment

    penalties = PenaltiesDraftingAgent().build_user_message(
        {"budget": 1_000_000, "penalty_rate": 0.5},
        [],
    )
    assert "อยู่นอกช่วง" in penalties

    high = TimelineDraftingAgent().build_user_message({"budget": 150_000_000}, [])
    low = TimelineDraftingAgent().build_user_message({"budget": 1_000_000, "duration": 30}, [])
    assert "180" in high
    assert "365" in low

    quals = QualificationsDraftingAgent().build_user_message({"budget": 10_000_000}, [])
    assert "2,500,000" in quals or "2500000" in quals or "_computed_capital" in quals

    budget = BudgetDraftingAgent().build_user_message({"budget": 5_000_000}, [])
    assert "5,000,000" in budget


def test_format_user_input_skips_empty_values():
    agent = _TinyAgent()
    assert agent._format_user_input({"name": "", "note": None}) == "(ไม่มีข้อมูลจากผู้ใช้)"
    message = agent.build_user_message({}, [], template={"placeholder_guidance": {}})
    assert "ข้อมูลจากผู้ใช้" in message
