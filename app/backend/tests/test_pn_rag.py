"""PN multi-RAG config + S3 upload/verify helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from app.pn_rag.config import load_rag_groups_config
from app.pn_rag.storage import PnS3Storage, _safe_filename


def test_load_rag_groups_from_repo_yaml() -> None:
    # Host: app/backend/tests → parents[2] = app/
    # Docker unit image: tests at /app/tests with infra mounted at /app/infra
    here = Path(__file__).resolve()
    candidates: list[Path] = [
        here.parents[2] / "infra" / "pn" / "rag-groups.yaml",
        Path("/app/infra/pn/rag-groups.yaml"),
    ]
    if len(here.parents) > 3:
        candidates.append(here.parents[3] / "infra" / "pn" / "rag-groups.yaml")
    cfg_path = next((p for p in candidates if p.is_file()), None)
    assert cfg_path is not None, f"rag-groups.yaml not found in {candidates}"
    cfg = load_rag_groups_config(cfg_path)
    assert cfg.default_group == "procurement-th"
    assert len(cfg.groups) >= 2
    ids = {g.id for g in cfg.groups}
    assert "procurement-th" in ids
    assert "agency-extra" in ids
    primary = cfg.require("procurement-th")
    assert primary.sources_prefix().startswith("rags/procurement-th/")
    assert primary.vector_index


def test_require_unknown_rag_group_raises(tmp_path: Path) -> None:
    path = tmp_path / "rag-groups.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "default_group": "a",
                "groups": [
                    {
                        "id": "a",
                        "name": "A",
                        "prefix": "rags/a/",
                        "vector_index": "a-v1",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    cfg = load_rag_groups_config(path)
    with pytest.raises(ValueError, match="unknown rag_group"):
        cfg.require("missing")


def test_safe_filename_strips_path() -> None:
    assert _safe_filename(r"..\..\ระเบียบ.pdf").endswith(".pdf")
    assert "/" not in _safe_filename("a/b/c.txt")


def test_upload_and_verify_writes_source_and_manifest() -> None:
    client = MagicMock()
    client.put_object = MagicMock()
    stat = MagicMock()
    stat.size = 12
    stat.etag = '"abc"'
    stat.metadata = {"x-amz-meta-sha256": "x", "x-amz-meta-rag_group": "procurement-th"}
    client.stat_object = MagicMock(return_value=stat)

    root = Path(__file__).resolve().parents[2]
    cfg = load_rag_groups_config(root / "infra" / "pn" / "rag-groups.yaml")
    # Force known sha path by patching verify to accept empty meta sha
    storage = PnS3Storage(client, config=cfg)
    pdf = b"%PDF-1.4 minimal"
    # Fix verify: set metadata sha to match after upload
    digest_holder: dict[str, str] = {}

    def put_side_effect(bucket, key, data, length, content_type, metadata=None):
        if metadata and "sha256" in metadata:
            digest_holder["sha"] = metadata["sha256"]
            stat.metadata = {
                "x-amz-meta-sha256": metadata["sha256"],
                "x-amz-meta-rag_group": metadata.get("rag_group", ""),
            }
            stat.size = length

    client.put_object.side_effect = put_side_effect

    result = storage.upload_and_verify(
        pdf,
        filename="คู่มือ.pdf",
        rag_group="procurement-th",
        claimed_mime="application/pdf",
    )
    assert result.verified is True
    assert result.rag_group == "procurement-th"
    assert "rags/procurement-th/sources/" in result.object_key
    assert result.manifest_key.endswith(".json")
    assert client.put_object.call_count == 2


def test_verify_missing_object() -> None:
    from minio.error import S3Error

    client = MagicMock()
    err = S3Error(
        "NoSuchKey",
        "missing",
        "res",
        "req",
        "host",
        "bucket",
        "obj",
    )
    client.stat_object = MagicMock(side_effect=err)
    root = Path(__file__).resolve().parents[2]
    cfg = load_rag_groups_config(root / "infra" / "pn" / "rag-groups.yaml")
    storage = PnS3Storage(client, config=cfg)
    result = storage.verify_object("rags/procurement-th/sources/nope.pdf")
    assert result.ok is False
    assert result.exists is False
