"""No-op embeddings when PageIndex / Custom RAG owns retrieval."""

from __future__ import annotations

from app.providers.base import EmbeddingProvider
from app.providers.constants import EMBEDDING_DIMENSIONS


class NoneEmbeddingProvider(EmbeddingProvider):
    """Return zero vectors so ingest/search never call a local embed server."""

    async def embed_query(self, text: str) -> list[float]:
        del text
        return [0.0] * EMBEDDING_DIMENSIONS

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]
