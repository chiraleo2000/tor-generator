"""Cohere Embed 4 via Bedrock Runtime (PN RAG)."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Literal

logger = logging.getLogger("tor_app.pn_rag.embed")

InputType = Literal["search_document", "search_query", "classification", "clustering"]


def _runtime_client(region: str):
    from app.providers.bedrock_client import bedrock_runtime_client
    from app.config import get_settings

    settings = get_settings()
    return bedrock_runtime_client(
        region=region or settings.bedrock_region,
        aws_access_key_id=settings.aws_access_key_id or "",
        aws_secret_access_key=settings.aws_secret_access_key or "",
        bearer_token=getattr(settings, "aws_bearer_token_bedrock", "") or "",
    )


def _parse_embeddings(payload: dict[str, Any]) -> list[list[float]]:
    raw = payload.get("embeddings")
    if isinstance(raw, list):
        return [[float(x) for x in row] for row in raw]
    if isinstance(raw, dict):
        floats = raw.get("float")
        if isinstance(floats, list):
            return [[float(x) for x in row] for row in floats]
    raise ValueError("Cohere Embed response missing float embeddings")


def embed_texts_sync(
    texts: list[str],
    *,
    input_type: InputType,
    model_id: str | None = None,
    region: str | None = None,
    output_dimension: int = 1024,
) -> list[list[float]]:
    """Embed up to 96 texts per Bedrock call (Cohere Embed v4)."""
    if not texts:
        return []
    from app.config import get_settings

    settings = get_settings()
    mid = (model_id or settings.bedrock_embedding_model_id or "cohere.embed-v4:0").strip()
    reg = (region or settings.bedrock_region or "ap-southeast-1").strip()
    dim = int(os.environ.get("EMBEDDING_DIMENSIONS") or output_dimension or 1024)
    client = _runtime_client(reg)
    out: list[list[float]] = []
    batch_size = 32
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        body = {
            "texts": batch,
            "input_type": input_type,
            "embedding_types": ["float"],
            "output_dimension": dim,
            "truncate": "RIGHT",
        }
        response = client.invoke_model(
            modelId=mid,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        vectors = _parse_embeddings(payload)
        if len(vectors) != len(batch):
            raise ValueError(
                f"embed count mismatch: got {len(vectors)} for {len(batch)} texts"
            )
        out.extend(vectors)
    return out


async def embed_texts(
    texts: list[str],
    *,
    input_type: InputType,
    model_id: str | None = None,
    region: str | None = None,
    output_dimension: int = 1024,
) -> list[list[float]]:
    return await asyncio.to_thread(
        embed_texts_sync,
        texts,
        input_type=input_type,
        model_id=model_id,
        region=region,
        output_dimension=output_dimension,
    )


async def embed_query(text: str, **kwargs: Any) -> list[float]:
    vectors = await embed_texts([text], input_type="search_query", **kwargs)
    return vectors[0]


async def embed_documents(texts: list[str], **kwargs: Any) -> list[list[float]]:
    return await embed_texts(texts, input_type="search_document", **kwargs)
