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
    parts = Path(__file__).resolve().parents
    if len(parts) > 3:
        return parts[3]
    return None


def sources_root(explicit: Path | None = None) -> Path | None:
    if explicit is not None:
        return explicit
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


def list_mandatory_sources(root: Path | None = None) -> list[CorpusFile]:
    """Handbook PDF + PDFs under การจัดซื้อจัดจ้าง/ข้อมูลดิบ, tagged by group."""
    files: list[CorpusFile] = []
    seen: set[Path] = set()

    def _add(path: Path, group: str) -> None:
        if not path.is_file():
            return
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        files.append(CorpusFile(path=path, group=group))

    base = sources_root(root)
    if base is not None:
        _add(base / HANDBOOK_FILENAME, GROUP_MANDATORY_HANDBOOK)
        raw_dir = base.joinpath(*RAW_FOLDER)
        if _is_listable_dir(raw_dir):
            for pdf in sorted(raw_dir.glob("*.pdf")):
                _add(pdf, GROUP_MANDATORY_RAW)

    env_dir = os.environ.get("RAW_DOCS_DIR")
    if env_dir:
        extra = Path(env_dir)
        if extra.is_file() and extra.suffix.lower() == ".pdf":
            _add(extra, GROUP_MANDATORY_RAW)
        elif _is_listable_dir(extra):
            for pdf in sorted(extra.glob("*.pdf")):
                _add(pdf, GROUP_MANDATORY_RAW)
    return files


def list_mandatory_paths(root: Path | None = None) -> list[Path]:
    return [item.path for item in list_mandatory_sources(root)]


def group_counts(files: list[CorpusFile]) -> dict[str, int]:
    counts = {GROUP_MANDATORY_HANDBOOK: 0, GROUP_MANDATORY_RAW: 0}
    for item in files:
        counts[item.group] = counts.get(item.group, 0) + 1
    return counts
