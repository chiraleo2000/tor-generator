"""Shared LLM token budgets."""

import pytest

from app.llm_tokens import (
    CHAT_MAX_TOKENS,
    CHAT_MIN_TOKENS,
    DRAFT_MAX_TOKENS,
    DRAFT_MIN_TOKENS,
    EMBEDDING_MAX_TOKENS,
    GEMMA_CONTEXT_WINDOW,
    REVIEW_ANALYZE_MAX_TOKENS,
    REVIEW_CONTEXT_WINDOW,
    REVIEW_MAX_TOKENS,
    REVIEW_SUGGESTION_MAX_TOKENS,
    chars_for_tokens,
    clamp_max_tokens,
    estimate_tokens,
    live_section_max_tokens,
    truncate_for_embedding,
)


def test_draft_and_chat_budgets():
    assert GEMMA_CONTEXT_WINDOW == 131_072
    assert EMBEDDING_MAX_TOKENS == 2_048
    assert DRAFT_MAX_TOKENS >= 8_192
    assert DRAFT_MAX_TOKENS <= GEMMA_CONTEXT_WINDOW
    assert DRAFT_MIN_TOKENS == 192
    assert CHAT_MAX_TOKENS == 32_768
    assert CHAT_MIN_TOKENS == 0
    assert REVIEW_MAX_TOKENS == GEMMA_CONTEXT_WINDOW
    assert REVIEW_ANALYZE_MAX_TOKENS == 65_536
    assert REVIEW_SUGGESTION_MAX_TOKENS == 32_768
    assert REVIEW_CONTEXT_WINDOW == GEMMA_CONTEXT_WINDOW
    assert chars_for_tokens(DRAFT_MIN_TOKENS) == 384
    assert CHAT_MAX_TOKENS + 4_000 < GEMMA_CONTEXT_WINDOW
    assert live_section_max_tokens() <= GEMMA_CONTEXT_WINDOW
    capped = clamp_max_tokens(
        "x",
        DRAFT_MAX_TOKENS,
        context_window=GEMMA_CONTEXT_WINDOW,
    )
    assert 256 <= capped <= GEMMA_CONTEXT_WINDOW - 256


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


def test_truncate_for_embedding_caps_at_requested_tokens():
    short = "สั้น"
    assert truncate_for_embedding(short) == short
    long_text = "ก" * (chars_for_tokens(EMBEDDING_MAX_TOKENS) + 50)
    clipped = truncate_for_embedding(long_text, max_tokens=EMBEDDING_MAX_TOKENS)
    assert len(clipped) == chars_for_tokens(EMBEDDING_MAX_TOKENS)
    assert estimate_tokens(clipped) <= EMBEDDING_MAX_TOKENS


@pytest.mark.parametrize(
    ("provider", "model"),
    [
        ("lm_studio", "google/gemma-4-e4b"),
        ("openai", "gpt-4o-mini"),
        ("claude", "claude-sonnet-4-20250514"),
        ("bedrock", "anthropic.claude-3-5-sonnet-20241022-v2:0"),
    ],
)
def test_clamp_uses_provider_window(provider, model):
    from app.providers.model_capabilities import capabilities_for, reset_capability_cache

    reset_capability_cache()
    caps = capabilities_for(provider, model, "local", "text-embedding-embeddinggemma-300m")
    capped = clamp_max_tokens("ก" * 200, 999_999, context_window=caps.context_window)
    assert 256 <= capped < caps.context_window
