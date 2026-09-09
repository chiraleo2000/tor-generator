"""Retrieve from S3 Vectors for PN MCP / API."""

from __future__ import annotations

import json
import logging
from typing import Any

from minio import Minio

from app.pn_rag.config import get_rag_groups_config
from app.pn_rag.embed import embed_query
from app.pn_rag.s3_vectors_store import query_vectors

logger = logging.getLogger("tor_app.pn_rag.retrieve")


def _load_chunk_text(minio_client: Minio | None, bucket: str, chunk_s3_key: str) -> str:
    if not minio_client or not chunk_s3_key:
        return ""
    try:
        resp = minio_client.get_object(bucket, chunk_s3_key)
        try:
            payload = json.loads(resp.read().decode("utf-8"))
        finally:
            resp.close()
            resp.release_conn()
        if isinstance(payload, dict):
            return str(payload.get("text") or "")
    except Exception:
        logger.exception("failed to load chunk %s", chunk_s3_key)
    return ""


def _query_hits(
    index_name: str,
    query_vector: list[float],
    top_k: int,
    metadata_filter: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    try:
        return query_vectors(
            index_name=index_name,
            query_vector=query_vector,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )
    except Exception:
        logger.exception("query_vectors with filter failed; retry without filter")
        return query_vectors(
            index_name=index_name,
            query_vector=query_vector,
            top_k=top_k,
            metadata_filter=None,
        )


def _score_from_distance(distance: Any) -> float:
    try:
        return 1.0 / (1.0 + float(distance)) if distance is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _hit_to_chunk(
    hit: dict[str, Any],
    *,
    group_id: str,
    vector_index: str,
    bucket: str,
    minio_client: Minio | None,
) -> dict[str, Any] | None:
    meta = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
    if meta.get("rag_group") and meta.get("rag_group") != group_id:
        return None
    chunk_s3_key = str(meta.get("chunk_s3_key") or "")
    text = _load_chunk_text(minio_client, bucket, chunk_s3_key)
    if not text:
        text = str(meta.get("text_preview") or "")
    return {
        "id": str(hit.get("key") or ""),
        "text": text,
        "score": _score_from_distance(hit.get("distance")),
        "source_document": str(meta.get("source_document") or ""),
        "metadata": {
            **meta,
            "rag_source": "s3_vectors",
            "rag_group": group_id,
            "vector_index": vector_index,
        },
    }


async def retrieve_pn_chunks(
    query: str,
    *,
    rag_group: str | None = None,
    top_k: int = 3,
    minio_client: Minio | None = None,
) -> list[dict[str, Any]]:
    """Embed query → S3 Vectors → attach full text from object S3 when possible."""
    q = (query or "").strip()
    if not q:
        return []
    cfg = get_rag_groups_config()
    group = cfg.require(rag_group)
    k = max(1, min(int(top_k or 3), int(__import__("os").environ.get("PN_RETRIEVE_TOP_K_MAX") or 5)))

    qvec = await embed_query(q)
    hits = _query_hits(group.vector_index, qvec, k, {"rag_group": group.id})
    out: list[dict[str, Any]] = []
    for hit in hits:
        chunk = _hit_to_chunk(
            hit,
            group_id=group.id,
            vector_index=group.vector_index,
            bucket=cfg.bucket,
            minio_client=minio_client,
        )
        if chunk is not None:
            out.append(chunk)
    return out
