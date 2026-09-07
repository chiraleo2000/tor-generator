"""None embedding provider (PageIndex owns retrieval)."""

import pytest

from app.providers.constants import EMBEDDING_DIMENSIONS
from app.providers.embedding.none_provider import NoneEmbeddingProvider


@pytest.mark.asyncio
async def test_none_embedding_returns_zero_vectors() -> None:
    provider = NoneEmbeddingProvider()
    query = await provider.embed_query("ทดสอบ")
    docs = await provider.embed_documents(["ก", "ข"])
    assert query == [0.0] * EMBEDDING_DIMENSIONS
    assert docs == [[0.0] * EMBEDDING_DIMENSIONS, [0.0] * EMBEDDING_DIMENSIONS]
