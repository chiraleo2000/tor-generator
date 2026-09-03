"""Amazon Bedrock embedding provider (Titan). Vectors are resized to 768-d."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.providers.base import EmbeddingProvider
from app.providers.constants import EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)


def _fit_dimensions(vector: list[float], size: int = EMBEDDING_DIMENSIONS) -> list[float]:
    if len(vector) == size:
        return vector
    if len(vector) > size:
        return vector[:size]
    return vector + [0.0] * (size - len(vector))


class BedrockEmbeddingProvider(EmbeddingProvider):
    """Titan embeddings via Bedrock Runtime invoke_model."""

    def __init__(
        self,
        *,
        region: str,
        model_id: str,
        aws_access_key_id: str = "",
        aws_secret_access_key: str = "",
        aws_bearer_token_bedrock: str = "",
    ) -> None:
        from app.providers.bedrock_client import bedrock_runtime_client

        self._client = bedrock_runtime_client(
            region=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            bearer_token=aws_bearer_token_bedrock,
        )
        self._model_id = model_id

    def _embed_one(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text})
        response = self._client.invoke_model(
            modelId=self._model_id,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        vector = payload.get("embedding") or payload.get("embeddingsByType", {}).get("float")
        if not isinstance(vector, list):
            raise ValueError("Bedrock embedding response missing vector")
        return _fit_dimensions([float(item) for item in vector])

    async def embed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._embed_one, text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        for item in texts:
            out.append(await asyncio.to_thread(self._embed_one, item))
        return out
