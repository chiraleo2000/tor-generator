"""Upload and verify documents on S3/MinIO under a rag_group prefix."""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from minio import Minio
from minio.error import S3Error

from app.domain.file_magic import require_kb_upload
from app.pn_rag.config import RagGroup, RagGroupsConfig, get_rag_groups_config

logger = logging.getLogger("tor_app.pn_rag.storage")

DEFAULT_DOCUMENT_NAME = "document.bin"
_SAFE_NAME = re.compile(r"[^\w.\-]+", re.UNICODE)


@dataclass(frozen=True)
class UploadResult:
    rag_group: str
    object_key: str
    manifest_key: str
    sha256: str
    size_bytes: int
    content_type: str
    filename: str
    bucket: str
    verified: bool
    vector_index: str


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    rag_group: str
    object_key: str
    sha256: str
    size_bytes: int
    etag: str
    exists: bool
    message: str
    bucket: str


def _safe_filename(name: str) -> str:
    base = (name or DEFAULT_DOCUMENT_NAME).replace("\\", "/").split("/")[-1].strip() or DEFAULT_DOCUMENT_NAME
    cleaned = _SAFE_NAME.sub("_", base).strip("._") or DEFAULT_DOCUMENT_NAME
    return cleaned[:180]


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify_missing(
    rag_group: str,
    object_key: str,
    bucket: str,
    *,
    message: str = "object not found",
) -> VerifyResult:
    return VerifyResult(
        ok=False,
        rag_group=rag_group,
        object_key=object_key,
        sha256="",
        size_bytes=0,
        etag="",
        exists=False,
        message=message,
        bucket=bucket,
    )


def _verify_sha_mismatch(
    rag_group: str,
    object_key: str,
    sha256: str,
    size_bytes: int,
    etag: str,
    bucket: str,
) -> VerifyResult:
    return VerifyResult(
        ok=False,
        rag_group=rag_group,
        object_key=object_key,
        sha256=sha256,
        size_bytes=size_bytes,
        etag=etag,
        exists=True,
        message="sha256 metadata mismatch",
        bucket=bucket,
    )


def _object_meta(stat: Any) -> dict[str, str]:
    return {
        str(k).lower().removeprefix("x-amz-meta-"): str(v)
        for k, v in (stat.metadata or {}).items()
    }


def _verify_from_stat(
    stat: Any,
    group_id: str,
    object_key: str,
    bucket: str,
    expected_sha256: str | None,
) -> VerifyResult:
    meta = _object_meta(stat)
    sha_meta = meta.get("sha256") or ""
    size_bytes = int(stat.size or 0)
    etag = str(stat.etag or "").strip('"')
    if expected_sha256 and sha_meta and sha_meta != expected_sha256:
        return _verify_sha_mismatch(
            group_id, object_key, sha_meta, size_bytes, str(stat.etag or ""), bucket
        )
    return _verify_ok(
        meta.get("rag_group") or group_id,
        object_key,
        sha_meta or (expected_sha256 or ""),
        size_bytes,
        etag,
        bucket,
    )


def _verify_ok(
    rag_group: str,
    object_key: str,
    sha256: str,
    size_bytes: int,
    etag: str,
    bucket: str,
) -> VerifyResult:
    ok = size_bytes > 0
    return VerifyResult(
        ok=ok,
        rag_group=rag_group,
        object_key=object_key,
        sha256=sha256,
        size_bytes=size_bytes,
        etag=etag,
        exists=True,
        message="ok" if ok else "empty object",
        bucket=bucket,
    )


class PnS3Storage:
    """Put/head objects for PN multi-RAG layouts on one bucket."""

    def __init__(
        self,
        client: Minio,
        config: RagGroupsConfig | None = None,
    ) -> None:
        self._client = client
        self._config = config or get_rag_groups_config()

    @property
    def bucket(self) -> str:
        return self._config.bucket

    def upload_and_verify(
        self,
        file_bytes: bytes,
        *,
        filename: str,
        rag_group: str | None = None,
        claimed_mime: str = "",
    ) -> UploadResult:
        """Validate type, upload to group prefix, write manifest, HEAD-verify."""
        if not file_bytes:
            raise ValueError("empty file")
        group = self._config.require(rag_group)
        content_type = require_kb_upload(file_bytes, claimed_mime, filename)
        digest = _sha256_hex(file_bytes)
        safe_name = _safe_filename(filename)
        object_key = f"{group.sources_prefix()}{digest}_{safe_name}"
        manifest_key = f"{group.manifest_prefix()}{digest}.json"

        self._client.put_object(
            self.bucket,
            object_key,
            io.BytesIO(file_bytes),
            length=len(file_bytes),
            content_type=content_type,
            metadata={
                "sha256": digest,
                "rag_group": group.id,
                "filename": safe_name,
            },
        )

        manifest = {
            "rag_group": group.id,
            "vector_index": group.vector_index,
            "object_key": object_key,
            "sha256": digest,
            "size_bytes": len(file_bytes),
            "content_type": content_type,
            "filename": safe_name,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "chunk_target_tokens": self._config.chunk_target_tokens,
            "embedding_model": self._config.embedding_model,
            "status": "uploaded",
        }
        body = json.dumps(manifest, ensure_ascii=False).encode("utf-8")
        self._client.put_object(
            self.bucket,
            manifest_key,
            io.BytesIO(body),
            length=len(body),
            content_type="application/json",
        )

        verify = self.verify_object(object_key, expected_sha256=digest, rag_group=group.id)
        if not verify.ok:
            raise RuntimeError(f"upload verify failed: {verify.message}")

        return UploadResult(
            rag_group=group.id,
            object_key=object_key,
            manifest_key=manifest_key,
            sha256=digest,
            size_bytes=len(file_bytes),
            content_type=content_type,
            filename=safe_name,
            bucket=self.bucket,
            verified=True,
            vector_index=group.vector_index,
        )

    def _stat_or_missing(self, object_key: str, group_id: str) -> Any | VerifyResult:
        try:
            return self._client.stat_object(self.bucket, object_key)
        except S3Error as exc:
            if exc.code not in {"NoSuchKey", "NotFound", "NoSuchObject"}:
                logger.exception("stat_object failed for %s", object_key)
            return _verify_missing(
                group_id,
                object_key,
                self.bucket,
                message="object not found" if exc.code in {"NoSuchKey", "NotFound", "NoSuchObject"} else str(exc),
            )

    def verify_object(
        self,
        object_key: str,
        *,
        expected_sha256: str | None = None,
        rag_group: str | None = None,
    ) -> VerifyResult:
        """HEAD object; optionally match sha256 from metadata or expected value."""
        group_id = (rag_group or "").strip() or self._config.default_group
        stat = self._stat_or_missing(object_key, group_id)
        if isinstance(stat, VerifyResult):
            return stat
        return _verify_from_stat(stat, group_id, object_key, self.bucket, expected_sha256)

    def list_source_keys(self, rag_group: str | None = None, *, limit: int = 100) -> list[str]:
        group = self._config.require(rag_group)
        prefix = group.sources_prefix()
        keys: list[str] = []
        for obj in self._client.list_objects(self.bucket, prefix=prefix, recursive=True):
            if obj.object_name:
                keys.append(obj.object_name)
            if len(keys) >= limit:
                break
        return keys


def upload_result_dict(result: UploadResult) -> dict[str, Any]:
    return asdict(result)


def verify_result_dict(result: VerifyResult) -> dict[str, Any]:
    return asdict(result)


def resolve_group(rag_group: str | None = None) -> RagGroup:
    return get_rag_groups_config().require(rag_group)
