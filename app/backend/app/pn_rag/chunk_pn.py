"""PN chunking targeting ~4096 tokens (Thai word tokens via existing chunker)."""

from __future__ import annotations

import os

from app.rag.chunking import ChunkingResult, chunk_text


def pn_chunk_text(text: str, *, document_id: str = "") -> ChunkingResult:
    target = int(os.environ.get("PN_CHUNK_TARGET_TOKENS") or 4096)
    overlap = int(os.environ.get("PN_CHUNK_OVERLAP_TOKENS") or 384)
    # Existing chunker uses min/max window; pin both near target for PN.
    max_size = max(256, target)
    min_size = max(128, min(max_size - 64, max_size // 2))
    return chunk_text(
        text,
        document_id=document_id or "pn-doc",
        min_chunk_size=min_size,
        max_chunk_size=max_size,
        overlap_size=min(overlap, max_size // 4),
    )
