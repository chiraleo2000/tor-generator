"""Shared LLM token budgets for TOR draft, KB Q&A, and TOR review.

OpenAI-compatible APIs expose max_tokens (completion cap), not min_tokens.
Draft still uses DRAFT_MIN_TOKENS in section prompts. KB chat no longer
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

DRAFT_MAX_TOKENS = GEMMA_CONTEXT_WINDOW
DRAFT_MIN_TOKENS = 6_144
CHAT_MAX_TOKENS = 32_768
CHAT_MIN_TOKENS = 0

# Review packs a large TOR + พ.ร.บ. + Phase 0 in one user-facing run.
REVIEW_MAX_TOKENS = GEMMA_CONTEXT_WINDOW
REVIEW_CONTEXT_WINDOW = GEMMA_CONTEXT_WINDOW
# Suggestion JSON must stay short; a huge completion cap makes Gemma leave the schema.
REVIEW_SUGGESTION_MAX_TOKENS = 8_192

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
