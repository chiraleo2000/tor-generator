"""Incremental mandatory PDF sync into pgvector (baseline corpus only)."""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.corpus import CorpusFile, list_mandatory_sources
from app.models.kb_chunk import KBChunk
from app.models.knowledge_base_document import KnowledgeBaseDocument
from app.rag.document_pipeline import ingest_file_bytes
from app.rag.graph_store import GraphRAGStore

logger = logging.getLogger(__name__)

ProgressFn = Callable[[str], None]


@dataclass
class SyncStats:
    ingested: int = 0
    skipped: int = 0
    failed: int = 0
    ingested_names: list[str] = field(default_factory=list)
    skipped_names: list[str] = field(default_factory=list)
    failed_names: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ingested": self.ingested,
            "skipped": self.skipped,
            "failed": self.failed,
            "ingested_names": self.ingested_names,
            "skipped_names": self.skipped_names,
            "failed_names": self.failed_names,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def wipe_baseline_documents(db: AsyncSession) -> int:
    """Delete shared KB rows and chunks. Keep officer private uploads."""
    result = await db.execute(
        select(KnowledgeBaseDocument.id).where(KnowledgeBaseDocument.owner_id.is_(None))
    )
    ids = [row[0] for row in result.all()]
    if not ids:
        return 0
    await db.execute(delete(KBChunk).where(KBChunk.document_id.in_(ids)))
    await db.execute(
        delete(KnowledgeBaseDocument).where(KnowledgeBaseDocument.owner_id.is_(None))
    )
    return len(ids)


async def _existing_baseline(
    db: AsyncSession,
) -> tuple[set[str], set[str]]:
    result = await db.execute(
        select(
            KnowledgeBaseDocument.name,
            KnowledgeBaseDocument.content_sha256,
        ).where(KnowledgeBaseDocument.owner_id.is_(None))
    )
    names: set[str] = set()
    hashes: set[str] = set()
    for name, digest in result.all():
        if name:
            names.add(str(name))
        if digest:
            hashes.add(str(digest))
    return names, hashes


async def _sync_one_pdf(
    item: CorpusFile,
    names: set[str],
    hashes: set[str],
    stats: SyncStats,
    log: ProgressFn,
    db: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[set[str], set[str]]:
    try:
        data = item.path.read_bytes()
    except OSError as exc:
        stats.failed += 1
        stats.failed_names.append(item.path.name)
        log(f"  failed read {item.path.name}: {exc}")
        return names, hashes
    digest = sha256_bytes(data)
    if digest in hashes or item.path.name in names:
        stats.skipped += 1
        stats.skipped_names.append(item.path.name)
        log(f"skip [{item.group}] {item.path.name}")
        return names, hashes
    log(f"ingest [{item.group}] {item.path.name} ({len(data)} bytes)")
    try:
        doc = await ingest_file_bytes(
            db=db,
            filename=item.path.name,
            content=data,
            mime_type="application/pdf",
            scope="baseline",
            owner_id=None,
            session_factory=session_factory,
            corpus_group=item.group,
            content_sha256=digest,
        )
        await db.commit()
        names.add(item.path.name)
        hashes.add(digest)
        if doc.processing_status == "failed":
            stats.failed += 1
            stats.failed_names.append(item.path.name)
            log(f"  failed: {doc.error_message}")
            return names, hashes
        stats.ingested += 1
        stats.ingested_names.append(item.path.name)
        log(f"  status={doc.processing_status} chunks={doc.chunk_count}")
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        names, hashes = await _existing_baseline(db)
        stats.failed += 1
        stats.failed_names.append(item.path.name)
        log(f"  failed: {exc}")
    return names, hashes


async def _wipe_baseline_if_requested(
    db: AsyncSession,
    *,
    wipe_baseline: bool,
    log: ProgressFn,
    neo4j_driver: Any | None,
) -> None:
    if not wipe_baseline:
        return
    removed = await wipe_baseline_documents(db)
    await db.commit()
    log(f"wiped {removed} baseline knowledge-base documents")
    if neo4j_driver is None:
        return
    try:
        await GraphRAGStore(neo4j_driver).wipe()
        log("wiped Neo4j graph")
    except Exception as exc:  # noqa: BLE001
        log(f"Neo4j wipe skipped: {exc}")


async def sync_mandatory_sources(
    db: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    wipe_baseline: bool = False,
    progress: ProgressFn | None = None,
    neo4j_driver: Any | None = None,
) -> SyncStats:
    """Ingest handbook + ข้อมูลดิบ PDFs. Default skips files already in the baseline."""
    stats = SyncStats()
    log = progress or (lambda message: logger.info(message))
    sources = list_mandatory_sources()
    if not sources:
        log("No PDFs found under documents/sources/")
        return stats
    await _wipe_baseline_if_requested(
        db, wipe_baseline=wipe_baseline, log=log, neo4j_driver=neo4j_driver
    )
    names, hashes = await _existing_baseline(db)
    for item in sources:
        names, hashes = await _sync_one_pdf(
            item, names, hashes, stats, log, db, session_factory
        )
    return stats
