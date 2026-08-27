"""Shared LLM token budgets."""

from app.llm_tokens import (
    CHAT_MAX_TOKENS,
    CHAT_MIN_TOKENS,
    DRAFT_MAX_TOKENS,
    DRAFT_MIN_TOKENS,
    REVIEW_CONTEXT_WINDOW,
    REVIEW_MAX_TOKENS,
    REVIEW_SUGGESTION_MAX_TOKENS,
    chars_for_tokens,
    clamp_max_tokens,
    estimate_tokens,
)


def test_draft_and_chat_budgets():
    assert DRAFT_MAX_TOKENS == 32_768
    assert DRAFT_MIN_TOKENS == 6_144
    assert CHAT_MAX_TOKENS == 32_768
    assert CHAT_MIN_TOKENS == 6_144
    assert REVIEW_MAX_TOKENS == 128_000
    assert REVIEW_SUGGESTION_MAX_TOKENS == 4_096
    assert REVIEW_CONTEXT_WINDOW == 128_000
    assert chars_for_tokens(DRAFT_MIN_TOKENS) == 12_288


def test_clamp_max_tokens_leaves_room_for_the_prompt():
    prompt = "ก" * 10_000
    capped = clamp_max_tokens(
        prompt,
        REVIEW_MAX_TOKENS,
        context_window=REVIEW_CONTEXT_WINDOW,
        system="sys",
    )
    used = estimate_tokens("sys") + estimate_tokens(prompt)
    assert capped <= REVIEW_CONTEXT_WINDOW - used - 256
    assert capped >= 256
