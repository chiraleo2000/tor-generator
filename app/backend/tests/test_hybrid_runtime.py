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
            patch(
                "app.rag.hybrid.retrieve_mcp_chunks_with_status",
                new_callable=AsyncMock,
                return_value=([], False),
            ),
            patch(
                "app.rag.hybrid._retrieve_custom_chunks",
                new_callable=AsyncMock,
                return_value=[],
            ),
        ):
            result, _citations, degraded, mcp_degraded = await hybrid.hybrid_retrieve(
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
        assert mcp_degraded is False
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
        result, _, degraded, mcp_degraded = await hybrid_retrieve_multi(
            "แบ่งซื้อได้หรือไม่",
            top_k=10,
        )
    assert [chunk.id for chunk in result.chunks] == ["a", "b"]
    assert degraded is False
    assert mcp_degraded is False


@pytest.mark.asyncio
async def test_hybrid_retrieve_multi_surfaces_mcp_degraded_true():
    from app.rag.hybrid import hybrid_retrieve_multi
    from app.rag.retrieval import RetrievalResult, RetrievedChunk

    local = RetrievedChunk(
        id="local-1",
        text="local",
        score=0.8,
        metadata={"rag_source": "local"},
    )

    async def fake_primary(query, **_kwargs):
        return (
            RetrievalResult(chunks=[local], query=query, top_k=5, actual_count=1),
            [],
            False,
            True,
        )

    with (
        patch("app.rag.hybrid.hybrid_retrieve", fake_primary),
        patch("app.rag.hybrid.expand_qa_queries", return_value=["วงเงิน"]),
    ):
        result, _, _, mcp_degraded = await hybrid_retrieve_multi("วงเงิน", top_k=5)
    assert mcp_degraded is True
    assert [chunk.id for chunk in result.chunks] == ["local-1"]


@pytest.mark.asyncio
async def test_hybrid_sort_is_deterministic_on_tied_scores():
    from app.rag.hybrid import _chunk_sort_key
    from app.rag.retrieval import RetrievedChunk

    local = RetrievedChunk(
        id="b-local", text="l", score=0.5, metadata={"rag_source": "local"}
    )
    custom = RetrievedChunk(
        id="a-custom", text="c", score=0.5, metadata={"rag_source": "custom_rag"}
    )
    mcp = RetrievedChunk(
        id="c-mcp", text="m", score=0.5, metadata={"rag_source": "mcp"}
    )
    rows = [mcp, custom, local]
    rows.sort(key=_chunk_sort_key)
    assert [item.id for item in rows] == ["b-local", "a-custom", "c-mcp"]


def test_apply_mcp_hits_tags_matching_local_and_keeps_extras():
    from app.rag.hybrid import _apply_mcp_hits
    from app.rag.retrieval import RetrievedChunk

    local = RetrievedChunk(
        id="local-1",
        text="วิธีเฉพาะเจาะจง",
        score=0.9,
        source_document="ระเบียบ.pdf",
        metadata={"rag_source": "local"},
    )
    other = RetrievedChunk(id="local-2", text="อื่น", score=0.4)
    mcp_same = RetrievedChunk(
        id="mcp-1",
        text="วิธีเฉพาะเจาะจง",
        score=0.88,
        source_document="ระเบียบ.pdf",
        metadata={"rag_source": "mcp", "mcp_server": "local-pgvector-mcp"},
    )
    mcp_extra = RetrievedChunk(
        id="mcp-2",
        text="ชิ้นจากหน่วยงาน",
        score=0.5,
        source_document="agency",
        metadata={"rag_source": "mcp", "mcp_server": "agency-legal-mcp"},
    )
    merged = _apply_mcp_hits([local, other], [mcp_same, mcp_extra])
    assert merged[0].metadata.get("rag_source") == "mcp"
    assert merged[0].metadata.get("mcp_server") == "local-pgvector-mcp"
    assert merged[0].id == "local-1"
    assert merged[1].id == "local-2"
    assert merged[2].id == "mcp-2"


@pytest.mark.asyncio
async def test_hybrid_retrieve_fail_open_when_local_embedding_raises():
    from app.rag.retrieval import RetrievedChunk

    previous = runtime.session_factory
    runtime.set_session_factory(MagicMock(name="live_session_factory"))
    mcp_chunk = RetrievedChunk(
        id="mcp-1",
        text="mcp",
        score=0.4,
        source_document="mcp-retrieve-stub",
        metadata={"rag_source": "mcp"},
    )
    embedding = MagicMock()
    embedding.embed_query = AsyncMock(side_effect=RuntimeError("invalid model"))
    try:
        with (
            patch.object(hybrid.ProviderFactory, "get_vector_store", return_value=MagicMock()),
            patch.object(hybrid.ProviderFactory, "get_embedding", return_value=embedding),
            patch(
                "app.rag.hybrid.retrieve_mcp_chunks_with_status",
                new_callable=AsyncMock,
                return_value=([mcp_chunk], False),
            ),
            patch("app.rag.hybrid._retrieve_custom_chunks", new_callable=AsyncMock, return_value=[]),
        ):
            result, citations, _graph, mcp_degraded = await hybrid.hybrid_retrieve(
                "วงเงิน",
                search_scope="global",
            )
        assert result.actual_count == 1
        assert result.chunks[0].id == "mcp-1"
        assert mcp_degraded is False
        assert any(item.get("type") == "mcp" for item in citations)
    finally:
        runtime.set_session_factory(previous)


@pytest.mark.asyncio
async def test_hybrid_retrieve_surfaces_mcp_degraded_true():
    from app.rag.retrieval import RetrievedChunk

    previous = runtime.session_factory
    runtime.set_session_factory(MagicMock(name="live_session_factory"))
    local = RetrievedChunk(
        id="local-1",
        text="local",
        score=0.8,
        metadata={"rag_source": "local"},
    )
    try:
        with (
            patch(
                "app.rag.hybrid._retrieve_local_chunks",
                new_callable=AsyncMock,
                return_value=[local],
            ),
            patch(
                "app.rag.hybrid._retrieve_custom_chunks",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.rag.hybrid.retrieve_mcp_chunks_with_status",
                new_callable=AsyncMock,
                return_value=([], True),
            ),
            patch(
                "app.rag.hybrid._expand_graph",
                new_callable=AsyncMock,
                return_value=([], True),
            ),
        ):
            degraded_run = await hybrid.hybrid_retrieve("วงเงิน", search_scope="global")
            with patch(
                "app.rag.hybrid.retrieve_mcp_chunks_with_status",
                new_callable=AsyncMock,
                return_value=([], False),
            ):
                disabled_run = await hybrid.hybrid_retrieve(
                    "วงเงิน", search_scope="global"
                )
        result, _citations, _graph, mcp_degraded = degraded_run
        other, _, _, other_mcp = disabled_run
        assert mcp_degraded is True
        assert other_mcp is False
        assert [chunk.id for chunk in result.chunks] == [chunk.id for chunk in other.chunks]
        assert [chunk.text for chunk in result.chunks] == [chunk.text for chunk in other.chunks]
    finally:
        runtime.set_session_factory(previous)


@pytest.mark.asyncio
async def test_hybrid_retrieve_mcp_exception_sets_degraded():
    previous = runtime.session_factory
    runtime.set_session_factory(MagicMock(name="live_session_factory"))
    try:
        with (
            patch(
                "app.rag.hybrid._retrieve_local_chunks",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.rag.hybrid._retrieve_custom_chunks",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "app.rag.hybrid.retrieve_mcp_chunks_with_status",
                new_callable=AsyncMock,
                side_effect=RuntimeError("mcp boom"),
            ),
            patch(
                "app.rag.hybrid._expand_graph",
                new_callable=AsyncMock,
                return_value=([], True),
            ),
        ):
            result, _citations, _graph, mcp_degraded = await hybrid.hybrid_retrieve(
                "",
                search_scope="both",
            )
        assert result.chunks == []
        assert mcp_degraded is True
    finally:
        runtime.set_session_factory(previous)

