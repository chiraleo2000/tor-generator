"""Ingest: extract → chunk ~4096 → Cohere Embed 4 → S3 Vectors (+ chunk JSON on S3)."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from minio import Minio

from app.domain.file_magic import detect_mime
from app.pn_rag.chunk_pn import pn_chunk_text
from app.pn_rag.config import RagGroup, get_rag_groups_config
from app.pn_rag.embed import embed_documents
from app.pn_rag.s3_vectors_store import put_vectors
from app.pn_rag.storage import PnS3Storage
from app.rag.extraction import extract_text

logger = logging.getLogger("tor_app.pn_rag.ingest")


@dataclass(frozen=True)
class IngestResult:
    rag_group: str
    object_key: str
    source_document: str
    sha256: str
    chunks: int
    vector_index: str
    vector_bucket: str
    status: str


def _put_json(client: Minio, bucket: str, key: str, payload: dict[str, Any]) -> None:
    import io

    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    client.put_object(
        bucket,
        key,
        io.BytesIO(raw),
        length=len(raw),
        content_type="application/json",
    )


def _extract_from_bytes(file_bytes: bytes, filename: str, content_type: str) -> str:
    # Keep original basename so *_tor_extract.json / *_combined.json routing works.
    safe_name = Path(filename).name or "document.bin"
    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / safe_name
        path.write_bytes(file_bytes)
        result = extract_text(str(path), content_type)
        return (result.text or "").strip()


def _load_object_bytes(minio_client: Minio, bucket: str, object_key: str) -> bytes:
    response = minio_client.get_object(bucket, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def _normalize_vector(vector: list[float], dim: int) -> list[float]:
    if len(vector) == dim:
        return vector
    if len(vector) > dim:
        return vector[:dim]
    return vector + [0.0] * (dim - len(vector))


def _write_chunk_and_vector_item(
    *,
    minio_client: Minio,
    bucket: str,
    group: RagGroup,
    embedding_model: str,
    object_key: str,
    name: str,
    doc_id: str,
    chunk: Any,
    vector: list[float],
) -> dict[str, Any]:
    chunk_key = f"{doc_id}_{chunk.metadata.chunk_index}"
    chunk_s3_key = f"{group.prefix}chunks/{doc_id}/{chunk.metadata.chunk_index}.json"
    _put_json(
        minio_client,
        bucket,
        chunk_s3_key,
        {
            "text": chunk.text,
            "rag_group": group.id,
            "source_document": name,
            "object_key": object_key,
            "chunk_index": chunk.metadata.chunk_index,
            "token_count": len(chunk.tokens),
            "embedding_model": embedding_model,
        },
    )
    return {
        "key": chunk_key,
        "vector": vector,
        "metadata": {
            "rag_group": group.id,
            "source_document": name,
            "object_key": object_key,
            "chunk_index": chunk.metadata.chunk_index,
            "chunk_s3_key": chunk_s3_key,
            "token_count": len(chunk.tokens),
            "text_preview": chunk.text[:400],
        },
    }


async def ingest_bytes(
    file_bytes: bytes,
    *,
    filename: str,
    rag_group: str | None,
    minio_client: Minio,
    claimed_mime: str = "",
    run_embed: bool = True,
) -> IngestResult:
    """Upload+verify to object S3, then chunk/embed into S3 Vectors."""
    storage = PnS3Storage(minio_client)
    upload = storage.upload_and_verify(
        file_bytes,
        filename=filename,
        rag_group=rag_group,
        claimed_mime=claimed_mime,
    )
    if not run_embed:
        return IngestResult(
            rag_group=upload.rag_group,
            object_key=upload.object_key,
            source_document=upload.filename,
            sha256=upload.sha256,
            chunks=0,
            vector_index=upload.vector_index,
            vector_bucket=os.environ.get("PN_S3_VECTOR_BUCKET") or upload.bucket,
            status="uploaded_only",
        )
    return await ingest_object_key(
        upload.object_key,
        rag_group=upload.rag_group,
        minio_client=minio_client,
        source_document=upload.filename,
        sha256=upload.sha256,
        content_type=upload.content_type,
        file_bytes=file_bytes,
    )


async def ingest_object_key(
    object_key: str,
    *,
    rag_group: str | None,
    minio_client: Minio,
    source_document: str | None = None,
    sha256: str | None = None,
    content_type: str | None = None,
    file_bytes: bytes | None = None,
) -> IngestResult:
    cfg = get_rag_groups_config()
    group: RagGroup = cfg.require(rag_group)
    bucket = cfg.bucket

    if file_bytes is None:
        file_bytes = _load_object_bytes(minio_client, bucket, object_key)

    name = source_document or object_key.rsplit("/", 1)[-1]
    mime = content_type or detect_mime(file_bytes, "") or "application/octet-stream"
    text = _extract_from_bytes(file_bytes, name, mime)
    if not text:
        raise ValueError("no extractable text from document")

    doc_id = sha256 or object_key.replace("/", "_")[-64:]
    chunking = pn_chunk_text(text, document_id=doc_id)
    if not chunking.chunks:
        raise ValueError("chunking produced zero chunks")

    texts = [c.text for c in chunking.chunks]
    vectors = await embed_documents(texts)
    dim = int(os.environ.get("EMBEDDING_DIMENSIONS") or cfg.embedding_dimensions or 1024)

    vector_items: list[dict[str, Any]] = []
    for chunk, vector in zip(chunking.chunks, vectors, strict=True):
        vector_items.append(
            _write_chunk_and_vector_item(
                minio_client=minio_client,
                bucket=bucket,
                group=group,
                embedding_model=cfg.embedding_model,
                object_key=object_key,
                name=name,
                doc_id=doc_id,
                chunk=chunk,
                vector=_normalize_vector(vector, dim),
            )
        )

    put_vectors(index_name=group.vector_index, items=vector_items)
    vector_bucket = os.environ.get("PN_S3_VECTOR_BUCKET") or bucket

    # Update manifest status
    if sha256:
        manifest_key = f"{group.manifest_prefix()}{sha256}.json"
        try:
            resp = minio_client.get_object(bucket, manifest_key)
            try:
                manifest = json.loads(resp.read().decode("utf-8"))
            finally:
                resp.close()
                resp.release_conn()
            if isinstance(manifest, dict):
                manifest["status"] = "indexed"
                manifest["chunks"] = len(vector_items)
                manifest["vector_index"] = group.vector_index
                _put_json(minio_client, bucket, manifest_key, manifest)
        except Exception:
            logger.exception("manifest update skipped for %s", manifest_key)

    return IngestResult(
        rag_group=group.id,
        object_key=object_key,
        source_document=name,
        sha256=doc_id,
        chunks=len(vector_items),
        vector_index=group.vector_index,
        vector_bucket=vector_bucket,
        status="indexed",
    )


def ingest_result_dict(result: IngestResult) -> dict[str, Any]:
    return asdict(result)
