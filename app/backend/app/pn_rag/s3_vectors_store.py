"""S3 Vectors put/query for PN RAG indexes."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("tor_app.pn_rag.s3_vectors")


def _region() -> str:
    return (
        os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or os.environ.get("BEDROCK_REGION")
        or "ap-southeast-1"
    )


def s3vectors_client(region: str | None = None):
    import boto3

    return boto3.client("s3vectors", region_name=region or _region())


def vector_bucket_name() -> str:
    name = (
        os.environ.get("PN_S3_VECTOR_BUCKET")
        or os.environ.get("PN_S3_BUCKET")
        or ""
    ).strip()
    if not name:
        from app.config import get_settings

        name = (get_settings().minio_bucket or "").strip()
    if not name:
        raise ValueError("PN_S3_VECTOR_BUCKET (or PN_S3_BUCKET) is required")
    return name


def put_vectors(
    *,
    index_name: str,
    items: list[dict[str, Any]],
    vector_bucket: str | None = None,
) -> None:
    """Put vectors. Each item: key, vector (list[float]), metadata (dict)."""
    if not items:
        return
    client = s3vectors_client()
    bucket = vector_bucket or vector_bucket_name()
    batch_size = 100
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        payload = []
        for row in batch:
            entry: dict[str, Any] = {
                "key": str(row["key"]),
                "data": {"float32": [float(x) for x in row["vector"]]},
            }
            meta = row.get("metadata")
            if isinstance(meta, dict) and meta:
                # S3 Vectors metadata values should be JSON-serializable scalars/lists
                entry["metadata"] = meta
            payload.append(entry)
        client.put_vectors(
            vectorBucketName=bucket,
            indexName=index_name,
            vectors=payload,
        )
        logger.info(
            "put_vectors index=%s bucket=%s count=%s",
            index_name,
            bucket,
            len(payload),
        )


def query_vectors(
    *,
    index_name: str,
    query_vector: list[float],
    top_k: int = 3,
    metadata_filter: dict[str, Any] | None = None,
    vector_bucket: str | None = None,
) -> list[dict[str, Any]]:
    """Return list of {key, distance, metadata}."""
    client = s3vectors_client()
    bucket = vector_bucket or vector_bucket_name()
    kwargs: dict[str, Any] = {
        "vectorBucketName": bucket,
        "indexName": index_name,
        "topK": max(1, int(top_k)),
        "queryVector": {"float32": [float(x) for x in query_vector]},
        "returnMetadata": True,
        "returnDistance": True,
    }
    if metadata_filter:
        kwargs["filter"] = metadata_filter
    response = client.query_vectors(**kwargs)
    vectors = response.get("vectors") or response.get("result") or []
    out: list[dict[str, Any]] = []
    if not isinstance(vectors, list):
        return out
    for row in vectors:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "key": str(row.get("key") or ""),
                "distance": row.get("distance"),
                "metadata": row.get("metadata") if isinstance(row.get("metadata"), dict) else {},
            }
        )
    return out
