"""Category helpers and ingest_file_bytes with mocked I/O."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.rag.document_pipeline import (
    _category_for,
    _file_type_for,
    _should_extract_legal_graph,
    ingest_file_bytes,
)


def test_category_for_keywords() -> None:
    assert _category_for("พระราชบัญญัติจัดซื้อ.pdf") == "law"
    assert _category_for("กฎกระทรวง.pdf") == "regulation"
    assert _category_for("ระเบียบกระทรวง.pdf") == "regulation"
    assert _category_for("หนังสือกรมบัญชีกลาง.pdf") == "guideline"
    assert _category_for("คู่มือการปฏิบัติ.pdf") == "manual"
    assert _category_for("อื่นๆ.txt") == "other"


def test_file_type_for() -> None:
    assert _file_type_for("application/pdf") == "pdf"
    assert _file_type_for(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ) == "docx"
    assert _file_type_for("text/plain") == "txt"


def test_should_extract_legal_graph() -> None:
    assert _should_extract_legal_graph("baseline") is True
    assert _should_extract_legal_graph("user") is False


@pytest.mark.asyncio
async def test_ingest_file_bytes_success_without_graph() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    store = MagicMock()
    store.put_file.return_value = {"gridfs_id": "g1"}
    factory = MagicMock()
    factory.get_embedding.return_value = MagicMock()
    factory.get_vector_store.return_value = MagicMock()
    with (
        patch("app.rag.document_pipeline.store_from_client", return_value=store),
        patch(
            "app.rag.document_pipeline.write_temp_bytes",
            new_callable=AsyncMock,
            return_value=Path("/tmp/x.pdf"),
        ),
        patch("app.rag.document_pipeline.ingest_document", new_callable=AsyncMock),
        patch("app.rag.document_pipeline.unlink_path", new_callable=AsyncMock),
        patch("app.rag.document_pipeline.ProviderFactory", return_value=factory),
        patch("app.rag.document_pipeline.runtime") as runtime,
    ):
        runtime.mongo_client = MagicMock()
        runtime.neo4j_driver = None
        doc = await ingest_file_bytes(
            db=db,
            filename="คู่มือ.pdf",
            content=b"%PDF",
            mime_type="application/pdf",
            scope="user",
            owner_id=uuid4(),
            session_factory=MagicMock(),
        )
    assert doc.mongo_gridfs_id == "g1"
    assert doc.processing_status == "pending"


@pytest.mark.asyncio
async def test_ingest_file_bytes_marks_failed() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    factory = MagicMock()
    factory.get_embedding.return_value = MagicMock()
    factory.get_vector_store.return_value = MagicMock()
    with (
        patch("app.rag.document_pipeline.store_from_client", return_value=None),
        patch(
            "app.rag.document_pipeline.write_temp_bytes",
            new_callable=AsyncMock,
            return_value=Path("/tmp/x.pdf"),
        ),
        patch(
            "app.rag.document_pipeline.ingest_document",
            new_callable=AsyncMock,
            side_effect=RuntimeError("embed down"),
        ),
        patch("app.rag.document_pipeline.unlink_path", new_callable=AsyncMock),
        patch("app.rag.document_pipeline.ProviderFactory", return_value=factory),
        patch("app.rag.document_pipeline.runtime") as runtime,
    ):
        runtime.mongo_client = None
        doc = await ingest_file_bytes(
            db=db,
            filename="a.pdf",
            content=b"x",
            mime_type="application/pdf",
            scope="baseline",
            session_factory=MagicMock(),
        )
    assert doc.processing_status == "failed"
    assert "embed down" in (doc.error_message or "")


@pytest.mark.asyncio
async def test_ingest_file_bytes_graph_extract() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    factory = MagicMock()
    factory.get_embedding.return_value = MagicMock()
    factory.get_vector_store.return_value = MagicMock()
    factory.get_llm.return_value = MagicMock()
    graph = MagicMock()
    graph.upsert_extraction = AsyncMock()
    with (
        patch("app.rag.document_pipeline.store_from_client", return_value=None),
        patch(
            "app.rag.document_pipeline.write_temp_bytes",
            new_callable=AsyncMock,
            return_value=Path("/tmp/x.pdf"),
        ),
        patch("app.rag.document_pipeline.ingest_document", new_callable=AsyncMock),
        patch("app.rag.document_pipeline.unlink_path", new_callable=AsyncMock),
        patch("app.rag.document_pipeline.ProviderFactory", return_value=factory),
        patch("app.rag.document_pipeline.runtime") as runtime,
        patch("app.rag.extraction.extract_text", return_value=MagicMock(text="กฎหมาย")),
        patch("app.rag.document_pipeline.extract_graph_from_text", new_callable=AsyncMock, return_value=([], [])),
        patch("app.rag.document_pipeline.GraphRAGStore", return_value=graph),
    ):
        runtime.mongo_client = None
        runtime.neo4j_driver = MagicMock()
        doc = await ingest_file_bytes(
            db=db,
            filename="พ.ร.บ..pdf",
            content=b"x",
            mime_type="application/pdf",
            scope="baseline",
            session_factory=MagicMock(),
        )
    assert doc.processing_status == "pending"
    graph.upsert_extraction.assert_awaited()


def test_category_for_prb_short_name() -> None:
    assert _category_for("พรบจัดซื้อ.pdf") == "law"


@pytest.mark.asyncio
async def test_ingest_file_bytes_refresh_and_graph_failures() -> None:
    db = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock(side_effect=RuntimeError("refresh"))
    factory = MagicMock()
    factory.get_embedding.return_value = MagicMock()
    factory.get_vector_store.return_value = MagicMock()
    factory.get_llm.return_value = MagicMock()
    with (
        patch("app.rag.document_pipeline.store_from_client", return_value=None),
        patch(
            "app.rag.document_pipeline.write_temp_bytes",
            new_callable=AsyncMock,
            return_value=Path("/tmp/x.pdf"),
        ),
        patch("app.rag.document_pipeline.ingest_document", new_callable=AsyncMock),
        patch("app.rag.document_pipeline.unlink_path", new_callable=AsyncMock),
        patch("app.rag.document_pipeline.ProviderFactory", return_value=factory),
        patch("app.rag.document_pipeline.runtime") as runtime,
        patch("app.rag.extraction.extract_text", return_value=MagicMock(text="กฎหมาย")),
        patch(
            "app.rag.document_pipeline.extract_graph_from_text",
            new_callable=AsyncMock,
            side_effect=RuntimeError("graph down"),
        ),
    ):
        runtime.mongo_client = None
        runtime.neo4j_driver = MagicMock()
        doc = await ingest_file_bytes(
            db=db,
            filename="พ.ร.บ..pdf",
            content=b"x",
            mime_type="application/pdf",
            scope="baseline",
            session_factory=MagicMock(),
            category="law",
            corpus_group="mandatory_handbook",
        )
    assert doc.processing_status == "pending"
    assert doc.category == "law"
    assert doc.corpus_group == "mandatory_handbook"
