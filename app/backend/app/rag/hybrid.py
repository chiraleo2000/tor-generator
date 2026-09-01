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
from app.rag.graph_store import GraphRAGStore, citations_from_graph
from app.rag.mcp_rag import retrieve_mcp_chunks
from app.rag.retrieval import RetrievalFilter, RetrievalResult, RetrievedChunk, coerce_page_number

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
        page_number=coerce_page_number(metadata.get("page_number")),
        metadata=metadata,
    )


def _use_local_rag(rag_sources: str) -> bool:
    return rag_sources in ("local", "both")


def _use_custom_rag(rag_sources: str) -> bool:
    return rag_sources in ("custom", "both")


def query_with_section(query: str, section_relevance: str | None) -> str:
    """Fold TOR section labels into the search text instead of JSONB equality."""
    if not section_relevance:
        return query
    from app.domain.slots import slot_label

    label = slot_label(section_relevance)
    parts = [query.strip()]
    if label and label not in query:
        parts.insert(0, label)
    if section_relevance not in query:
        parts.insert(0, section_relevance)
    return " ".join(part for part in parts if part)


def _merged_search_filter(
    *,
    user_id: UUID | str | None,
    search_scope: str,
    section_relevance: str | None,
    extra_filter: RetrievalFilter | None,
) -> dict:
    """ACL + optional document_type/legal_reference.

    Do not apply section_relevance as JSONB containment: baseline law PDFs
    are not tagged with s1–s13, so an exact filter returns zero chunks.
    """
    del section_relevance
    merged_filter = owner_filter_dict(user_id=user_id, search_scope=search_scope)
    if extra_filter:
        extra = extra_filter.to_filter_dict() or {}
        extra.pop("section_relevance", None)
        merged_filter.update(extra)
    return merged_filter


async def _retrieve_local_chunks(
    query: str,
    *,
    user_id: UUID | str | None,
    search_scope: str,
    top_k: int,
    section_relevance: str | None,
    extra_filter: RetrievalFilter | None,
) -> list[RetrievedChunk]:
    db_factory = runtime.session_factory
    if db_factory is None:
        return []
    factory = ProviderFactory()
    store = factory.get_vector_store(db_factory)
    query_vector = await factory.get_embedding().embed_query(
        query_with_section(query, section_relevance)
    )
    merged_filter = _merged_search_filter(
        user_id=user_id,
        search_scope=search_scope,
        section_relevance=section_relevance,
        extra_filter=extra_filter,
    )
    search_results = await store.search(query_vector, top_k=top_k, filter=merged_filter)
    return [
        mapped
        for mapped in (
            _chunk_from_hit(item, user_id=user_id, search_scope=search_scope)
            for item in search_results
        )
        if mapped is not None
    ]


async def _retrieve_custom_chunks(
    query: str,
    *,
    user_id: UUID | str | None,
    search_scope: str,
    top_k: int,
    rag_sources: str,
) -> list[RetrievedChunk]:
    client = build_custom_rag_client()
    if client is None:
        if rag_sources == "custom":
            logger.warning("rag_sources=custom but custom RAG is not configured")
        return []
    try:
        settings = get_settings()
        custom_k = int(getattr(settings, "custom_rag_top_k", top_k) or top_k)
        return await client.retrieve(
            query,
            user_id=user_id,
            search_scope=search_scope,
            top_k=max(top_k, custom_k),
        )
    except Exception:  # NOSONAR python:S110 — fail-open extra RAG
        logger.exception("Custom RAG retrieve failed; continuing with local results")
        return []


def _citations_for_chunk(chunk: RetrievedChunk) -> list[dict[str, str]]:
    citations: list[dict[str, str]] = []
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
    return citations


def _dedupe_citations(citations: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in citations:
        key = f"{item.get('type')}:{item.get('label')}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


async def _expand_graph(
    query: str,
    *,
    chunks: list[RetrievedChunk],
    section_relevance: str | None,
    top_k: int,
    search_scope: str,
    user_id: UUID | str | None,
) -> tuple[list[dict[str, str]], bool]:
    if runtime.neo4j_driver is None:
        return [], True
    try:
        store_graph = GraphRAGStore(runtime.neo4j_driver)
        graph_limit = max(8, min(48, top_k))
        rows = await store_graph.expand(
            query_text=query,
            slot_key=section_relevance,
            limit=graph_limit,
            search_scope=search_scope,
            owner_id=str(user_id) if user_id else None,
        )
        citations = citations_from_graph(rows)
        extra_bits = [
            str(row.get("name") or row.get("other") or "")
            for row in rows
            if row.get("name") or row.get("other")
        ]
        if extra_bits and chunks:
            chunks[0].text = chunks[0].text + "\n\n[กราฟกฎหมาย]\n" + "\n".join(
                extra_bits[:graph_limit]
            )
        return citations, False
    except Exception:  # NOSONAR python:S110 — fail-open graph expand
        logger.exception("GraphRAG expand failed; continuing with vector/custom RAG")
        return [], True


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
    chunks: list[RetrievedChunk] = []

    if _use_local_rag(rag_sources):
        if runtime.session_factory is None and not _use_custom_rag(rag_sources):
            return empty, [], True
        chunks.extend(
            await _retrieve_local_chunks(
                query,
                user_id=user_id,
                search_scope=search_scope,
                top_k=top_k,
                section_relevance=section_relevance,
                extra_filter=extra_filter,
            )
        )

    if _use_custom_rag(rag_sources):
        chunks.extend(
            await _retrieve_custom_chunks(
                query,
                user_id=user_id,
                search_scope=search_scope,
                top_k=top_k,
                rag_sources=rag_sources,
            )
        )

    try:
        chunks.extend(
            await retrieve_mcp_chunks(query, user_id=user_id, search_scope=search_scope)
        )
    except Exception:  # NOSONAR python:S110 — fail-open MCP
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
        citations.extend(_citations_for_chunk(chunk))

    graph_citations: list[dict[str, str]] = []
    graph_degraded = True
    if _use_local_rag(rag_sources):
        graph_citations, graph_degraded = await _expand_graph(
            query,
            chunks=chunks,
            section_relevance=section_relevance,
            top_k=top_k,
            search_scope=search_scope,
            user_id=user_id,
        )
    citations.extend(graph_citations)

    return result, _dedupe_citations(citations), graph_degraded


_QA_QUESTION_TAILS = (
    "หมายความว่าอย่างไร",
    "ได้หรือไม่",
    "หรือไม่",
    "อย่างไร",
    "คืออะไร",
    "ไหม",
)


def expand_qa_queries(query: str) -> list[str]:
    """Primary question plus a shorter keyword variant for recall."""
    text = " ".join((query or "").split())
    if not text:
        return []
    out: list[str] = [text]
    stripped = text
    for tail in _QA_QUESTION_TAILS:
        if stripped.endswith(tail) and len(stripped) > len(tail) + 6:
            stripped = stripped[: -len(tail)].strip(" \t?？")
            break
    if stripped and stripped not in out:
        out.append(stripped)
    if len(text) > 160:
        short = text[:160].rsplit(" ", 1)[0] or text[:160]
        if short not in out:
            out.append(short)
    return out[:3]


def _chunk_identity(chunk: RetrievedChunk) -> str:
    return str(chunk.id or "") or str(chunk.text or "")[:80]


async def _safe_local_chunks(
    query: str,
    *,
    user_id: UUID | str | None,
    search_scope: str,
    top_k: int,
    section_relevance: str | None,
    extra_filter: RetrievalFilter | None,
) -> list[RetrievedChunk]:
    try:
        return await _retrieve_local_chunks(
            query,
            user_id=user_id,
            search_scope=search_scope,
            top_k=top_k,
            section_relevance=section_relevance,
            extra_filter=extra_filter,
        )
    except Exception:
        logger.exception("variant RAG query failed")
        return []


async def hybrid_retrieve_multi(
    query: str,
    *,
    user_id: UUID | str | None = None,
    search_scope: str = "both",
    top_k: int = 5,
    section_relevance: str | None = None,
    extra_filter: RetrievalFilter | None = None,
) -> tuple[RetrievalResult, list[dict[str, str]], bool]:
    """Primary hybrid retrieve plus extra vector hits from query variants."""
    primary, citations, degraded = await hybrid_retrieve(
        query,
        user_id=user_id,
        search_scope=search_scope,
        top_k=top_k,
        section_relevance=section_relevance,
        extra_filter=extra_filter,
    )
    variants = expand_qa_queries(query)[1:]
    if not variants:
        return primary, citations, degraded

    merged = list(primary.chunks)
    seen: set[str] = set()
    for chunk in merged:
        key = _chunk_identity(chunk)
        if key:
            seen.add(key)
    extra_k = max(8, top_k // 2)
    for variant in variants:
        extra = await _safe_local_chunks(
            variant,
            user_id=user_id,
            search_scope=search_scope,
            top_k=extra_k,
            section_relevance=section_relevance,
            extra_filter=extra_filter,
        )
        for chunk in extra:
            key = _chunk_identity(chunk)
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(chunk)

    merged.sort(key=lambda item: item.score, reverse=True)
    cap = max(top_k * 2, top_k)
    merged = merged[:cap]
    result = RetrievalResult(
        chunks=merged,
        query=query,
        top_k=top_k,
        actual_count=len(merged),
        filter_applied=extra_filter,
    )
    return result, citations, degraded
