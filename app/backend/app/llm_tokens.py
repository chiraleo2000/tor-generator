"""Shared LLM token budgets for TOR draft, KB Q&A, and TOR review.

OpenAI-compatible APIs expose max_tokens (completion cap), not min_tokens.
Draft uses DRAFT_MIN_TOKENS as a soft floor in substance prompts (not a
verbosity target). KB chat no longer
enforces a minimum length (CHAT_MIN_TOKENS is unused).

google/gemma-4-e4b allows a 131072-token context. Draft and review may request
that full completion budget; clamp_max_tokens still keeps prompt + completion
inside the window. KB chat keeps a smaller completion cap so RAG packing has room.
text-embedding-embeddinggemma-300m allows 2048 input tokens.
"""

from __future__ import annotations

# Local Gemma 4 E4B (LM Studio / SGLang / llama.cpp)
GEMMA_CONTEXT_WINDOW = 131_072
# EmbeddingGemma 300M input cap
EMBEDDING_MAX_TOKENS = 2_048

# Bedrock / PageIndex path: cap completions so Phase 3 cannot sit on one 131k decode.
SECTION_MAX_TOKENS = 8_192
SECTION_MIN_TOKENS = 192
SCOPE_SUB_MAX_TOKENS = 2_048
SCOPE_SUB_MIN_TOKENS = 96
DRAFT_MAX_TOKENS = SECTION_MAX_TOKENS
DRAFT_MIN_TOKENS = SECTION_MIN_TOKENS
CHAT_MAX_TOKENS = 32_768
CHAT_MIN_TOKENS = 0

# Review packs a large TOR + พ.ร.บ./มาตรฐาน + Phase 0 in one user-facing run.
REVIEW_MAX_TOKENS = GEMMA_CONTEXT_WINDOW
REVIEW_CONTEXT_WINDOW = GEMMA_CONTEXT_WINDOW
# Deep analyze pass before JSON/comment — use most of the remaining window.
REVIEW_ANALYZE_MAX_TOKENS = 65_536
# Suggestion JSON needs room for long suggested_text; clamp still protects the window.
REVIEW_SUGGESTION_MAX_TOKENS = 32_768
# Review LLM calls read the full packed TOR + heavy law/standards RAG.
REVIEW_TIMEOUT_SECONDS = 900.0
# Prompt packing budgets (chars ≈ 2× tokens via estimate_tokens).
REVIEW_LEGAL_CONTEXT_CHARS = 90_000
REVIEW_REQUIREMENTS_CHARS = 60_000
REVIEW_CUSTOM_REQUIREMENTS_CHARS = 32_000

DEFAULT_MAX_TOKENS = DRAFT_MAX_TOKENS


def estimate_tokens(text: str) -> int:
    """Conservative Gemma token estimate for mixed Thai/English text."""
    return max(1, (len(text or "") + 1) // 2)


def chars_for_tokens(tokens: int) -> int:
    """Inverse of estimate_tokens for prompt length copy."""
    return max(0, int(tokens) * 2)


def truncate_for_embedding(
    text: str, max_tokens: int = EMBEDDING_MAX_TOKENS
) -> str:
    """Keep embedding input inside EmbeddingGemma's 2048-token window."""
    raw = text or ""
    limit = chars_for_tokens(max_tokens)
    if len(raw) <= limit:
        return raw
    return raw[:limit]


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
