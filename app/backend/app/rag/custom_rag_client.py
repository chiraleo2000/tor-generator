"""HTTP client for an optional external Custom RAG retrieve API."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

import httpx

from app.config import get_settings
from app.rag.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


class CustomRagClient:
    """Calls POST {base}/v1/retrieve and maps chunks into RetrievedChunk."""

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
        payload: dict[str, Any] = {
            "query": query,
            "top_k": top_k or self._top_k,
            "filters": {
                "search_scope": search_scope,
                "user_id": str(user_id) if user_id else None,
            },
        }
        url = f"{self._base_url}/v1/retrieve"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        raw_chunks = data.get("chunks") if isinstance(data, dict) else None
        if not isinstance(raw_chunks, list):
            return []
        chunks: list[RetrievedChunk] = []
        for index, item in enumerate(raw_chunks):
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            metadata = {**metadata, "rag_source": "custom_rag"}
            source = (
                item.get("source_document")
                or metadata.get("source_document")
                or metadata.get("document_name")
            )
            chunks.append(
                RetrievedChunk(
                    id=str(item.get("id") or f"custom-rag-{uuid4().hex[:12]}-{index}"),
                    text=text,
                    score=float(item.get("score") or 0.0),
                    document_type=metadata.get("document_type"),
                    legal_reference=metadata.get("legal_reference"),
                    section_relevance=metadata.get("section_relevance"),
                    source_document=str(source) if source else None,
                    section_label=metadata.get("section_label"),
                    page_number=metadata.get("page_number"),
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
        top_k=int(getattr(settings, "custom_rag_top_k", 5) or 5),
        timeout=float(getattr(settings, "custom_rag_timeout_seconds", 30.0) or 30.0),
    )
