"""Shared LLM token budgets for TOR draft, KB Q&A, and TOR review.

OpenAI-compatible APIs expose max_tokens (completion cap), not min_tokens.
The floor is enforced in system/user prompts via DRAFT_MIN_TOKENS / CHAT_MIN_TOKENS.
"""

from __future__ import annotations

DRAFT_MAX_TOKENS = 32_768
DRAFT_MIN_TOKENS = 6_144
CHAT_MAX_TOKENS = 32_768
CHAT_MIN_TOKENS = 6_144

# Review packs a large TOR + พ.ร.บ. + Phase 0 in one user-facing run.
REVIEW_MAX_TOKENS = 128_000
REVIEW_CONTEXT_WINDOW = 128_000
# Suggestion JSON must stay short; a 128k completion cap makes Gemma leave the schema.
REVIEW_SUGGESTION_MAX_TOKENS = 4_096

DEFAULT_MAX_TOKENS = DRAFT_MAX_TOKENS


def estimate_tokens(text: str) -> int:
    """Conservative Gemma token estimate for mixed Thai/English text."""
    return max(1, (len(text or "") + 1) // 2)


def chars_for_tokens(tokens: int) -> int:
    """Inverse of estimate_tokens for prompt length copy."""
    return max(0, int(tokens) * 2)


def clamp_max_tokens(
    prompt: str,
    requested: int,
    *,
    context_window: int,
    system: str = "",
) -> int:
    """Keep prompt + completion inside the model context window."""
    used = estimate_tokens(system) + estimate_tokens(prompt)
    room = int(context_window) - used - 256
    return max(256, min(int(requested), room))
