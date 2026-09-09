"""PN ingest / embed / S3 Vectors retrieve (mocked AWS)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from app.pn_rag.config import load_rag_groups_config
from app.pn_rag.embed import _parse_embeddings
from app.pn_rag.s3_vectors_store import put_vectors, query_vectors


def test_parse_embeddings_list_and_float_dict() -> None:
    assert _parse_embeddings({"embeddings": [[0.1, 0.2]]}) == [[0.1, 0.2]]
    assert _parse_embeddings({"embeddings": {"float": [[1.0, 2.0]]}}) == [[1.0, 2.0]]
    with pytest.raises(ValueError):
        _parse_embeddings({"embeddings": {}})


def test_put_and_query_vectors_call_boto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PN_S3_VECTOR_BUCKET", "vec-bucket")
    client = MagicMock()
    client.put_vectors = MagicMock()
    client.query_vectors = MagicMock(
        return_value={
            "vectors": [
                {
                    "key": "doc_0",
                    "distance": 0.1,
                    "metadata": {"rag_group": "procurement-th", "text_preview": "hi"},
                }
            ]
        }
    )
    with patch("app.pn_rag.s3_vectors_store.s3vectors_client", return_value=client):
        put_vectors(
            index_name="procurement-th-embed4-v1",
            items=[
                {
                    "key": "doc_0",
                    "vector": [0.0] * 4,
                    "metadata": {"rag_group": "procurement-th"},
                }
            ],
        )
        hits = query_vectors(
            index_name="procurement-th-embed4-v1",
            query_vector=[0.0] * 4,
            top_k=3,
            metadata_filter={"rag_group": "procurement-th"},
        )
    assert client.put_vectors.called
    assert hits[0]["key"] == "doc_0"
    assert hits[0]["metadata"]["rag_group"] == "procurement-th"


@pytest.mark.asyncio
async def test_ingest_bytes_indexes_chunks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PN_S3_VECTOR_BUCKET", "vec-bucket")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "4")
    path = tmp_path / "rag-groups.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "bucket": "obj-bucket",
                "default_group": "procurement-th",
                "embedding_dimensions": 4,
                "groups": [
                    {
                        "id": "procurement-th",
                        "name": "main",
                        "prefix": "rags/procurement-th/",
                        "vector_index": "procurement-th-embed4-v1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    cfg = load_rag_groups_config(path)

    client = MagicMock()
    digest_holder: dict[str, str] = {}
    stat = MagicMock()
    stat.size = 0
    stat.etag = '"e"'
    stat.metadata = {}

    def put_side_effect(bucket, key, data, length, content_type, metadata=None):
        if metadata and "sha256" in metadata:
            digest_holder["sha"] = metadata["sha256"]
            stat.metadata = {
                "x-amz-meta-sha256": metadata["sha256"],
                "x-amz-meta-rag_group": metadata.get("rag_group", ""),
            }
            stat.size = length

    client.put_object.side_effect = put_side_effect
    client.stat_object = MagicMock(return_value=stat)

    fake_chunks = MagicMock()
    chunk = MagicMock()
    chunk.text = "ข้อความทดสอบการจัดซื้อจัดจ้าง"
    chunk.tokens = ["ข้อความ", "ทดสอบ"]
    chunk.metadata = MagicMock(chunk_index=0)
    fake_chunks.chunks = [chunk]

    with (
        patch("app.pn_rag.ingest.get_rag_groups_config", return_value=cfg),
        patch("app.pn_rag.storage.get_rag_groups_config", return_value=cfg),
        patch("app.pn_rag.ingest.pn_chunk_text", return_value=fake_chunks),
        patch(
            "app.pn_rag.ingest.embed_documents",
            return_value=[[0.1, 0.2, 0.3, 0.4]],
        ),
        patch("app.pn_rag.ingest.put_vectors") as put_vec,
        patch(
            "app.pn_rag.ingest._extract_from_bytes",
            return_value="ข้อความทดสอบการจัดซื้อจัดจ้าง",
        ),
    ):
        from app.pn_rag.ingest import ingest_bytes

        result = await ingest_bytes(
            b"hello",
            filename="note.txt",
            rag_group="procurement-th",
            minio_client=client,
            claimed_mime="text/plain",
        )

    assert result.status == "indexed"
    assert result.chunks == 1
    assert put_vec.called
    assert any("chunks/" in str(c.args[1]) for c in client.put_object.call_args_list)


@pytest.mark.asyncio
async def test_retrieve_pn_chunks_loads_text(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PN_S3_VECTOR_BUCKET", "vec-bucket")
    path = tmp_path / "rag-groups.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "bucket": "obj-bucket",
                "default_group": "procurement-th",
                "groups": [
                    {
                        "id": "procurement-th",
                        "name": "main",
                        "prefix": "rags/procurement-th/",
                        "vector_index": "idx",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    cfg = load_rag_groups_config(path)
    minio = MagicMock()

    class _Body:
        def read(self):
            return b'{"text":"full chunk text"}'

        def close(self):
            return None

        def release_conn(self):
            return None

    minio.get_object = MagicMock(return_value=_Body())

    with (
        patch("app.pn_rag.retrieve.get_rag_groups_config", return_value=cfg),
        patch("app.pn_rag.retrieve.embed_query", return_value=[0.0, 1.0]),
        patch(
            "app.pn_rag.retrieve.query_vectors",
            return_value=[
                {
                    "key": "a_0",
                    "distance": 0.2,
                    "metadata": {
                        "rag_group": "procurement-th",
                        "chunk_s3_key": "rags/procurement-th/chunks/a/0.json",
                        "source_document": "a.txt",
                        "text_preview": "preview",
                    },
                }
            ],
        ),
    ):
        from app.pn_rag.retrieve import retrieve_pn_chunks

        hits = await retrieve_pn_chunks(
            "งบประมาณ",
            rag_group="procurement-th",
            top_k=3,
            minio_client=minio,
        )
    assert len(hits) == 1
    assert hits[0]["text"] == "full chunk text"
    assert hits[0]["metadata"]["rag_source"] == "s3_vectors"


def test_retrieve_backend_prefers_vector_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import mcp_retrieve_server as mcp

    monkeypatch.delenv("PN_RETRIEVE_BACKEND", raising=False)
    monkeypatch.delenv("PN_S3_VECTOR_BUCKET", raising=False)
    monkeypatch.setenv("PN_S3_BUCKET", "objects-only")
    assert mcp._retrieve_backend() == "pgvector"
    monkeypatch.setenv("PN_S3_VECTOR_BUCKET", "vectors")
    assert mcp._retrieve_backend() == "s3_vectors"
    monkeypatch.setenv("PN_RETRIEVE_BACKEND", "pgvector")
    assert mcp._retrieve_backend() == "pgvector"
