"""Amazon Bedrock embedding provider. Vector size follows the live model (Cohere 1024 / Titan 1024 / env)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Literal

from app.providers.base import EmbeddingProvider
from app.providers.bedrock_client import call_bedrock_with_retry
from app.providers.constants import EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)

InputType = Literal["search_document", "search_query", "classification", "clustering"]

_COHERE_OUTPUT_DIMS = (256, 512, 1024, 1536)
_TITAN_OUTPUT_DIMS = (256, 512, 1024)
_COHERE_BATCH_SIZE = 32


def _target_dimensions() -> int:
    try:
        from app.providers.model_capabilities import embedding_dimensions

        return int(embedding_dimensions())
    except Exception:
        return EMBEDDING_DIMENSIONS


def _fit_dimensions(vector: list[float], size: int | None = None) -> list[float]:
    target = int(size or _target_dimensions())
    if len(vector) == target:
        return vector
    if len(vector) > target:
        return vector[:target]
    return vector + [0.0] * (target - len(vector))


def _is_cohere_model(model_id: str) -> bool:
    return "cohere" in (model_id or "").lower()


def _nearest_output_dimension(target: int, allowed: tuple[int, ...]) -> int:
    if target in allowed:
        return target
    for size in allowed:
        if target <= size:
            return size
    return allowed[-1]


def _request_output_dimension(model_id: str, target: int | None = None) -> int:
    size = int(target if target is not None else _target_dimensions())
    allowed = _COHERE_OUTPUT_DIMS if _is_cohere_model(model_id) else _TITAN_OUTPUT_DIMS
    return _nearest_output_dimension(size, allowed)


def _titan_body(text: str, model_id: str) -> dict[str, Any]:
    return {
        "inputText": text,
        "dimensions": _request_output_dimension(model_id),
    }


def _cohere_body(texts: list[str], input_type: InputType, model_id: str) -> dict[str, Any]:
    return {
        "texts": texts,
        "input_type": input_type,
        "embedding_types": ["float"],
        "output_dimension": _request_output_dimension(model_id),
        "truncate": "RIGHT",
    }


def _parse_titan_vector(payload: dict[str, Any]) -> list[float]:
    vector = payload.get("embedding") or payload.get("embeddingsByType", {}).get("float")
    if not isinstance(vector, list):
        raise ValueError("Bedrock embedding response missing vector")
    return _fit_dimensions([float(item) for item in vector])


def _parse_cohere_vectors(payload: dict[str, Any]) -> list[list[float]]:
    raw = payload.get("embeddings")
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        rows = raw.get("float")
    else:
        rows = None
    if not isinstance(rows, list):
        raise ValueError("Bedrock embedding response missing vector")
    return [_fit_dimensions([float(item) for item in row]) for row in rows]


class BedrockEmbeddingProvider(EmbeddingProvider):
    """Titan/Cohere embeddings via Bedrock Runtime invoke_model."""

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

    def _invoke_model(self, body: dict[str, Any]) -> dict[str, Any]:
        def _call() -> dict[str, Any]:
            response = self._client.invoke_model(
                modelId=self._model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            return json.loads(response["body"].read())

        return call_bedrock_with_retry(
            _call,
            model_id=self._model_id,
            op="invoke_model",
        )

    def _embed_one(self, text: str) -> list[float]:
        if _is_cohere_model(self._model_id):
            return self._embed_cohere([text], input_type="search_query")[0]
        payload = self._invoke_model(_titan_body(text, self._model_id))
        return _parse_titan_vector(payload)

    def _embed_cohere(
        self,
        texts: list[str],
        *,
        input_type: InputType,
    ) -> list[list[float]]:
        out: list[list[float]] = []
        for index in range(0, len(texts), _COHERE_BATCH_SIZE):
            batch = texts[index : index + _COHERE_BATCH_SIZE]
            payload = self._invoke_model(
                _cohere_body(batch, input_type, self._model_id)
            )
            vectors = _parse_cohere_vectors(payload)
            if len(vectors) != len(batch):
                raise ValueError(
                    f"embed count mismatch: got {len(vectors)} for {len(batch)} texts"
                )
            out.extend(vectors)
        return out

    async def embed_query(self, text: str) -> list[float]:
        return await asyncio.to_thread(self._embed_one, text)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if _is_cohere_model(self._model_id):
            return await asyncio.to_thread(
                self._embed_cohere, texts, input_type="search_document"
            )
        out: list[list[float]] = []
        for item in texts:
            out.append(await asyncio.to_thread(self._embed_one, item))
        return out
