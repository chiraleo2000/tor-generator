"""Retrieval must see handles set during FastAPI lifespan, not the import-time None."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app import infra as runtime
from app.rag import hybrid
from app.rag.retrieval import RetrievalFilter


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
            result, _citations, degraded = await hybrid.hybrid_retrieve(
                "วงเงินเฉพาะเจาะจง",
                search_scope="global",
                section_relevance="s6",
                extra_filter=RetrievalFilter(section_relevance="s6"),
            )
        gvs.assert_called_once()
        filter_arg = store.search.await_args.kwargs.get("filter") or {}
        assert "section_relevance" not in filter_arg
        assert embedding.embed_query.await_args.args[0].startswith("s6")
        gvs.assert_called_once()
        assert gvs.call_args.args[0] is sentinel
        assert result.actual_count == 0
        assert degraded is True
    finally:
        runtime.set_session_factory(previous)


def test_expand_qa_queries_adds_keyword_variant():
    from app.rag.hybrid import expand_qa_queries

    assert expand_qa_queries("") == []
    variants = expand_qa_queries("แบ่งซื้อแบ่งจ้างได้หรือไม่")
    assert variants[0] == "แบ่งซื้อแบ่งจ้างได้หรือไม่"
    assert "แบ่งซื้อแบ่งจ้าง" in variants
    assert expand_qa_queries("วงเงินเฉพาะเจาะจง") == ["วงเงินเฉพาะเจาะจง"]


@pytest.mark.asyncio
async def test_hybrid_retrieve_multi_merges_variant_chunks():
    from app.rag.hybrid import hybrid_retrieve_multi
    from app.rag.retrieval import RetrievalResult, RetrievedChunk

    primary = RetrievedChunk(id="a", text="หลัก", score=0.9)
    extra = RetrievedChunk(id="b", text="เสริม", score=0.8)

    async def fake_primary(query, **_kwargs):
        return (
            RetrievalResult(chunks=[primary], query=query, top_k=10, actual_count=1),
            [],
            False,
        )

    async def fake_local(*_args, **_kwargs):
        return [extra]

    with (
        patch("app.rag.hybrid.hybrid_retrieve", fake_primary),
        patch("app.rag.hybrid._retrieve_local_chunks", fake_local),
    ):
        result, _, degraded = await hybrid_retrieve_multi(
            "แบ่งซื้อได้หรือไม่",
            top_k=10,
        )
    assert [chunk.id for chunk in result.chunks] == ["a", "b"]
    assert degraded is False
