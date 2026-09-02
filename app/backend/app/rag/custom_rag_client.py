"""HTTP client for external RAG APIs, including Betimes PageIndex RAG."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

import httpx

from app.config import get_settings
from app.rag.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


class CustomRagClient:
    """Retrieve and normalize chunks from Custom RAG or PageIndex RAG.

    The original TOR contract is ``POST {base}/v1/retrieve`` with a ``chunks``
    response. Betimes PageIndex RAG exposes ``POST /api/search`` with a ``hits``
    response. A full ``.../api/search`` URL selects PageIndex directly; a plain
    base URL keeps the original contract and falls back to PageIndex on 404/405.
    """

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = "",
        top_k: int = 5,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key.strip()
        self._top_k = max(1, int(top_k))
        self._timeout = timeout

    async def retrieve(
        self,
        query: str,
        *,
        user_id: UUID | str | None = None,
        search_scope: str = "both",
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
            # Knowledge-RAG protects /api/* with X-API-Key. Sending both headers
            # preserves compatibility with generic Bearer-token Custom RAG APIs.
            headers["X-API-Key"] = self._api_key
        effective_top_k = max(1, int(top_k or self._top_k))
        custom_payload: dict[str, Any] = {
            "query": query,
            "top_k": effective_top_k,
            "filters": {
                "search_scope": search_scope,
                "user_id": str(user_id) if user_id else None,
            },
        }
        pageindex_payload = {
            "query": query,
            "k": effective_top_k,
            "user_id": str(user_id) if user_id else None,
            "search_scope": search_scope,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            if self._base_url.endswith("/api/search"):
                response = await client.post(
                    self._base_url,
                    json=pageindex_payload,
                    headers=headers,
                )
            else:
                response = await client.post(
                    f"{self._base_url}/v1/retrieve",
                    json=custom_payload,
                    headers=headers,
                )
                if response.status_code in (404, 405):
                    response = await client.post(
                        f"{self._base_url}/api/search",
                        json=pageindex_payload,
                        headers=headers,
                    )
            response.raise_for_status()
            data = response.json()

        is_pageindex = isinstance(data, dict) and isinstance(data.get("hits"), list)
        raw_chunks = (
            data.get("hits") if is_pageindex else data.get("chunks")
        ) if isinstance(data, dict) else None
        if not isinstance(raw_chunks, list):
            return []
        chunks: list[RetrievedChunk] = []
        for index, item in enumerate(raw_chunks):
            if not isinstance(item, dict):
                continue
            text = str(
                item.get("text")
                or item.get("full_text")
                or item.get("details")
                or item.get("summary")
                or ""
            ).strip()
            if not text:
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            metadata = dict(metadata)
            if is_pageindex:
                metadata.update(
                    {
                        "rag_source": "pageindex_rag",
                        "retrieval_engine": "pageindex_bm25_graph",
                        "doc_id": item.get("doc_id"),
                        "section_id": item.get("section_id"),
                        "source_kind": item.get("source_kind"),
                        "source_origin": item.get("source_origin"),
                        "source_url": item.get("source_url"),
                        "keywords": item.get("keywords") or [],
                    }
                )
            else:
                metadata["rag_source"] = "custom_rag"
            source = (
                item.get("source_document")
                or item.get("doc_title")
                or metadata.get("source_document")
                or metadata.get("document_name")
            )
            chunk_id = item.get("id")
            if not chunk_id and item.get("doc_id"):
                chunk_id = f"{item['doc_id']}:{item.get('section_id') or index}"
            score = float(item.get("score") or 0.0)
            if is_pageindex and score > 1.0:
                # BM25 scores are unbounded; keep ordering while making them
                # comparable to cosine-similarity results used by the TOR app.
                score = score / (score + 1.0)
            chunks.append(
                RetrievedChunk(
                    id=str(chunk_id or f"custom-rag-{uuid4().hex[:12]}-{index}"),
                    text=text,
                    score=max(0.0, score),
                    document_type=metadata.get("document_type") or item.get("source_kind"),
                    legal_reference=metadata.get("legal_reference") or item.get("legal_reference"),
                    section_relevance=(
                        metadata.get("section_relevance")
                        or item.get("section_relevance")
                    ),
                    source_document=str(source) if source else None,
                    section_label=metadata.get("section_label") or item.get("title"),
                    page_number=metadata.get("page_number") or item.get("page_start"),
                    metadata=metadata,
                )
            )
        return chunks


def build_custom_rag_client() -> CustomRagClient | None:
    settings = get_settings()
    if not getattr(settings, "custom_rag_enabled", False):
        return None
    base = str(getattr(settings, "custom_rag_base_url", "") or "").strip()
    if not base:
        return None
    return CustomRagClient(
        base_url=base,
        api_key=str(getattr(settings, "custom_rag_api_key", "") or ""),
        top_k=int(getattr(settings, "custom_rag_top_k", 24) or 24),
        timeout=float(getattr(settings, "custom_rag_timeout_seconds", 30.0) or 30.0),
    )
