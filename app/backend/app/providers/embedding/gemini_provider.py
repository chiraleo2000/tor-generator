"""Gemini embedding provider via the public REST API (httpx)."""

from __future__ import annotations

import logging

import httpx

from app.providers.base import EmbeddingProvider
from app.providers.constants import EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Google Gemini embedContent client, truncated/padded to EMBEDDING_DIMENSIONS."""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-004",
        dimensions: int = EMBEDDING_DIMENSIONS,
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required for GeminiEmbeddingProvider")
        self._api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self._timeout = timeout

    def _fit(self, vector: list[float]) -> list[float]:
        if len(vector) == self.dimensions:
            return vector
        if len(vector) > self.dimensions:
            return vector[: self.dimensions]
        return vector + [0.0] * (self.dimensions - len(vector))

    async def embed_query(self, text: str) -> list[float]:
        url = f"{_GEMINI_BASE}/models/{self.model}:embedContent?key={self._api_key}"
        body = {"content": {"parts": [{"text": text}]}}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=body)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as exc:
            raise TimeoutError("Gemini embeddings timed out") from exc
        except httpx.HTTPError as exc:
            raise ConnectionError(f"Gemini embeddings unreachable: {exc}") from exc
        values = (payload.get("embedding") or {}).get("values") or []
        return self._fit([float(item) for item in values])

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_query(text) for text in texts]
