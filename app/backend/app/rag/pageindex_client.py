"""HTTP client for PageIndex document ingestion and lifecycle operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from app.config import get_settings


class PageIndexClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str = "",
        ingest_timeout: float = 1800.0,
    ) -> None:
        base = base_url.rstrip("/")
        if base.endswith("/api/search"):
            base = base[: -len("/api/search")]
        self._base_url = base
        self._api_key = api_key.strip()
        self._ingest_timeout = max(30.0, float(ingest_timeout))

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            return {"Accept": "application/json"}
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "X-API-Key": self._api_key,
        }

    async def ingest_document(
        self,
        *,
        document_id: str,
        document_name: str,
        content: bytes,
        mime_type: str,
        category: str,
        owner_id: str | None,
        scope: str,
        replace: bool = True,
    ) -> dict[str, Any]:
        data = {
            "doc_id": document_id,
            "display_name": document_name,
            "category": category,
            "owner_id": owner_id or "",
            "scope": scope,
            "replace": "true" if replace else "false",
        }
        extension = {
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "text/plain": ".txt",
        }.get(mime_type)
        upload_name = document_name
        if extension and Path(upload_name).suffix.lower() != extension:
            upload_name = f"{upload_name}{extension}"
        files = {"file": (upload_name, content, mime_type)}
        timeout = httpx.Timeout(self._ingest_timeout, connect=15.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/ingest",
                data=data,
                files=files,
                headers=self._headers(),
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                try:
                    detail = response.json().get("detail")
                except Exception:
                    detail = response.text[:500]
                raise RuntimeError(
                    f"PageIndex ingestion rejected the document: {detail or response.status_code}"
                ) from exc
            payload = response.json()
        if not isinstance(payload, dict) or payload.get("status") != "ready":
            raise RuntimeError("PageIndex ingestion did not return ready status")
        return payload

    async def delete_document(self, document_id: str) -> None:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.delete(
                f"{self._base_url}/api/docs/{document_id}",
                headers=self._headers(),
            )
        if response.status_code == 404:
            return
        response.raise_for_status()

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self._base_url}/health")
            response.raise_for_status()
            return response.json()


def build_pageindex_client() -> PageIndexClient:
    settings = get_settings()
    return PageIndexClient(
        base_url=settings.pageindex_base_url,
        api_key=settings.pageindex_api_key or settings.custom_rag_api_key,
        ingest_timeout=settings.pageindex_ingest_timeout_seconds,
    )
