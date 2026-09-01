"""Incremental mandatory corpus sync."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.domain.corpus import GROUP_MANDATORY_RAW, CorpusFile
from app.rag.seed_corpus import (
    sha256_bytes,
    sync_mandatory_sources,
    wipe_baseline_documents,
)


def test_sha256_bytes_is_stable():
    first = sha256_bytes(b"abc")
    second = sha256_bytes(b"abc")
    assert first == second
    assert first != sha256_bytes(b"abd")


@pytest.mark.asyncio
async def test_wipe_baseline_documents_noop_when_empty():
    db = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    db.execute = AsyncMock(return_value=result)
    assert await wipe_baseline_documents(db) == 0
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_wipe_baseline_documents_deletes_ids():
    db = AsyncMock()
    result = MagicMock()
    result.all.return_value = [("doc-1",), ("doc-2",)]
    db.execute = AsyncMock(return_value=result)
    assert await wipe_baseline_documents(db) == 2
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_sync_returns_empty_when_no_pdfs(monkeypatch):
    monkeypatch.setattr("app.rag.seed_corpus.list_mandatory_sources", lambda: [])
    stats = await sync_mandatory_sources(AsyncMock(), MagicMock())
    assert stats.as_dict()["ingested"] == 0
    assert stats.skipped == 0


@pytest.mark.asyncio
async def test_sync_skips_existing_hash(tmp_path, monkeypatch):
    pdf = tmp_path / "พรบ.pdf"
    data = b"%PDF-1.4 skip"
    pdf.write_bytes(data)
    item = CorpusFile(path=pdf, group=GROUP_MANDATORY_RAW)
    monkeypatch.setattr("app.rag.seed_corpus.list_mandatory_sources", lambda: [item])

    async def existing(_db):
        return {pdf.name}, {sha256_bytes(data)}

    db = AsyncMock()
    db.commit = AsyncMock()
    with patch("app.rag.seed_corpus._existing_baseline", existing):
        stats = await sync_mandatory_sources(db, MagicMock())
    assert stats.skipped == 1
    assert pdf.name in stats.skipped_names


@pytest.mark.asyncio
async def test_sync_ingests_new_pdf(tmp_path, monkeypatch):
    pdf = tmp_path / "ระเบียบ.pdf"
    pdf.write_bytes(b"%PDF-1.4 new")
    item = CorpusFile(path=pdf, group=GROUP_MANDATORY_RAW)
    monkeypatch.setattr("app.rag.seed_corpus.list_mandatory_sources", lambda: [item])
    doc = SimpleNamespace(processing_status="ready", chunk_count=4, error_message=None)

    async def existing(_db):
        return set(), set()

    db = AsyncMock()
    db.commit = AsyncMock()
    with (
        patch("app.rag.seed_corpus._existing_baseline", existing),
        patch("app.rag.seed_corpus.ingest_file_bytes", AsyncMock(return_value=doc)),
    ):
        stats = await sync_mandatory_sources(db, MagicMock())
    assert stats.ingested == 1
    assert stats.ingested_names == [pdf.name]


@pytest.mark.asyncio
async def test_sync_records_failed_status_and_read_error(tmp_path, monkeypatch):
    missing = CorpusFile(path=tmp_path / "missing.pdf", group=GROUP_MANDATORY_RAW)
    pdf = tmp_path / "fail.pdf"
    pdf.write_bytes(b"%PDF-1.4 fail")
    failed_item = CorpusFile(path=pdf, group=GROUP_MANDATORY_RAW)
    monkeypatch.setattr(
        "app.rag.seed_corpus.list_mandatory_sources",
        lambda: [missing, failed_item],
    )
    doc = SimpleNamespace(processing_status="failed", chunk_count=0, error_message="bad pdf")

    async def existing(_db):
        return set(), set()

    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    with (
        patch("app.rag.seed_corpus._existing_baseline", existing),
        patch("app.rag.seed_corpus.ingest_file_bytes", AsyncMock(return_value=doc)),
    ):
        stats = await sync_mandatory_sources(db, MagicMock())
    assert stats.failed == 2
    assert "missing.pdf" in stats.failed_names
    assert "fail.pdf" in stats.failed_names


@pytest.mark.asyncio
async def test_sync_rolls_back_on_ingest_exception(tmp_path, monkeypatch):
    pdf = tmp_path / "boom.pdf"
    pdf.write_bytes(b"%PDF-1.4 boom")
    item = CorpusFile(path=pdf, group=GROUP_MANDATORY_RAW)
    monkeypatch.setattr("app.rag.seed_corpus.list_mandatory_sources", lambda: [item])

    async def existing(_db):
        return set(), set()

    db = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    with (
        patch("app.rag.seed_corpus._existing_baseline", existing),
        patch(
            "app.rag.seed_corpus.ingest_file_bytes",
            AsyncMock(side_effect=RuntimeError("ingest down")),
        ),
    ):
        stats = await sync_mandatory_sources(db, MagicMock())
    assert stats.failed == 1
    db.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_sync_wipe_baseline_and_graph(tmp_path, monkeypatch):
    pdf = tmp_path / "keep.pdf"
    pdf.write_bytes(b"%PDF-1.4 keep")
    item = CorpusFile(path=pdf, group=GROUP_MANDATORY_RAW)
    monkeypatch.setattr("app.rag.seed_corpus.list_mandatory_sources", lambda: [item])

    async def existing(_db):
        return {pdf.name}, {sha256_bytes(b"%PDF-1.4 keep")}

    db = AsyncMock()
    db.commit = AsyncMock()
    store = MagicMock()
    store.wipe = AsyncMock()
    with (
        patch("app.rag.seed_corpus.wipe_baseline_documents", AsyncMock(return_value=3)),
        patch("app.rag.seed_corpus._existing_baseline", existing),
        patch("app.rag.seed_corpus.GraphRAGStore", return_value=store),
    ):
        stats = await sync_mandatory_sources(
            db, MagicMock(), wipe_baseline=True, neo4j_driver=object()
        )
    assert stats.skipped == 1
    store.wipe.assert_awaited()


@pytest.mark.asyncio
async def test_sync_wipe_skips_neo4j_errors(tmp_path, monkeypatch):
    pdf = tmp_path / "keep.pdf"
    pdf.write_bytes(b"%PDF-1.4 keep")
    item = CorpusFile(path=pdf, group=GROUP_MANDATORY_RAW)
    monkeypatch.setattr("app.rag.seed_corpus.list_mandatory_sources", lambda: [item])

    async def existing(_db):
        return {pdf.name}, {sha256_bytes(b"%PDF-1.4 keep")}

    db = AsyncMock()
    db.commit = AsyncMock()
    store = MagicMock()
    store.wipe = AsyncMock(side_effect=RuntimeError("neo4j down"))
    with (
        patch("app.rag.seed_corpus.wipe_baseline_documents", AsyncMock(return_value=1)),
        patch("app.rag.seed_corpus._existing_baseline", existing),
        patch("app.rag.seed_corpus.GraphRAGStore", return_value=store),
    ):
        stats = await sync_mandatory_sources(
            db, MagicMock(), wipe_baseline=True, neo4j_driver=object()
        )
    assert stats.skipped == 1
