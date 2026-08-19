"""Hybrid pgvector + GraphRAG retrieval used by chat, intake, and orchestrator."""

from __future__ import annotations

import logging
from uuid import UUID

from app.infra import neo4j_driver, session_factory
from app.providers.factory import ProviderFactory
from app.rag.graph_store import GraphRAGStore, citations_from_graph
from app.rag.retrieval import RetrievalFilter, RetrievalResult, RetrievedChunk

logger = logging.getLogger(__name__)


def owner_filter_dict(
    *,
    user_id: UUID | str | None,
    search_scope: str = "both",
) -> dict:
    payload: dict = {"search_scope": search_scope}
    if user_id is not None:
        payload["owner_user_id"] = str(user_id)
    return payload


async def hybrid_retrieve(
    query: str,
    *,
    user_id: UUID | str | None = None,
    search_scope: str = "both",
    top_k: int = 5,
    section_relevance: str | None = None,
    extra_filter: RetrievalFilter | None = None,
) -> tuple[RetrievalResult, list[dict[str, str]], bool]:
    """Return pgvector chunks plus graph citations.

    The third value is True when Neo4j expansion was skipped (degraded).
    """
    empty = RetrievalResult(chunks=[], query=query, top_k=top_k, actual_count=0)
    if session_factory is None:
        return empty, [], True

    factory = ProviderFactory()
    store = factory.get_vector_store(session_factory)
    query_vector = await factory.get_embedding().embed_query(query)
    merged_filter = owner_filter_dict(user_id=user_id, search_scope=search_scope)
    if extra_filter:
        extra = extra_filter.to_filter_dict() or {}
        merged_filter.update(extra)
    elif section_relevance:
        merged_filter["section_relevance"] = section_relevance

    search_results = await store.search(query_vector, top_k=top_k, filter=merged_filter)
    chunks = [
        RetrievedChunk(
            id=item.id,
            text=item.text,
            score=item.score,
            document_type=(item.metadata or {}).get("document_type"),
            legal_reference=(item.metadata or {}).get("legal_reference"),
            section_relevance=(item.metadata or {}).get("section_relevance"),
            source_document=(item.metadata or {}).get("source_document"),
            section_label=(item.metadata or {}).get("section_label"),
            page_number=(item.metadata or {}).get("page_number"),
            metadata=item.metadata or {},
        )
        for item in search_results
    ]
    result = RetrievalResult(
        chunks=chunks,
        query=query,
        top_k=top_k,
        actual_count=len(chunks),
        filter_applied=extra_filter,
    )

    citations: list[dict[str, str]] = []
    for chunk in chunks:
        if chunk.source_document:
            citations.append({"type": "document", "label": chunk.source_document})
        if chunk.legal_reference:
            citations.append({"type": "article", "label": chunk.legal_reference})
        if chunk.section_relevance:
            citations.append({"type": "slot", "label": str(chunk.section_relevance)})

    graph_degraded = True
    if neo4j_driver is not None:
        try:
            store_graph = GraphRAGStore(neo4j_driver)
            rows = await store_graph.expand(
                query_text=query,
                slot_key=section_relevance,
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
                    extra_bits[:8]
                )
            graph_degraded = False
        except Exception:
            logger.exception("GraphRAG expand failed; continuing with pgvector")
            graph_degraded = True

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in citations:
        key = f"{item.get('type')}:{item.get('label')}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return result, unique, graph_degraded
