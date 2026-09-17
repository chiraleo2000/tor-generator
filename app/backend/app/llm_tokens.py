"""Shared LLM token budgets for TOR draft, KB Q&A, and TOR review.

OpenAI-compatible APIs expose max_tokens (completion cap), not min_tokens.
Draft uses DRAFT_MIN_TOKENS as a soft floor in substance prompts (not a
verbosity target). KB chat no longer
enforces a minimum length (CHAT_MIN_TOKENS is unused).

Completion and embedding limits follow env (``TOR_*`` / ``EMBEDDING_*``) via
``current_capabilities()``. Catalog constants below are fallbacks / test ceilings;
prefer the ``live_*`` helpers at call sites.
"""

from __future__ import annotations

from app.providers.model_capabilities import (
    DEFAULT_CONTEXT_WINDOW,
    GEMMA_CONTEXT_WINDOW as _GEMMA_WINDOW,
    chat_max_tokens as _live_chat,
    current_capabilities,
    embedding_max_input as live_embedding_max_input,
    review_analyze_max_tokens as _live_review_analyze,
    review_max_tokens as _live_review,
    section_max_tokens as _live_section,
    scope_max_tokens as _live_scope,
)

# Kept for tests / docs that mention Gemma's max window; live clamp uses env.
GEMMA_CONTEXT_WINDOW = _GEMMA_WINDOW
# Catalog ceilings — clamp_max_tokens / live helpers shrink per provider/env.
SECTION_MAX_TOKENS = 32_768
SECTION_MIN_TOKENS = 192
SCOPE_SUB_MAX_TOKENS = 8_192
SCOPE_SUB_MIN_TOKENS = 96
DRAFT_MAX_TOKENS = SECTION_MAX_TOKENS
DRAFT_MIN_TOKENS = SECTION_MIN_TOKENS
CHAT_MAX_TOKENS = 32_768
CHAT_MIN_TOKENS = 0
EMBEDDING_MAX_TOKENS = 2_048

# Review catalog ceilings (actual runtime uses live_review_* / TOR_CONTEXT_WINDOW).
REVIEW_MAX_TOKENS = DEFAULT_CONTEXT_WINDOW
REVIEW_CONTEXT_WINDOW = DEFAULT_CONTEXT_WINDOW
REVIEW_ANALYZE_MAX_TOKENS = 16_384
REVIEW_SUGGESTION_MAX_TOKENS = 8_192
REVIEW_TIMEOUT_SECONDS = 900.0
REVIEW_LEGAL_CONTEXT_CHARS = 90_000
REVIEW_REQUIREMENTS_CHARS = 60_000
REVIEW_CUSTOM_REQUIREMENTS_CHARS = 32_000

DEFAULT_MAX_TOKENS = DRAFT_MAX_TOKENS


def live_context_window() -> int:
    return current_capabilities().context_window


def live_section_max_tokens() -> int:
    return _live_section()


def live_scope_max_tokens() -> int:
    return _live_scope()


def live_chat_max_tokens() -> int:
    return _live_chat()


def live_review_max_tokens() -> int:
    return _live_review()


def live_review_analyze_max_tokens() -> int:
    return _live_review_analyze()


def live_review_context_window() -> int:
    return live_context_window()


def live_embedding_max_tokens() -> int:
    return live_embedding_max_input()


def estimate_tokens(text: str) -> int:
    """Conservative token estimate for mixed Thai/English text."""
    return max(1, (len(text or "") + 1) // 2)


def chars_for_tokens(tokens: int) -> int:
    """Inverse of estimate_tokens for prompt length copy."""
    return max(0, int(tokens) * 2)


def truncate_for_embedding(
    text: str, max_tokens: int | None = None
) -> str:
    """Keep embedding input inside the active model's input window."""
    raw = text or ""
    limit_tokens = int(max_tokens) if max_tokens is not None else live_embedding_max_input()
    limit = chars_for_tokens(limit_tokens)
    if len(raw) <= limit:
        return raw
    return raw[:limit]


def clamp_max_tokens(
    prompt: str,
    requested: int,
    *,
    context_window: int | None = None,
    system: str = "",
) -> int:
    """Keep prompt + completion inside the model context window."""
    window = int(context_window) if context_window is not None else live_context_window()
    used = estimate_tokens(system) + estimate_tokens(prompt)
    room = int(window) - used - 256
    return max(256, min(int(requested), room))
