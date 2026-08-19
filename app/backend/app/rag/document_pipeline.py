"""Ingest a file into Mongo GridFS + pgvector + Neo4j graph."""

from __future__ import annotations

import logging
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.corpus import group_for_filename
from app.infra import mongo_client, neo4j_driver
from app.io_temp import unlink_path, write_temp_bytes
from app.models.knowledge_base_document import KnowledgeBaseDocument
from app.providers.factory import ProviderFactory
from app.rag.graph_extract import extract_graph_from_text
from app.rag.graph_store import GraphRAGStore
from app.rag.ingestion import ingest_document
from app.storage.mongo_store import store_from_client

logger = logging.getLogger(__name__)


def _category_for(name: str) -> str:
    if "พรบ" in name or "พระราชบัญญัติ" in name:
        return "law"
    if "กฎกระทรวง" in name:
        return "regulation"
    if "ระเบียบ" in name:
        return "regulation"
    if "หนังสือ" in name or "กรมบัญชีกลาง" in name:
        return "guideline"
    if "คู่มือ" in name:
        return "manual"
    return "guideline"


def _file_type_for(mime_type: str) -> str:
    if mime_type.endswith("pdf"):
        return "pdf"
    if "word" in mime_type:
        return "docx"
    return "txt"


async def ingest_file_bytes(
    *,
    db: AsyncSession,
    filename: str,
    content: bytes,
    mime_type: str,
    scope: str,
    owner_id: UUID | None = None,
    project_id: str | None = None,
    session_factory,
    corpus_group: str | None = None,
    category: str | None = None,
) -> KnowledgeBaseDocument:
    """Store original, chunk/embed, and optionally extract a graph."""
    resolved_group = corpus_group or group_for_filename(filename, owner_id=owner_id)
    store = store_from_client(mongo_client)
    grid_id = None
    if store is not None:
        meta = store.put_file(
            filename=filename,
            content=content,
            content_type=mime_type,
            scope=scope,
            owner_id=str(owner_id) if owner_id else None,
            project_id=project_id,
        )
        grid_id = meta.get("gridfs_id")

    suffix = Path(filename).suffix or ".bin"
    tmp_path = await write_temp_bytes(content, suffix=suffix)
    extra_metadata = {
        "corpus_group": resolved_group,
        "scope": scope,
        "owner_id": str(owner_id) if owner_id else None,
    }
    doc = KnowledgeBaseDocument(
        id=uuid4(),
        name=filename[:500],
        category=category or _category_for(filename),
        file_type=_file_type_for(mime_type),
        storage_path=str(tmp_path),
        processing_status="pending",
        owner_id=owner_id,
        mongo_gridfs_id=grid_id,
        scope=scope,
        corpus_group=resolved_group,
    )
    db.add(doc)
    await db.flush()

    factory = ProviderFactory()
    embedding = factory.get_embedding()
    vector_store = factory.get_vector_store(session_factory)
    try:
        await ingest_document(
            document_id=str(doc.id),
            document_name=doc.name,
            file_path=str(tmp_path),
            mime_type=mime_type,
            embedding_provider=embedding,
            vector_store_provider=vector_store,
            session=db,
            extra_metadata=extra_metadata,
        )
    except Exception as exc:
        doc.processing_status = "failed"
        doc.error_message = str(exc)[:1000]
        logger.exception("ingest failed for %s", filename)
        await unlink_path(tmp_path)
        return doc

    if neo4j_driver is not None:
        try:
            from app.rag.extraction import extract_text

            extracted = extract_text(str(tmp_path), mime_type)
            llm = factory.get_llm()
            nodes, rels = await extract_graph_from_text(
                llm, extracted.text, document_name=filename
            )
            graph = GraphRAGStore(neo4j_driver)
            await graph.upsert_extraction(
                document_id=str(doc.id),
                document_name=filename,
                nodes=nodes,
                rels=rels,
                owner_id=str(owner_id) if owner_id else None,
                scope=scope,
            )
        except Exception:
            logger.exception("graph extract failed for %s (chunks still saved)", filename)

    await unlink_path(tmp_path)
    return doc
