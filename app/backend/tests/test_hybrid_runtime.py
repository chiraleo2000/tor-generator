"""Retrieval must see handles set during FastAPI lifespan, not the import-time None."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import infra as runtime
from app.rag import hybrid


@pytest.mark.asyncio
async def test_hybrid_retrieve_uses_session_factory_set_after_import():
    sentinel = MagicMock(name="live_session_factory")
    previous = runtime.session_factory
    runtime.set_session_factory(sentinel)
    try:
        store = MagicMock()
        store.search = AsyncMock(return_value=[])
        embedding = MagicMock()
        embedding.embed_query = AsyncMock(return_value=[0.1, 0.2])
        with (
            patch.object(hybrid.ProviderFactory, "get_vector_store", return_value=store) as gvs,
            patch.object(hybrid.ProviderFactory, "get_embedding", return_value=embedding),
        ):
            result, _citations, degraded = await hybrid.hybrid_retrieve("วงเงินเฉพาะเจาะจง")
        gvs.assert_called_once()
        assert gvs.call_args.args[0] is sentinel
        assert result.actual_count == 0
        assert degraded is True
    finally:
        runtime.set_session_factory(previous)
