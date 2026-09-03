"""HTTP client for an optional external Custom RAG retrieve API."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

import httpx

from app.config import get_settings
from app.rag.retrieval import RetrievedChunk, coerce_page_number

logger = logging.getLogger(__name__)


def resolve_custom_rag_url(base_url: str, retrieve_path: str = "") -> str:
    """Build POST URL. Empty path keeps /api/search bases as-is; else /v1/retrieve."""
    base = (base_url or "").strip().rstrip("/")
    path = (retrieve_path or "").strip()
    if path.startswith(("http://", "https://")):
        return path.rstrip("/")
    if path:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{base}{path.rstrip('/')}"
    lower = base.lower()
    if lower.endswith(("/v1/retrieve", "/api/search", "/search")):
        return base
    return f"{base}/v1/retrieve"


def _raw_chunk_list(data: Any) -> list[Any]:
    if not isinstance(data, dict):
        return []
    for key in ("chunks", "results", "items", "documents", "hits"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    nested = data.get("data")
    if isinstance(nested, dict):
        return _raw_chunk_list(nested)
    if isinstance(nested, list):
        return nested
    return []


def _item_text(item: dict[str, Any]) -> str:
    for key in ("text", "content", "snippet", "page_content", "body"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _chunk_from_item(item: dict[str, Any], index: int) -> RetrievedChunk | None:
    text = _item_text(item)
    if not text:
        return None
    metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
    metadata = {**metadata, "rag_source": "custom_rag"}
    source = (
        item.get("source_document")
        or metadata.get("source_document")
        or metadata.get("document_name")
        or item.get("title")
    )
    try:
        score = float(item.get("score") or item.get("relevance") or 0.0)
    except (TypeError, ValueError):
        score = 0.0
    return RetrievedChunk(
        id=str(item.get("id") or f"custom-rag-{uuid4().hex[:12]}-{index}"),
        text=text,
        score=score,
        document_type=metadata.get("document_type"),
        legal_reference=metadata.get("legal_reference"),
        section_relevance=metadata.get("section_relevance"),
        source_document=str(source) if source else None,
        section_label=metadata.get("section_label"),
        page_number=coerce_page_number(
            item.get("page_number") or metadata.get("page_number")
        ),
        metadata=metadata,
    )


class CustomRagClient:
    """Calls POST retrieve/search URL and maps chunks into RetrievedChunk."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = "",
        top_k: int = 5,
        timeout: float = 30.0,
        retrieve_path: str = "",
    ) -> None:
        self._url = resolve_custom_rag_url(base_url, retrieve_path)
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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(self._url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        chunks: list[RetrievedChunk] = []
        for index, item in enumerate(_raw_chunk_list(data)):
            if not isinstance(item, dict):
                continue
            chunk = _chunk_from_item(item, index)
            if chunk is not None:
                chunks.append(chunk)
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
        retrieve_path=str(getattr(settings, "custom_rag_retrieve_path", "") or ""),
    )
