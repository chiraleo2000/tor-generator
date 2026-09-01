"""Multi-query law RAG packing for TOR review."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.rag.law_review import (
    collect_law_review_chunks,
    format_law_chunks,
    law_review_context,
)


@pytest.mark.asyncio
async def test_collect_law_review_chunks_dedupes_and_skips_errors():
    first = SimpleNamespace(id="1", text="มาตรา 8", source_document="พรบ.pdf", page_number=2)
    dup = SimpleNamespace(id="1", text="มาตรา 8")
    second = SimpleNamespace(id="2", text="ราคากลาง", source_document="คู่มือ.pdf", page_number=None)
    calls = {"n": 0}

    async def fake_retrieve(*_args, **_kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("rag down")
        if calls["n"] == 2:
            return SimpleNamespace(chunks=[first]), [], False
        return SimpleNamespace(chunks=[dup, second]), [], False

    with patch("app.rag.law_review.hybrid_retrieve", fake_retrieve):
        out = await collect_law_review_chunks()
    assert [item.id for item in out] == ["1", "2"]

    packed = format_law_chunks(out)
    assert "[พรบ.pdf หน้า 2]" in packed
    assert "มาตรา 8" in packed
    assert "[คู่มือ.pdf]" in packed
    assert format_law_chunks([SimpleNamespace(text="", source_document="x")]) == ""

    with patch(
        "app.rag.law_review.collect_law_review_chunks",
        AsyncMock(return_value=out),
    ):
        assert "ราคากลาง" in await law_review_context()
