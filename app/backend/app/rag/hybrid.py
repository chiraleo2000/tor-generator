"""Hybrid pgvector + GraphRAG + optional Custom RAG retrieval."""

from __future__ import annotations

import logging
from uuid import UUID

from app import infra as runtime
from app.config import get_settings
from app.providers.base import SearchResult
from app.providers.factory import ProviderFactory
from app.rag.acl import document_is_visible
from app.rag.custom_rag_client import build_custom_rag_client
from app.rag.mcp_rag import retrieve_mcp_chunks
from app.rag.graph_store import GraphRAGStore, citations_from_graph
from app.rag.retrieval import RetrievalFilter, RetrievalResult, RetrievedChunk

logger = logging.getLogger(__name__)


def _meta_source(metadata: dict | None) -> str | None:
    data = metadata or {}
    return data.get("source_document") or data.get("document_name")


def owner_filter_dict(
    *,
    user_id: UUID | str | None,
    search_scope: str = "both",
) -> dict:
    payload: dict = {"search_scope": search_scope}
    if user_id is not None:
        payload["owner_user_id"] = str(user_id)
    return payload


def _chunk_from_hit(
    item: SearchResult, *, user_id: UUID | str | None, search_scope: str
) -> RetrievedChunk | None:
    metadata = item.metadata or {}
    if not document_is_visible(
        document_owner_id=metadata.get("owner_id"),
        viewer_id=user_id,
        search_scope=search_scope,
    ):
        return None
    return RetrievedChunk(
        id=item.id,
        text=item.text,
        score=item.score,
        document_type=metadata.get("document_type"),
        legal_reference=metadata.get("legal_reference"),
        section_relevance=metadata.get("section_relevance"),
        source_document=_meta_source(metadata),
        section_label=metadata.get("section_label"),
        page_number=metadata.get("page_number"),
        metadata=metadata,
    )


def _use_local_rag(rag_sources: str) -> bool:
    return rag_sources in ("local", "both")


def _use_custom_rag(rag_sources: str) -> bool:
    return rag_sources in ("custom", "both")


async def hybrid_retrieve(
    query: str,
    *,
    user_id: UUID | str | None = None,
    search_scope: str = "both",
    top_k: int = 5,
    section_relevance: str | None = None,
    extra_filter: RetrievalFilter | None = None,
) -> tuple[RetrievalResult, list[dict[str, str]], bool]:
    """Return local vector chunks, optional custom/MCP RAG, plus graph citations.

    The third value is True when Neo4j expansion was skipped (degraded).
    """
    settings = get_settings()
    rag_sources = str(getattr(settings, "rag_sources", "both") or "both")
    empty = RetrievalResult(chunks=[], query=query, top_k=top_k, actual_count=0)
    db_factory = runtime.session_factory
    chunks: list[RetrievedChunk] = []
    custom_degraded = False

    if _use_local_rag(rag_sources):
        if db_factory is None:
            if not _use_custom_rag(rag_sources):
                return empty, [], True
        else:
            factory = ProviderFactory()
            store = factory.get_vector_store(db_factory)
            query_vector = await factory.get_embedding().embed_query(query)
            merged_filter = owner_filter_dict(user_id=user_id, search_scope=search_scope)
            if extra_filter:
                extra = extra_filter.to_filter_dict() or {}
                merged_filter.update(extra)
            elif section_relevance:
                merged_filter["section_relevance"] = section_relevance

            search_results = await store.search(
                query_vector, top_k=top_k, filter=merged_filter
            )
            chunks = [
                mapped
                for mapped in (
                    _chunk_from_hit(
                        item, user_id=user_id, search_scope=search_scope
                    )
                    for item in search_results
                )
                if mapped is not None
            ]

    if _use_custom_rag(rag_sources):
        client = build_custom_rag_client()
        if client is None and rag_sources == "custom":
            logger.warning("rag_sources=custom but custom RAG is not configured")
        elif client is not None:
            try:
                custom_k = int(getattr(settings, "custom_rag_top_k", top_k) or top_k)
                custom_chunks = await client.retrieve(
                    query,
                    user_id=user_id,
                    search_scope=search_scope,
                    top_k=max(top_k, custom_k),
                )
                chunks.extend(custom_chunks)
            except Exception:
                logger.exception("Custom RAG retrieve failed; continuing with local results")
                custom_degraded = True

    try:
        chunks.extend(
            await retrieve_mcp_chunks(query, user_id=user_id, search_scope=search_scope)
        )
    except Exception:
        logger.exception("MCP RAG retrieve failed; continuing with other sources")

    chunks.sort(key=lambda item: item.score, reverse=True)
    chunks = chunks[: max(top_k * 2, top_k)]

    result = RetrievalResult(
        chunks=chunks,
        query=query,
        top_k=top_k,
        actual_count=len(chunks),
        filter_applied=extra_filter,
    )

    citations: list[dict[str, str]] = []
    for chunk in chunks:
        source_kind = (chunk.metadata or {}).get("rag_source")
        if source_kind == "custom_rag":
            label = chunk.source_document or "Custom RAG"
            citations.append({"type": "custom_rag", "label": str(label)})
        if source_kind == "mcp":
            citations.append({"type": "mcp", "label": str(chunk.source_document or "MCP")})
        if chunk.source_document:
            citations.append({"type": "document", "label": chunk.source_document})
        if chunk.legal_reference:
            citations.append({"type": "article", "label": chunk.legal_reference})
        if chunk.section_relevance:
            citations.append({"type": "slot", "label": str(chunk.section_relevance)})

    graph_degraded = True
    if _use_local_rag(rag_sources) and runtime.neo4j_driver is not None:
        try:
            store_graph = GraphRAGStore(runtime.neo4j_driver)
            graph_limit = max(8, min(32, top_k))
            rows = await store_graph.expand(
                query_text=query,
                slot_key=section_relevance,
                limit=graph_limit,
                search_scope=search_scope,
                owner_id=str(user_id) if user_id else None,
            )
            citations.extend(citations_from_graph(rows))
            extra_bits = [
                str(row.get("name") or row.get("other") or "")
                for row in rows
                if row.get("name") or row.get("other")
            ]
            if extra_bits and chunks:
                chunks[0].text = chunks[0].text + "\n\n[กราฟกฎหมาย]\n" + "\n".join(
                    extra_bits[:graph_limit]
                )
            graph_degraded = False
        except Exception:
            logger.exception("GraphRAG expand failed; continuing with vector/custom RAG")
            graph_degraded = True

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in citations:
        key = f"{item.get('type')}:{item.get('label')}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    # Preserve prior contract: third flag means graph degraded (custom failure is logged only)
    del custom_degraded
    return result, unique, graph_degraded
