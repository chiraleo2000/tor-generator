"""Shared LLM token budgets."""

from app.llm_tokens import (
    CHAT_MAX_TOKENS,
    CHAT_MIN_TOKENS,
    DRAFT_MAX_TOKENS,
    DRAFT_MIN_TOKENS,
    EMBEDDING_MAX_TOKENS,
    GEMMA_CONTEXT_WINDOW,
    REVIEW_CONTEXT_WINDOW,
    REVIEW_MAX_TOKENS,
    REVIEW_SUGGESTION_MAX_TOKENS,
    chars_for_tokens,
    clamp_max_tokens,
    estimate_tokens,
    truncate_for_embedding,
)


def test_draft_and_chat_budgets():
    assert GEMMA_CONTEXT_WINDOW == 131_072
    assert EMBEDDING_MAX_TOKENS == 2_048
    assert DRAFT_MAX_TOKENS == GEMMA_CONTEXT_WINDOW
    assert DRAFT_MIN_TOKENS == 6_144
    assert CHAT_MAX_TOKENS == 32_768
    assert CHAT_MIN_TOKENS == 0
    assert REVIEW_MAX_TOKENS == GEMMA_CONTEXT_WINDOW
    assert REVIEW_SUGGESTION_MAX_TOKENS == 8_192
    assert REVIEW_CONTEXT_WINDOW == GEMMA_CONTEXT_WINDOW
    assert chars_for_tokens(DRAFT_MIN_TOKENS) == 12_288
    assert CHAT_MAX_TOKENS + 4_000 < GEMMA_CONTEXT_WINDOW
    assert DRAFT_MAX_TOKENS <= GEMMA_CONTEXT_WINDOW
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


def test_truncate_for_embedding_caps_at_2048_tokens():
    short = "สั้น"
    assert truncate_for_embedding(short) == short
    long_text = "ก" * (chars_for_tokens(EMBEDDING_MAX_TOKENS) + 50)
    clipped = truncate_for_embedding(long_text)
    assert len(clipped) == chars_for_tokens(EMBEDDING_MAX_TOKENS)
    assert estimate_tokens(clipped) <= EMBEDDING_MAX_TOKENS
