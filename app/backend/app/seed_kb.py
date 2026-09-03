"""Ingest documents/knowledge-base markdown and JSON extracts into the RAG store.

Usage (from app/backend/): python -m app.seed_kb

On Windows, Docker often cannot list the Thai-path bind-mount at /knowledge-base.
Run this on the host instead, pointing at Docker Postgres and LM Studio:

  POSTGRES_HOST=127.0.0.1
  LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
  KNOWLEDGE_BASE_DIR=<repo>/documents/knowledge-base
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.knowledge_base_document import KnowledgeBaseDocument

_HOST_SEED_HINT = (
    "Knowledge-base directory is not readable. On Windows Docker, the Thai-path "
    "bind-mount /knowledge-base often raises OSError [Errno 5]. Seed from the host:\n"
    "  set POSTGRES_HOST=127.0.0.1\n"
    "  set LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1\n"
    "  set KNOWLEDGE_BASE_DIR=<repo>/documents/knowledge-base\n"
    "  python -m app.seed_kb"
)


def _repo_root() -> Path | None:
    # Local: app/backend/app/seed_kb.py → parents[3] is the repository root.
    # Docker: /app/app/seed_kb.py does not have that many parents.
    parts = Path(__file__).resolve().parents
    if len(parts) > 3:
        return parts[3]
    return None


def _is_listable_dir(path: Path) -> bool:
    """True when path exists and directory listing does not raise OSError."""
    try:
        if not path.exists():
            return False
        next(path.iterdir(), None)
        return True
    except OSError:
        return False


def _safe_print(message: str) -> None:
    """Print without crashing Windows consoles that cannot encode Thai paths."""
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        fallback = message.encode(encoding, errors="replace").decode(
            encoding, errors="replace"
        )
        print(fallback)


def _kb_candidates() -> list[Path]:
    env_dir = os.environ.get("KNOWLEDGE_BASE_DIR")
    candidates: list[Path] = []
    if env_dir:
        candidates.append(Path(env_dir))
    repo_root = _repo_root()
    if repo_root is not None:
        candidates.append(repo_root / "documents" / "knowledge-base")
    candidates.append(Path("/knowledge-base"))
    candidates.append(Path(__file__).resolve().parents[2] / "knowledge-base")
    candidates.append(Path("/app/knowledge-base"))
    return candidates


def _knowledge_base_dir() -> Path:
    for candidate in _kb_candidates():
        if _is_listable_dir(candidate):
            return candidate
    return _kb_candidates()[0]


def _should_seed(path: Path) -> bool:
    """True when a knowledge-base file should be ingested.

    Combined topic packs (`*_combined.json`) and decision-rules JSON are
    seeded even when the filename starts with `_`. Coverage matrices and
    the external-sources note stay out of the RAG store.
    """
    try:
        if not path.is_file():
            return False
    except OSError:
        return False

    name = path.name
    if name.startswith("_coverage_matrix"):
        return False
    if name == "_external_sources_note.md":
        return False
    if name.endswith("_combined.json"):
        return True
    if path.parent.name == "04-decision-rules" and name.endswith(".json"):
        return True
    if name.startswith("_"):
        return False
    return True


def list_seed_files(kb_dir: Path, limit: int | None = None) -> list[Path]:
    """Markdown, text, TOR extracts, combined packs, and decision-rules JSON."""
    if limit is None:
        limit = int(os.environ.get("SEED_KB_LIMIT", "80"))
    files: list[Path] = []
    if not _is_listable_dir(kb_dir):
        return []
    patterns = (
        "*.md",
        "*.txt",
        "*_tor_extract.json",
        "*_combined.json",
        "04-decision-rules/*.json",
    )
    for pattern in patterns:
        try:
            files.extend(kb_dir.rglob(pattern))
        except OSError:
            return []
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in files:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen or not _should_seed(path):
            continue
        seen.add(resolved)
        unique.append(path)
    unique.sort(key=lambda item: item.name)
    return unique[:limit]


def _document_name(path: Path) -> str:
    """Prefer a `.kbname` sidecar so Linux can store short filenames."""
    sidecar = path.with_name(f"{path.stem}.kbname")
    if sidecar.is_file():
        label = sidecar.read_text(encoding="utf-8").strip()
        if label:
            return label[:500]
    return path.stem[:500]


def _category_for(name: str) -> str:
    lowered = name.lower()
    if "พรบ" in name or "พระราชบัญญัติ" in name:
        return "law"
    if "กฎกระทรวง" in name:
        return "regulation"
    if "ระเบียบ" in name:
        return "regulation"
    if "หนังสือ" in name or "กรมบัญชีกลาง" in name:
        return "guideline"
    if "คู่มือ" in name:
        return "manual"
    if "tor" in lowered or "example" in lowered:
        return "example_tor"
    return "guideline"


def _mime_for(path: Path, file_type: str) -> str:
    if path.name.endswith("_tor_extract.json") or path.suffix.lower() == ".json":
        return "application/json"
    mime = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
    }
    return mime.get(file_type, "text/plain")


def _resolve_ingest_path(storage_path: str, kb_dir: Path) -> Path | None:
    stored = Path(storage_path)
    if stored.is_file():
        return stored
    name = stored.name
    direct = kb_dir / name
    if direct.is_file():
        return direct
    try:
        matches = [path for path in kb_dir.rglob(name) if path.is_file()]
    except OSError:
        matches = []
    if len(matches) == 1:
        return matches[0]
    stem = Path(name).stem
    try:
        stem_matches = [
            path
            for path in kb_dir.rglob("*")
            if path.is_file() and path.stem == stem
        ]
    except OSError:
        stem_matches = []
    if len(stem_matches) == 1:
        return stem_matches[0]
    return None


KB_DIR = _knowledge_base_dir()


def _requeue_existing(existing: KnowledgeBaseDocument, name: str) -> None:
    stuck = existing.processing_status == "failed" or (
        existing.processing_status == "processing" and existing.chunk_count == 0
    )
    if stuck:
        existing.processing_status = "pending"
        existing.error_message = None
        _safe_print(f"re-queue stuck: {name}")
        return
    if existing.processing_status == "completed":
        _safe_print(f"skip existing: {name}")
        return
    _safe_print(f"already queued: {name}")


def _queue_new_document(db: AsyncSession, path: Path, name: str) -> None:
    suffix = path.suffix.lower().lstrip(".")
    file_type = "txt" if suffix in {"md", "json", "txt"} else suffix
    db.add(
        KnowledgeBaseDocument(
            name=name,
            category=_category_for(name),
            file_type=file_type if file_type in {"pdf", "docx", "txt"} else "txt",
            storage_path=str(path),
            processing_status="pending",
            chunk_count=0,
        )
    )
    _safe_print(f"queued: {name}")


async def _enqueue_seed_files(db: AsyncSession, files: list[Path]) -> None:
    for path in files:
        name = _document_name(path)
        existing = (
            await db.execute(
                select(KnowledgeBaseDocument).where(KnowledgeBaseDocument.name == name)
            )
        ).scalar_one_or_none()
        if existing:
            _requeue_existing(existing, name)
            continue
        _queue_new_document(db, path, name)
    await db.commit()


async def _pending_documents(db: AsyncSession) -> list[KnowledgeBaseDocument]:
    result = await db.execute(
        select(KnowledgeBaseDocument).where(
            KnowledgeBaseDocument.processing_status.in_(("pending", "processing"))
        )
    )
    return list(result.scalars().all())


async def _ingest_one(
    doc: KnowledgeBaseDocument,
    kb_dir: Path,
    embedding: object,
    vector_store: object,
    db: AsyncSession,
    ingest_document: Callable[..., Awaitable[Any]],
) -> None:
    doc_name = doc.name
    resolved = _resolve_ingest_path(doc.storage_path, kb_dir)
    if resolved is None:
        doc.processing_status = "failed"
        doc.error_message = "file missing"
        _safe_print(f"missing file: {doc_name}")
        return
    if not _should_seed(resolved):
        doc.processing_status = "completed"
        doc.chunk_count = 0
        _safe_print(f"skip internal: {doc_name}")
        return
    try:
        result = await ingest_document(
            document_id=str(doc.id),
            document_name=doc_name,
            file_path=str(resolved),
            mime_type=_mime_for(resolved, doc.file_type),
            embedding_provider=embedding,
            vector_store_provider=vector_store,
            session=db,
        )
        _safe_print(
            f"{'ok' if result.success else 'fail'}: {doc_name} chunks={result.total_chunks}"
        )
    except Exception as exc:  # noqa: BLE001
        doc.processing_status = "failed"
        doc.error_message = str(exc)[:1000]
        _safe_print(f"ingest error {doc_name}: {exc}")


async def _ingest_pending(
    db: AsyncSession, kb_dir: Path, settings: object, session_factory: object
) -> None:
    pending = await _pending_documents(db)
    try:
        from app.providers.factory import ProviderFactory
        from app.rag.ingestion import ingest_document

        factory_ai = ProviderFactory(settings)
        embedding = factory_ai.get_embedding()
        vector_store = factory_ai.get_vector_store(session_factory)
        for doc in pending:
            await _ingest_one(
                doc, kb_dir, embedding, vector_store, db, ingest_document
            )
    except Exception as exc:  # noqa: BLE001
        _safe_print(
            "embedding/vector providers unavailable, leaving documents "
            f"pending: {exc}"
        )
    await db.commit()


async def seed() -> None:
    kb_dir = _knowledge_base_dir()
    if not _is_listable_dir(kb_dir):
        _safe_print(_HOST_SEED_HINT)
        _safe_print(f"tried: {', '.join(str(path) for path in _kb_candidates())}")
        return

    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_size=5)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    files = list_seed_files(kb_dir)
    _safe_print(f"found {len(files)} knowledge-base files under {kb_dir}")
    async with factory() as db:
        await _enqueue_seed_files(db, files)
        await _ingest_pending(db, kb_dir, settings, factory)
    await engine.dispose()
    _safe_print("seed_kb complete")


if __name__ == "__main__":
    asyncio.run(seed())
