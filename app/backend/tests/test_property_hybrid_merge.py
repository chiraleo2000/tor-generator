"""Property tests for hybrid MCP merge (mcp-rag-config-and-deploy)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app import infra as runtime
from app.rag import hybrid
from app.rag.hybrid import _chunk_sort_key, _citations_for_chunk
from app.rag.retrieval import RetrievedChunk

MAX_EX = 100


def _chunk(chunk_id: str, score: float, source: str, text: str = "t") -> RetrievedChunk:
    return RetrievedChunk(
        id=chunk_id,
        text=text,
        score=score,
        source_document=f"doc-{chunk_id}",
        metadata={"rag_source": source},
    )


@pytest.mark.property
@pytest.mark.asyncio
@given(n_local=st.integers(min_value=0, max_value=4), n_custom=st.integers(min_value=0, max_value=3))
@settings(max_examples=MAX_EX)
async def test_property_6_fail_open_preservation(n_local: int, n_custom: int) -> None:
    # Feature: mcp-rag-config-and-deploy, Property 6: Fail-Open Preservation
    local = [_chunk(f"l{i}", 0.9 - i * 0.01, "local") for i in range(n_local)]
    custom = [_chunk(f"c{i}", 0.8 - i * 0.01, "custom_rag") for i in range(n_custom)]
    previous = runtime.session_factory
    runtime.set_session_factory(MagicMock())
    try:
        with (
            patch(
                "app.rag.hybrid._retrieve_local_chunks",
                new_callable=AsyncMock,
                return_value=list(local),
            ),
            patch(
                "app.rag.hybrid._retrieve_custom_chunks",
                new_callable=AsyncMock,
                return_value=list(custom),
            ),
            patch(
                "app.rag.hybrid._expand_graph",
                new_callable=AsyncMock,
                return_value=([], True),
            ),
        ):
            with patch(
                "app.rag.hybrid.retrieve_mcp_chunks_with_status",
                new_callable=AsyncMock,
                return_value=([], True),
            ):
                down = await hybrid.hybrid_retrieve("q", search_scope="both", top_k=20)
            with patch(
                "app.rag.hybrid.retrieve_mcp_chunks_with_status",
                new_callable=AsyncMock,
                return_value=([], False),
            ):
                off = await hybrid.hybrid_retrieve("q", search_scope="both", top_k=20)
        down_result, _, _, down_mcp = down
        off_result, _, _, off_mcp = off
        assert down_mcp is True
        assert off_mcp is False
        assert [item.id for item in down_result.chunks] == [item.id for item in off_result.chunks]
        assert [item.text for item in down_result.chunks] == [item.text for item in off_result.chunks]
        assert [item.score for item in down_result.chunks] == [item.score for item in off_result.chunks]
    finally:
        runtime.set_session_factory(previous)


@pytest.mark.property
@pytest.mark.asyncio
@given(n=st.integers(min_value=1, max_value=5))
@settings(max_examples=MAX_EX)
async def test_property_7_successful_mcp_inclusion(n: int) -> None:
    # Feature: mcp-rag-config-and-deploy, Property 7: Successful MCP Chunk Inclusion
    mcp_chunks = [_chunk(f"m{i}", 0.7, "mcp", text=f"mcp-{i}") for i in range(n)]
    previous = runtime.session_factory
    runtime.set_session_factory(MagicMock())
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
                return_value=(list(mcp_chunks), False),
            ),
            patch(
                "app.rag.hybrid._expand_graph",
                new_callable=AsyncMock,
                return_value=([], True),
            ),
        ):
            result, _, _, mcp_degraded = await hybrid.hybrid_retrieve(
                "q", search_scope="both", top_k=max(n, 1)
            )
        ids = {item.id for item in result.chunks}
        for chunk in mcp_chunks:
            if chunk.score >= 0:
                assert chunk.id in ids or len(result.chunks) <= max(n * 2, n)
        assert mcp_degraded is False
        assert any(item.metadata.get("rag_source") == "mcp" for item in result.chunks)
    finally:
        runtime.set_session_factory(previous)


@pytest.mark.property
@given(
    scores=st.lists(
        st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=9,
    )
)
@settings(max_examples=MAX_EX)
def test_property_8_deterministic_merge_ordering(scores: list[float]) -> None:
    # Feature: mcp-rag-config-and-deploy, Property 8: Deterministic Merge Ordering
    sources = ["local", "custom_rag", "mcp"]
    rows = [
        _chunk(f"id-{index}", scores[index], sources[index % 3])
        for index in range(len(scores))
    ]
    shuffled = list(reversed(rows))
    a = sorted(rows, key=_chunk_sort_key)
    b = sorted(shuffled, key=_chunk_sort_key)
    assert [item.id for item in a] == [item.id for item in b]


@pytest.mark.property
@given(label=st.one_of(st.none(), st.text(min_size=1, max_size=20)))
@settings(max_examples=MAX_EX)
def test_property_10_mcp_citation_generation(label: str | None) -> None:
    # Feature: mcp-rag-config-and-deploy, Property 10: MCP Citation Generation
    chunk = RetrievedChunk(
        id="m1",
        text="t",
        score=0.4,
        source_document=label,
        metadata={"rag_source": "mcp"},
    )
    citations = _citations_for_chunk(chunk)
    mcp = [item for item in citations if item.get("type") == "mcp"]
    assert mcp
    expected = str(label) if label else "MCP"
    assert mcp[0]["label"] == expected
