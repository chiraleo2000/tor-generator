"""Unit tests for RAG ingestion pipeline module.

Tests the orchestration logic of extract -> chunk -> embed -> store,
including per-chunk failure handling, batch processing, and metadata construction.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.ingestion import (
    BatchIngestionResult,
    ChunkFailure,
    IngestionProgress,
    IngestionResult,
    _build_chunk_metadata,
    _generate_chunk_id,
    ingest_batch,
    ingest_document,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def document_id() -> str:
    return "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.fixture
def document_name() -> str:
    return "พ.ร.บ. การจัดซื้อจัดจ้าง 2560"


@pytest.fixture
def mock_embedding_provider() -> AsyncMock:
    """Mock embedding provider that returns a dummy 768-dim vector."""
    provider = AsyncMock()
    provider.embed_query = AsyncMock(return_value=[0.1] * 768)
    provider.embed_documents = AsyncMock(return_value=[[0.1] * 768])
    return provider


@pytest.fixture
def mock_vector_store_provider() -> AsyncMock:
    """Mock vector store provider with successful upsert."""
    provider = AsyncMock()
    provider.upsert = AsyncMock(return_value=None)
    provider.search = AsyncMock(return_value=[])
    provider.delete = AsyncMock(return_value=None)
    return provider


@pytest.fixture
def sample_extraction_result():
    """Create a sample ExtractionResult for patching."""
    from app.rag.extraction import ExtractionResult

    return ExtractionResult(
        text="ข้อ 1 ความเป็นมา การจัดซื้อจัดจ้างภาครัฐเป็นกระบวนการสำคัญ " * 100,
        page_count=3,
        method="direct",
        warnings=[],
    )


@pytest.fixture
def sample_chunking_result(document_id):
    """Create a sample ChunkingResult for patching."""
    from app.rag.chunking import ChunkingResult, ChunkMetadata, TextChunk

    chunks = [
        TextChunk(
            text="ข้อ 1 ความเป็นมา การจัดซื้อจัดจ้างภาครัฐ",
            tokens=["ข้อ", " ", "1", " ", "ความ", "เป็น", "มา"],
            metadata=ChunkMetadata(
                document_id=document_id,
                chunk_index=0,
                section_label="ข้อ 1 ความเป็นมา",
                page_number=1,
            ),
        ),
        TextChunk(
            text="ข้อ 2 วัตถุประสงค์ เพื่อให้การจัดซื้อจัดจ้าง",
            tokens=["ข้อ", " ", "2", " ", "วัตถุประสงค์"],
            metadata=ChunkMetadata(
                document_id=document_id,
                chunk_index=1,
                section_label="ข้อ 2 วัตถุประสงค์",
                page_number=2,
            ),
        ),
        TextChunk(
            text="ข้อ 3 คุณสมบัติ ผู้มีสิทธิเสนอราคา",
            tokens=["ข้อ", " ", "3", " ", "คุณสมบัติ"],
            metadata=ChunkMetadata(
                document_id=document_id,
                chunk_index=2,
                section_label=None,
                page_number=3,
            ),
        ),
    ]
    return ChunkingResult(chunks=chunks, total_tokens=700, document_id=document_id)


# ---------------------------------------------------------------------------
# Test: _generate_chunk_id
# ---------------------------------------------------------------------------


class TestGenerateChunkId:
    """Tests for chunk ID generation."""

    def test_deterministic_output(self, document_id):
        """Same inputs always produce the same chunk ID."""
        id1 = _generate_chunk_id(document_id, 0)
        id2 = _generate_chunk_id(document_id, 0)
        assert id1 == id2

    def test_different_indices_produce_different_ids(self, document_id):
        """Different chunk indices produce different IDs."""
        id0 = _generate_chunk_id(document_id, 0)
        id1 = _generate_chunk_id(document_id, 1)
        assert id0 != id1

    def test_valid_uuid_format(self, document_id):
        """Generated ID is a valid UUID string."""
        chunk_id = _generate_chunk_id(document_id, 5)
        parsed = uuid.UUID(chunk_id)
        assert str(parsed) == chunk_id


# ---------------------------------------------------------------------------
# Test: _build_chunk_metadata
# ---------------------------------------------------------------------------


class TestBuildChunkMetadata:
    """Tests for metadata construction."""

    def test_includes_required_fields(self, sample_chunking_result):
        """Metadata includes document_name, document_id, chunk_index, chunk_text."""
        chunk = sample_chunking_result.chunks[0]
        metadata = _build_chunk_metadata(chunk, "Test Document")

        assert metadata["document_name"] == "Test Document"
        assert metadata["document_id"] == chunk.metadata.document_id
        assert metadata["chunk_index"] == 0
        assert metadata["chunk_text"] == chunk.text

    def test_includes_section_label_when_present(self, sample_chunking_result):
        """Section label is included when the chunk has one."""
        chunk = sample_chunking_result.chunks[0]
        metadata = _build_chunk_metadata(chunk, "Doc")

        assert "section_label" in metadata
        assert metadata["section_label"] == "ข้อ 1 ความเป็นมา"

    def test_excludes_section_label_when_none(self, sample_chunking_result):
        """Section label is excluded when None."""
        chunk = sample_chunking_result.chunks[2]
        metadata = _build_chunk_metadata(chunk, "Doc")

        assert "section_label" not in metadata

    def test_includes_page_number(self, sample_chunking_result):
        """Page number is included when present."""
        chunk = sample_chunking_result.chunks[1]
        metadata = _build_chunk_metadata(chunk, "Doc")

        assert metadata["page_number"] == 2

    def test_merges_extra_metadata(self, sample_chunking_result):
        chunk = sample_chunking_result.chunks[0]
        metadata = _build_chunk_metadata(
            chunk,
            "Doc",
            {"corpus_group": "user", "owner_id": "abc", "scope": "user"},
        )
        assert metadata["corpus_group"] == "user"
        assert metadata["owner_id"] == "abc"
        assert metadata["scope"] == "user"
        assert metadata["source_document"] == "Doc"


# ---------------------------------------------------------------------------
# Test: ingest_document
# ---------------------------------------------------------------------------


class TestIngestDocument:
    """Tests for the single-document ingestion orchestration."""

    @pytest.mark.asyncio
    async def test_successful_ingestion(
        self,
        document_id,
        document_name,
        mock_embedding_provider,
        mock_vector_store_provider,
        sample_extraction_result,
        sample_chunking_result,
    ):
        """Full pipeline succeeds when extraction, chunking, embedding, and upsert all pass."""
        with (
            patch("app.rag.ingestion.extract_text", return_value=sample_extraction_result),
            patch("app.rag.ingestion.chunk_text", return_value=sample_chunking_result),
        ):
            result = await ingest_document(
                document_id=document_id,
                document_name=document_name,
                file_path="/fake/path.pdf",
                mime_type="application/pdf",
                embedding_provider=mock_embedding_provider,
                vector_store_provider=mock_vector_store_provider,
            )

        assert result.success is True
        assert result.total_chunks == 3
        assert result.embedded_chunks == 3
        assert result.failed_chunks == []
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_extraction_failure_returns_failed_result(
        self,
        document_id,
        document_name,
        mock_embedding_provider,
        mock_vector_store_provider,
    ):
        """If text extraction raises, result is failure with appropriate error."""
        with patch(
            "app.rag.ingestion.extract_text",
            side_effect=FileNotFoundError("File not found: /fake.pdf"),
        ):
            result = await ingest_document(
                document_id=document_id,
                document_name=document_name,
                file_path="/fake.pdf",
                mime_type="application/pdf",
                embedding_provider=mock_embedding_provider,
                vector_store_provider=mock_vector_store_provider,
            )

        assert result.success is False
        assert "Text extraction failed" in result.error_message
        assert "FileNotFoundError" in result.error_message

    @pytest.mark.asyncio
    async def test_empty_extraction_returns_failed_result(
        self,
        document_id,
        document_name,
        mock_embedding_provider,
        mock_vector_store_provider,
    ):
        """If extraction returns empty text, result is failure."""
        from app.rag.extraction import ExtractionResult

        empty_result = ExtractionResult(text="   ", page_count=1, method="direct")

        with patch("app.rag.ingestion.extract_text", return_value=empty_result):
            result = await ingest_document(
                document_id=document_id,
                document_name=document_name,
                file_path="/fake.pdf",
                mime_type="application/pdf",
                embedding_provider=mock_embedding_provider,
                vector_store_provider=mock_vector_store_provider,
            )

        assert result.success is False
        assert "empty text" in result.error_message

    @pytest.mark.asyncio
    async def test_chunking_failure_returns_failed_result(
        self,
        document_id,
        document_name,
        mock_embedding_provider,
        mock_vector_store_provider,
        sample_extraction_result,
    ):
        """If chunking raises, result is failure."""
        with (
            patch("app.rag.ingestion.extract_text", return_value=sample_extraction_result),
            patch("app.rag.ingestion.chunk_text", side_effect=RuntimeError("Tokenizer error")),
        ):
            result = await ingest_document(
                document_id=document_id,
                document_name=document_name,
                file_path="/fake.pdf",
                mime_type="application/pdf",
                embedding_provider=mock_embedding_provider,
                vector_store_provider=mock_vector_store_provider,
            )

        assert result.success is False
        assert "Chunking failed" in result.error_message

    @pytest.mark.asyncio
    async def test_partial_embedding_failure_continues(
        self,
        document_id,
        document_name,
        mock_vector_store_provider,
        sample_extraction_result,
        sample_chunking_result,
    ):
        """Req 3.8: If some chunks fail embedding, skip them and continue others."""
        # Embedding fails on chunk index 1, succeeds on 0 and 2
        call_count = 0

        async def embed_with_failure(text):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Second call fails
                raise RuntimeError("Embedding API timeout")
            return [0.1] * 768

        embedding_provider = AsyncMock()
        embedding_provider.embed_query = AsyncMock(side_effect=embed_with_failure)

        with (
            patch("app.rag.ingestion.extract_text", return_value=sample_extraction_result),
            patch("app.rag.ingestion.chunk_text", return_value=sample_chunking_result),
        ):
            result = await ingest_document(
                document_id=document_id,
                document_name=document_name,
                file_path="/fake.pdf",
                mime_type="application/pdf",
                embedding_provider=embedding_provider,
                vector_store_provider=mock_vector_store_provider,
            )

        assert result.success is True
        assert result.total_chunks == 3
        assert result.embedded_chunks == 2
        assert len(result.failed_chunks) == 1
        assert result.failed_chunks[0].chunk_index == 1
        assert "Embedding failed" in result.failed_chunks[0].error

    @pytest.mark.asyncio
    async def test_vector_store_upsert_failure_skips_chunk(
        self,
        document_id,
        document_name,
        mock_embedding_provider,
        sample_extraction_result,
        sample_chunking_result,
    ):
        """If vector store upsert fails for a chunk, skip it and continue."""
        call_count = 0

        async def upsert_with_failure(id, vector, metadata):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # First upsert fails
                raise ConnectionError("DB connection lost")

        vector_store = AsyncMock()
        vector_store.upsert = AsyncMock(side_effect=upsert_with_failure)

        with (
            patch("app.rag.ingestion.extract_text", return_value=sample_extraction_result),
            patch("app.rag.ingestion.chunk_text", return_value=sample_chunking_result),
        ):
            result = await ingest_document(
                document_id=document_id,
                document_name=document_name,
                file_path="/fake.pdf",
                mime_type="application/pdf",
                embedding_provider=mock_embedding_provider,
                vector_store_provider=vector_store,
            )

        assert result.success is True
        assert result.embedded_chunks == 2
        assert len(result.failed_chunks) == 1
        assert "Vector store upsert failed" in result.failed_chunks[0].error

    @pytest.mark.asyncio
    async def test_all_chunks_fail_returns_failure(
        self,
        document_id,
        document_name,
        mock_vector_store_provider,
        sample_extraction_result,
        sample_chunking_result,
    ):
        """If ALL chunks fail embedding, the overall result is failure."""
        embedding_provider = AsyncMock()
        embedding_provider.embed_query = AsyncMock(
            side_effect=RuntimeError("Provider down")
        )

        with (
            patch("app.rag.ingestion.extract_text", return_value=sample_extraction_result),
            patch("app.rag.ingestion.chunk_text", return_value=sample_chunking_result),
        ):
            result = await ingest_document(
                document_id=document_id,
                document_name=document_name,
                file_path="/fake.pdf",
                mime_type="application/pdf",
                embedding_provider=embedding_provider,
                vector_store_provider=mock_vector_store_provider,
            )

        assert result.success is False
        assert result.total_chunks == 3
        assert result.embedded_chunks == 0
        assert len(result.failed_chunks) == 3

    @pytest.mark.asyncio
    async def test_calls_embedding_for_each_chunk(
        self,
        document_id,
        document_name,
        mock_embedding_provider,
        mock_vector_store_provider,
        sample_extraction_result,
        sample_chunking_result,
    ):
        """Embedding provider is called once per chunk with the chunk text."""
        with (
            patch("app.rag.ingestion.extract_text", return_value=sample_extraction_result),
            patch("app.rag.ingestion.chunk_text", return_value=sample_chunking_result),
        ):
            await ingest_document(
                document_id=document_id,
                document_name=document_name,
                file_path="/fake.pdf",
                mime_type="application/pdf",
                embedding_provider=mock_embedding_provider,
                vector_store_provider=mock_vector_store_provider,
            )

        assert mock_embedding_provider.embed_query.call_count == 3
        # Verify texts passed to embed_query
        call_args = [
            call.args[0] for call in mock_embedding_provider.embed_query.call_args_list
        ]
        assert call_args[0] == "ข้อ 1 ความเป็นมา การจัดซื้อจัดจ้างภาครัฐ"
        assert call_args[1] == "ข้อ 2 วัตถุประสงค์ เพื่อให้การจัดซื้อจัดจ้าง"

    @pytest.mark.asyncio
    async def test_upsert_called_with_correct_metadata(
        self,
        document_id,
        document_name,
        mock_embedding_provider,
        mock_vector_store_provider,
        sample_extraction_result,
        sample_chunking_result,
    ):
        """Vector store upsert receives correct metadata including document name and section."""
        with (
            patch("app.rag.ingestion.extract_text", return_value=sample_extraction_result),
            patch("app.rag.ingestion.chunk_text", return_value=sample_chunking_result),
        ):
            await ingest_document(
                document_id=document_id,
                document_name=document_name,
                file_path="/fake.pdf",
                mime_type="application/pdf",
                embedding_provider=mock_embedding_provider,
                vector_store_provider=mock_vector_store_provider,
            )

        assert mock_vector_store_provider.upsert.call_count == 3

        # Check first upsert call metadata
        first_call_kwargs = mock_vector_store_provider.upsert.call_args_list[0].kwargs
        metadata = first_call_kwargs["metadata"]
        assert metadata["document_name"] == document_name
        assert metadata["document_id"] == document_id
        assert metadata["chunk_index"] == 0
        assert metadata["section_label"] == "ข้อ 1 ความเป็นมา"
        assert metadata["page_number"] == 1


# ---------------------------------------------------------------------------
# Test: ingest_batch
# ---------------------------------------------------------------------------


class TestIngestBatch:
    """Tests for the batch ingestion orchestration."""

    @pytest.mark.asyncio
    async def test_processes_all_documents(
        self,
        mock_embedding_provider,
        mock_vector_store_provider,
        sample_extraction_result,
        sample_chunking_result,
    ):
        """Batch processes all documents and returns aggregate results."""
        documents = [
            {
                "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "name": "Doc 1",
                "file_path": "/path/doc1.pdf",
                "mime_type": "application/pdf",
            },
            {
                "id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
                "name": "Doc 2",
                "file_path": "/path/doc2.docx",
                "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            },
        ]

        with (
            patch("app.rag.ingestion.extract_text", return_value=sample_extraction_result),
            patch("app.rag.ingestion.chunk_text", return_value=sample_chunking_result),
        ):
            result = await ingest_batch(
                documents=documents,
                embedding_provider=mock_embedding_provider,
                vector_store_provider=mock_vector_store_provider,
            )

        assert result.total_documents == 2
        assert result.successful_documents == 2
        assert result.failed_documents == 0
        assert len(result.results) == 2

    @pytest.mark.asyncio
    async def test_batch_with_mixed_results(
        self,
        mock_embedding_provider,
        mock_vector_store_provider,
        sample_extraction_result,
        sample_chunking_result,
    ):
        """Batch handles mix of successful and failed documents."""
        documents = [
            {
                "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "name": "Good Doc",
                "file_path": "/path/good.pdf",
                "mime_type": "application/pdf",
            },
            {
                "id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
                "name": "Bad Doc",
                "file_path": "/path/bad.pdf",
                "mime_type": "application/pdf",
            },
        ]

        call_count = 0

        def mock_extract(file_path, mime_type):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise FileNotFoundError("File not found")
            return sample_extraction_result

        with (
            patch("app.rag.ingestion.extract_text", side_effect=mock_extract),
            patch("app.rag.ingestion.chunk_text", return_value=sample_chunking_result),
        ):
            result = await ingest_batch(
                documents=documents,
                embedding_provider=mock_embedding_provider,
                vector_store_provider=mock_vector_store_provider,
            )

        assert result.total_documents == 2
        assert result.successful_documents == 1
        assert result.failed_documents == 1
        assert result.results[0].success is True
        assert result.results[1].success is False

    @pytest.mark.asyncio
    async def test_progress_callback_invoked(
        self,
        mock_embedding_provider,
        mock_vector_store_provider,
        sample_extraction_result,
        sample_chunking_result,
    ):
        """Progress callback is called after each document is processed."""
        documents = [
            {
                "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "name": "Doc 1",
                "file_path": "/path/doc1.pdf",
                "mime_type": "application/pdf",
            },
            {
                "id": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff",
                "name": "Doc 2",
                "file_path": "/path/doc2.pdf",
                "mime_type": "application/pdf",
            },
        ]

        progress_updates: list[IngestionProgress] = []

        def track_progress(progress: IngestionProgress):
            # Store a snapshot of the progress
            progress_updates.append(
                IngestionProgress(
                    total_documents=progress.total_documents,
                    processed_documents=progress.processed_documents,
                    failed_documents=progress.failed_documents,
                    current_document=progress.current_document,
                )
            )

        with (
            patch("app.rag.ingestion.extract_text", return_value=sample_extraction_result),
            patch("app.rag.ingestion.chunk_text", return_value=sample_chunking_result),
        ):
            await ingest_batch(
                documents=documents,
                embedding_provider=mock_embedding_provider,
                vector_store_provider=mock_vector_store_provider,
                progress_callback=track_progress,
            )

        assert len(progress_updates) == 2
        assert progress_updates[0].processed_documents == 1
        assert progress_updates[1].processed_documents == 2
        assert progress_updates[0].total_documents == 2

    @pytest.mark.asyncio
    async def test_empty_batch_returns_zero_results(
        self,
        mock_embedding_provider,
        mock_vector_store_provider,
    ):
        """Empty document list returns zero-count result."""
        result = await ingest_batch(
            documents=[],
            embedding_provider=mock_embedding_provider,
            vector_store_provider=mock_vector_store_provider,
        )

        assert result.total_documents == 0
        assert result.successful_documents == 0
        assert result.failed_documents == 0
        assert result.results == []


# ---------------------------------------------------------------------------
# Test: Database status updates (with mock session)
# ---------------------------------------------------------------------------


class TestDatabaseStatusUpdate:
    """Tests for document status updates via session."""

    @pytest.mark.asyncio
    async def test_status_updated_to_processing_then_completed(
        self,
        document_id,
        document_name,
        mock_embedding_provider,
        mock_vector_store_provider,
        sample_extraction_result,
        sample_chunking_result,
    ):
        """When session is provided, document status is updated through the pipeline."""
        # Create a mock session
        mock_doc = MagicMock()
        mock_doc.processing_status = "pending"
        mock_doc.chunk_count = 0
        mock_doc.error_message = None
        mock_doc.processed_at = None

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_doc)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        with (
            patch("app.rag.ingestion.extract_text", return_value=sample_extraction_result),
            patch("app.rag.ingestion.chunk_text", return_value=sample_chunking_result),
        ):
            result = await ingest_document(
                document_id=document_id,
                document_name=document_name,
                file_path="/fake.pdf",
                mime_type="application/pdf",
                embedding_provider=mock_embedding_provider,
                vector_store_provider=mock_vector_store_provider,
                session=mock_session,
            )

        assert result.success is True
        # Session.get should be called for the status updates
        assert mock_session.get.call_count >= 1
        # Session.commit should be called for status updates
        assert mock_session.commit.call_count >= 1

    @pytest.mark.asyncio
    async def test_status_set_to_failed_on_extraction_error(
        self,
        document_id,
        document_name,
        mock_embedding_provider,
        mock_vector_store_provider,
    ):
        """When extraction fails, document status is set to failed."""
        mock_doc = MagicMock()
        mock_doc.processing_status = "pending"

        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_doc)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        with patch(
            "app.rag.ingestion.extract_text",
            side_effect=FileNotFoundError("not found"),
        ):
            result = await ingest_document(
                document_id=document_id,
                document_name=document_name,
                file_path="/fake.pdf",
                mime_type="application/pdf",
                embedding_provider=mock_embedding_provider,
                vector_store_provider=mock_vector_store_provider,
                session=mock_session,
            )

        assert result.success is False
        # The doc should have been set to "failed" status
        assert mock_doc.processing_status == "failed"
        assert mock_doc.error_message is not None


def test_unmapped_filename_category_is_other():
    from app.rag.document_pipeline import _category_for

    assert _category_for("บันทึกภายใน.txt") == "other"
    assert _category_for("พระราชบัญญัติ.pdf") == "law"
