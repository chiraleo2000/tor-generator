"""Resolve the git repo root on the host and inside the backend container."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "docker-compose.yml").is_file():
            return parent
    if Path("/documents/sources").is_dir():
        return Path("/")
    parents = list(here.parents)
    if len(parents) > 3:
        return parents[3]
    return parents[-1]


def knowledge_base_dir(root: Path | None = None) -> Path:
    docker_kb = Path("/knowledge-base")
    if docker_kb.is_dir():
        return docker_kb
    return (root or repo_root()) / "documents" / "knowledge-base"
