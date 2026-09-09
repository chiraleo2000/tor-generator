"""Load multi-RAG group config (one S3 bucket → many RAG / MCP targets)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings

logger = logging.getLogger("tor_app.pn_rag.config")

RAG_GROUPS_FILENAME = "rag-groups.yaml"
_DEFAULT_REL = Path("infra") / "pn" / RAG_GROUPS_FILENAME


def _default_config_path() -> Path:
    """Resolve rag-groups.yaml from env, sibling app/infra, or cwd."""
    env = (os.environ.get("PN_RAG_GROUPS_PATH") or "").strip()
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    # app/backend/app/pn_rag → app/infra/pn-ec2 then app/infra/pn
    for rel in (
        Path("infra") / "pn-ec2" / RAG_GROUPS_FILENAME,
        _DEFAULT_REL,
    ):
        candidate = here.parents[3] / rel
        if candidate.is_file():
            return candidate
    return Path.cwd() / "app" / "infra" / "pn-ec2" / RAG_GROUPS_FILENAME


@dataclass(frozen=True)
class RagGroup:
    id: str
    name: str
    description: str
    prefix: str
    vector_index: str
    mcp_enabled: bool = True

    def sources_prefix(self) -> str:
        base = self.prefix if self.prefix.endswith("/") else f"{self.prefix}/"
        return f"{base}sources/"

    def manifest_prefix(self) -> str:
        base = self.prefix if self.prefix.endswith("/") else f"{self.prefix}/"
        return f"{base}manifest/"


@dataclass(frozen=True)
class RagGroupsConfig:
    bucket: str
    default_group: str
    chunk_target_tokens: int
    embedding_model: str
    embedding_dimensions: int
    groups: tuple[RagGroup, ...] = field(default_factory=tuple)

    def get(self, group_id: str) -> RagGroup | None:
        key = (group_id or "").strip()
        for group in self.groups:
            if group.id == key:
                return group
        return None

    def require(self, group_id: str | None = None) -> RagGroup:
        gid = (group_id or "").strip() or self.default_group
        group = self.get(gid)
        if group is None:
            known = ", ".join(g.id for g in self.groups) or "(none)"
            raise ValueError(f"unknown rag_group={gid!r}; known: {known}")
        return group

    def mcp_groups(self) -> list[RagGroup]:
        return [g for g in self.groups if g.mcp_enabled]


def _parse_group(raw: dict[str, Any]) -> RagGroup:
    gid = str(raw.get("id") or "").strip()
    if not gid:
        raise ValueError("rag group missing id")
    prefix = str(raw.get("prefix") or f"rags/{gid}/").strip()
    if not prefix.endswith("/"):
        prefix = f"{prefix}/"
    return RagGroup(
        id=gid,
        name=str(raw.get("name") or gid).strip(),
        description=str(raw.get("description") or "").strip(),
        prefix=prefix,
        vector_index=str(raw.get("vector_index") or f"{gid}-embed4-v1").strip(),
        mcp_enabled=bool(raw.get("mcp_enabled", True)),
    )


def load_rag_groups_config(path: Path | None = None) -> RagGroupsConfig:
    """Load YAML; bucket falls back to settings.minio_bucket when empty."""
    cfg_path = path or _default_config_path()
    if not cfg_path.is_file():
        logger.warning("PN rag-groups config missing: %s — using built-in default", cfg_path)
        settings = get_settings()
        default = RagGroup(
            id="procurement-th",
            name="จัดซื้อจัดจ้าง (คลังหลัก)",
            description="default",
            prefix="rags/procurement-th/",
            vector_index="procurement-th-embed4-v1",
            mcp_enabled=True,
        )
        return RagGroupsConfig(
            bucket=settings.minio_bucket,
            default_group=default.id,
            chunk_target_tokens=4096,
            embedding_model="cohere.embed-v4:0",
            embedding_dimensions=1024,
            groups=(default,),
        )

    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    groups_raw = data.get("groups") or []
    groups = tuple(_parse_group(item) for item in groups_raw if isinstance(item, dict))
    if not groups:
        raise ValueError(f"no rag groups in {cfg_path}")

    settings = get_settings()
    bucket = str(data.get("bucket") or "").strip() or settings.minio_bucket
    default_group = str(data.get("default_group") or groups[0].id).strip()
    if not any(g.id == default_group for g in groups):
        default_group = groups[0].id

    return RagGroupsConfig(
        bucket=bucket,
        default_group=default_group,
        chunk_target_tokens=int(data.get("chunk_target_tokens") or 4096),
        embedding_model=str(data.get("embedding_model") or "cohere.embed-v4:0"),
        embedding_dimensions=int(data.get("embedding_dimensions") or 1024),
        groups=groups,
    )


@lru_cache(maxsize=4)
def _cached_config(path_key: str) -> RagGroupsConfig:
    return load_rag_groups_config(Path(path_key) if path_key else None)


def get_rag_groups_config(*, reload: bool = False) -> RagGroupsConfig:
    path = _default_config_path()
    key = str(path.resolve()) if path.is_file() else ""
    if reload:
        _cached_config.cache_clear()
    return _cached_config(key)


def list_rag_groups(*, mcp_only: bool = False) -> list[RagGroup]:
    cfg = get_rag_groups_config()
    return cfg.mcp_groups() if mcp_only else list(cfg.groups)


def get_rag_group(group_id: str | None = None) -> RagGroup:
    return get_rag_groups_config().require(group_id)
