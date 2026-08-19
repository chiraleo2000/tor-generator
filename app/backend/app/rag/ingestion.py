"""RAG ingestion pipeline — orchestrates extraction, chunking, embedding, and vector store upsert.

Processes KnowledgeBaseDocument records through the full pipeline:
  1. Text extraction (PDF/DOCX/TXT via extraction module)
  2. Thai-aware chunking (via chunking module)
  3. Embedding generation (via configured EmbeddingProvider)
  4. Vector store upsert (via configured VectorStoreProvider)

Handles embedding failures per-chunk: skips failed chunks, logs the failure,
and continues processing remaining chunks. Updates KnowledgeBaseDocument
processing_status and chunk_count in the database.

Requirements: 3.3, 3.7, 3.8
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

from app.rag.chunking import ChunkingResult, TextChunk, chunk_text
from app.rag.extraction import ExtractionResult, extract_text

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.providers.base import EmbeddingProvider, VectorStoreProvider

logger = logging.getLogger(__name__)


@dataclass
class ChunkFailure:
    """Records a failed embedding attempt for a single chunk.

    Attributes:
        chunk_index: Zero-based index of the chunk that failed.
        document_id: Identifier of the source document.
        error: Description of the failure.
    """

    chunk_index: int
    document_id: str
    error: str


@dataclass
class IngestionProgress:
    """Tracks progress of a batch ingestion operation.

    Attributes:
        total_documents: Total documents to process.
        processed_documents: Documents fully processed so far.
        failed_documents: Documents that failed processing.
        current_document: Name of the document currently being processed.
    """

    total_documents: int = 0
    processed_documents: int = 0
    failed_documents: int = 0
    current_document: str = ""


@dataclass
class IngestionResult:
    """Result of ingesting a single document.

    Attributes:
        document_id: The document's UUID.
        document_name: Human-readable document name.
        success: Whether the overall ingestion succeeded.
        total_chunks: Total chunks produced from the document.
        embedded_chunks: Number of chunks successfully embedded and stored.
        failed_chunks: List of ChunkFailure records for chunks that failed.
        error_message: Top-level error message if the entire ingestion failed.
    """

    document_id: str
    document_name: str
    success: bool
    total_chunks: int = 0
    embedded_chunks: int = 0
    failed_chunks: list[ChunkFailure] = field(default_factory=list)
    error_message: str | None = None


@dataclass
class BatchIngestionResult:
    """Result of a batch ingestion operation across multiple documents.

    Attributes:
        total_documents: Total documents attempted.
        successful_documents: Documents that completed successfully.
        failed_documents: Documents that failed entirely.
        results: Per-document ingestion results.
    """

    total_documents: int = 0
    successful_documents: int = 0
    failed_documents: int = 0
    results: list[IngestionResult] = field(default_factory=list)


async def ingest_document(
    document_id: str,
    document_name: str,
    file_path: str,
    mime_type: str,
    embedding_provider: "EmbeddingProvider",
    vector_store_provider: "VectorStoreProvider",
    session: "AsyncSession | None" = None,
    extra_metadata: dict | None = None,
) -> IngestionResult:
    """Ingest a single document through the full RAG pipeline.

    Orchestrates: extraction -> chunking -> embedding -> vector store upsert.
    Handles per-chunk embedding failures gracefully (Req 3.8).

    Args:
        document_id: UUID string of the KnowledgeBaseDocument.
        document_name: Human-readable document name (used in metadata).
        file_path: Path to the document file on disk/storage.
        mime_type: MIME type of the document file.
        embedding_provider: Configured embedding provider instance.
        vector_store_provider: Configured vector store provider instance.
        session: Optional SQLAlchemy async session for updating document status.

    Returns:
        IngestionResult with details about the ingestion outcome.
    """
    logger.info("Starting ingestion for document: %s (id=%s)", document_name, document_id)

    # Update status to processing
    if session:
        await _update_document_status(session, document_id, "processing")

    # Step 1: Extract text
    try:
        extraction_result: ExtractionResult = extract_text(file_path, mime_type)
    except Exception as e:
        error_msg = f"Text extraction failed: {type(e).__name__}: {e}"
        logger.error("Extraction failed for document %s: %s", document_id, error_msg)
        if session:
            await _update_document_status(
                session, document_id, "failed", error_message=error_msg
            )
        return IngestionResult(
            document_id=document_id,
            document_name=document_name,
            success=False,
            error_message=error_msg,
        )

    if not extraction_result.text.strip():
        error_msg = "Extraction produced empty text"
        logger.warning("Document %s produced no text after extraction", document_id)
        if session:
            await _update_document_status(
                session, document_id, "failed", error_message=error_msg
            )
        return IngestionResult(
            document_id=document_id,
            document_name=document_name,
            success=False,
            error_message=error_msg,
        )

    # Step 2: Chunk text (Thai-aware)
    try:
        chunking_result: ChunkingResult = chunk_text(
            text=extraction_result.text,
            document_id=document_id,
        )
    except Exception as e:
        error_msg = f"Chunking failed: {type(e).__name__}: {e}"
        logger.error("Chunking failed for document %s: %s", document_id, error_msg)
        if session:
            await _update_document_status(
                session, document_id, "failed", error_message=error_msg
            )
        return IngestionResult(
            document_id=document_id,
            document_name=document_name,
            success=False,
            error_message=error_msg,
        )

    if not chunking_result.chunks:
        error_msg = "Chunking produced no chunks"
        logger.warning("Document %s produced no chunks after text chunking", document_id)
        if session:
            await _update_document_status(
                session, document_id, "failed", error_message=error_msg
            )
        return IngestionResult(
            document_id=document_id,
            document_name=document_name,
            success=False,
            error_message=error_msg,
        )

    # Step 3 & 4: Embed and upsert each chunk
    total_chunks = len(chunking_result.chunks)
    embedded_count = 0
    failed_chunks: list[ChunkFailure] = []

    for chunk in chunking_result.chunks:
        chunk_id = _generate_chunk_id(document_id, chunk.metadata.chunk_index)

        # Step 3: Generate embedding for this chunk
        try:
            embedding = await embedding_provider.embed_query(chunk.text)
        except Exception as e:
            # Req 3.8: Skip failed chunk, log failure, continue
            failure = ChunkFailure(
                chunk_index=chunk.metadata.chunk_index,
                document_id=document_id,
                error=f"Embedding failed: {type(e).__name__}: {e}",
            )
            failed_chunks.append(failure)
            logger.warning(
                "Embedding failed for chunk %d of document %s: %s",
                chunk.metadata.chunk_index,
                document_id,
                str(e),
            )
            continue

        # Step 4: Upsert into vector store with metadata
        metadata = _build_chunk_metadata(chunk, document_name, extra_metadata)

        try:
            await vector_store_provider.upsert(
                id=chunk_id,
                vector=embedding,
                metadata=metadata,
            )
            embedded_count += 1
        except Exception as e:
            # Treat vector store upsert failure same as embedding failure
            failure = ChunkFailure(
                chunk_index=chunk.metadata.chunk_index,
                document_id=document_id,
                error=f"Vector store upsert failed: {type(e).__name__}: {e}",
            )
            failed_chunks.append(failure)
            logger.warning(
                "Vector store upsert failed for chunk %d of document %s: %s",
                chunk.metadata.chunk_index,
                document_id,
                str(e),
            )
            continue

    # Determine success: at least one chunk was embedded
    success = embedded_count > 0

    # Update document status in database
    if session:
        if success:
            await _update_document_status(
                session,
                document_id,
                "completed",
                chunk_count=embedded_count,
            )
        else:
            error_msg = (
                f"All {total_chunks} chunks failed embedding/storage. "
                f"First failure: {failed_chunks[0].error if failed_chunks else 'unknown'}"
            )
            await _update_document_status(
                session, document_id, "failed", error_message=error_msg
            )

    if failed_chunks:
        logger.info(
            "Document %s: %d/%d chunks embedded, %d failed",
            document_id,
            embedded_count,
            total_chunks,
            len(failed_chunks),
        )

    return IngestionResult(
        document_id=document_id,
        document_name=document_name,
        success=success,
        total_chunks=total_chunks,
        embedded_chunks=embedded_count,
        failed_chunks=failed_chunks,
        error_message=None if success else "All chunks failed embedding/storage",
    )


async def ingest_batch(
    documents: list[dict],
    embedding_provider: "EmbeddingProvider",
    vector_store_provider: "VectorStoreProvider",
    session: "AsyncSession | None" = None,
    progress_callback: Callable[[IngestionProgress], None] | None = None,
) -> BatchIngestionResult:
    """Process a batch of documents through the ingestion pipeline.

    Each document dict should contain:
        - id: str (UUID)
        - name: str
        - file_path: str
        - mime_type: str

    Processes documents sequentially and reports progress via callback.
    Req 3.7: Batch ingestion endpoint that processes full knowledge base.

    Args:
        documents: List of document dicts with id, name, file_path, mime_type.
        embedding_provider: Configured embedding provider instance.
        vector_store_provider: Configured vector store provider instance.
        session: Optional SQLAlchemy async session.
        progress_callback: Optional callback invoked after each document completes.

    Returns:
        BatchIngestionResult summarizing the entire batch operation.
    """
    total = len(documents)
    progress = IngestionProgress(total_documents=total)
    results: list[IngestionResult] = []
    successful = 0
    failed = 0

    logger.info("Starting batch ingestion of %d documents", total)

    for doc in documents:
        doc_id = doc["id"]
        doc_name = doc["name"]
        file_path = doc["file_path"]
        mime_type = doc["mime_type"]

        progress.current_document = doc_name

        result = await ingest_document(
            document_id=doc_id,
            document_name=doc_name,
            file_path=file_path,
            mime_type=mime_type,
            embedding_provider=embedding_provider,
            vector_store_provider=vector_store_provider,
            session=session,
        )

        results.append(result)

        if result.success:
            successful += 1
        else:
            failed += 1

        progress.processed_documents = successful + failed
        progress.failed_documents = failed

        if progress_callback:
            progress_callback(progress)

    logger.info(
        "Batch ingestion complete: %d/%d successful, %d failed",
        successful,
        total,
        failed,
    )

    return BatchIngestionResult(
        total_documents=total,
        successful_documents=successful,
        failed_documents=failed,
        results=results,
    )


def _generate_chunk_id(document_id: str, chunk_index: int) -> str:
    """Generate a deterministic unique ID for a chunk.

    Uses UUID5 with the document_id as namespace and chunk_index as name,
    ensuring the same chunk always gets the same ID (idempotent upserts).

    Args:
        document_id: The parent document's UUID string.
        chunk_index: Zero-based index of the chunk.

    Returns:
        A UUID string for the chunk.
    """
    namespace = uuid.UUID(document_id) if isinstance(document_id, str) else document_id
    return str(uuid.uuid5(namespace, str(chunk_index)))


def _build_chunk_metadata(
    chunk: TextChunk, document_name: str, extra: dict | None = None
) -> dict:
    """Build metadata dict for a chunk to be stored in the vector store.

    Req 3.3: Metadata includes source document name, section, page number.
    """
    metadata = {
        "document_id": chunk.metadata.document_id,
        "document_name": document_name,
        "chunk_index": chunk.metadata.chunk_index,
        "chunk_text": chunk.text,
        "source_document": document_name,
    }

    if chunk.metadata.section_label:
        metadata["section_label"] = chunk.metadata.section_label

    if chunk.metadata.page_number is not None:
        metadata["page_number"] = chunk.metadata.page_number

    if extra:
        for key, value in extra.items():
            if value is not None:
                metadata[key] = value

    return metadata


async def _update_document_status(
    session: "AsyncSession",
    document_id: str,
    status: str,
    chunk_count: int | None = None,
    error_message: str | None = None,
) -> None:
    """Update KnowledgeBaseDocument processing_status and chunk_count in the database.

    Args:
        session: SQLAlchemy async session.
        document_id: UUID string of the document to update.
        status: New processing status (pending|processing|completed|failed).
        chunk_count: Number of successfully embedded chunks (set on completed).
        error_message: Error description (set on failed).
    """
    from app.models.knowledge_base_document import KnowledgeBaseDocument

    try:
        doc_uuid = uuid.UUID(document_id) if isinstance(document_id, str) else document_id
        doc = await session.get(KnowledgeBaseDocument, doc_uuid)
        if doc is None:
            logger.error("Document %s not found in database for status update", document_id)
            return

        doc.processing_status = status

        if chunk_count is not None:
            doc.chunk_count = chunk_count

        if error_message is not None:
            doc.error_message = error_message

        if status in ("completed", "failed"):
            doc.processed_at = datetime.now(timezone.utc).replace(tzinfo=None)

        await session.commit()
        logger.debug("Updated document %s status to %s", document_id, status)

    except Exception:
        logger.exception("Failed to update document %s status", document_id)
        # Don't re-raise: status update failure shouldn't stop ingestion
        try:
            await session.rollback()
        except Exception:
            pass
