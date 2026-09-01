"""Mandatory RAG corpus paths and grouping for procurement PDFs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

GROUP_MANDATORY_RAW = "mandatory_raw"
GROUP_MANDATORY_HANDBOOK = "mandatory_handbook"
GROUP_USER = "user"

HANDBOOK_FILENAME = "คู่มือแนวปฏิบัติ_การจัดซื้อจัดจ้างภาครัฐ.pdf"
RAW_FOLDER = ("การจัดซื้อจัดจ้าง", "ข้อมูลดิบ")

GROUP_LABELS = {
    GROUP_MANDATORY_HANDBOOK: "คู่มือแนวปฏิบัติ (บังคับ)",
    GROUP_MANDATORY_RAW: "ข้อมูลดิบกฎหมาย/ระเบียบ (บังคับ)",
    GROUP_USER: "เอกสารของฉัน",
}

GROUP_ORDER = (GROUP_MANDATORY_HANDBOOK, GROUP_MANDATORY_RAW, GROUP_USER)


def group_for_filename(filename: str, owner_id: object | None = None) -> str:
    """Tag a file as user-owned, handbook, or mandatory raw corpus."""
    if owner_id is not None:
        return GROUP_USER
    name = filename or ""
    if HANDBOOK_FILENAME in name or "คู่มือแนวปฏิบัติ" in name:
        return GROUP_MANDATORY_HANDBOOK
    return GROUP_MANDATORY_RAW


@dataclass(frozen=True)
class CorpusFile:
    path: Path
    group: str


def repo_root() -> Path | None:
    """Walk up from this file until documents/sources (or .git + app/backend) is found.

    corpus.py lives at app/backend/app/domain/ — fixed parents[N] breaks when the
    package depth changes; discovery is safer for host and Docker layouts.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "documents" / "sources").is_dir():
            return parent
        if (parent / ".git").exists() and (parent / "app" / "backend").is_dir():
            return parent
    return None


def sources_root(explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        return explicit
    env_root = os.environ.get("KB_SOURCES_ROOT", "").strip()
    if env_root:
        return Path(env_root)
    root = repo_root()
    if root is None:
        return None
    return root / "documents" / "sources"


def _is_listable_dir(path: Path) -> bool:
    try:
        if not path.exists():
            return False
        next(path.iterdir(), None)
        return True
    except OSError:
        return False


def _add_corpus_file(
    files: list[CorpusFile], seen: set[Path], path: Path, group: str
) -> None:
    if not path.is_file():
        return
    resolved = path.resolve()
    if resolved in seen:
        return
    seen.add(resolved)
    files.append(CorpusFile(path=path, group=group))


def _collect_pdfs(
    files: list[CorpusFile], seen: set[Path], directory: Path, group: str
) -> None:
    if not _is_listable_dir(directory):
        return
    for pdf in sorted(directory.rglob("*.pdf")):
        _add_corpus_file(files, seen, pdf, group)


def _add_raw_docs_env(files: list[CorpusFile], seen: set[Path]) -> None:
    env_dir = os.environ.get("RAW_DOCS_DIR")
    if not env_dir:
        return
    extra = Path(env_dir)
    if extra.is_file() and extra.suffix.lower() == ".pdf":
        _add_corpus_file(files, seen, extra, GROUP_MANDATORY_RAW)
        return
    _collect_pdfs(files, seen, extra, GROUP_MANDATORY_RAW)


def list_mandatory_sources(root: Path | None = None) -> list[CorpusFile]:
    """Handbook PDF + PDFs under การจัดซื้อจัดจ้าง/ข้อมูลดิบ, tagged by group."""
    files: list[CorpusFile] = []
    seen: set[Path] = set()
    base = sources_root(root)
    if base is not None:
        _add_corpus_file(files, seen, base / HANDBOOK_FILENAME, GROUP_MANDATORY_HANDBOOK)
        _collect_pdfs(files, seen, base.joinpath(*RAW_FOLDER), GROUP_MANDATORY_RAW)
    _add_raw_docs_env(files, seen)
    return files


def list_mandatory_paths(root: Path | None = None) -> list[Path]:
    return [item.path for item in list_mandatory_sources(root)]


def group_counts(files: list[CorpusFile]) -> dict[str, int]:
    counts = {GROUP_MANDATORY_HANDBOOK: 0, GROUP_MANDATORY_RAW: 0}
    for item in files:
        counts[item.group] = counts.get(item.group, 0) + 1
    return counts
