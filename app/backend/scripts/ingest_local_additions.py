"""Additive host ingest for this machine. Does not wipe the baseline.

Reads PDFs from the host (Thai paths fail inside the container). Embeds into
the Compose pgvector database. Does not call seed_kb and does not embed
*_tor_extract.json.

The rate PDF is deleted from the ownerless baseline first, then ingested
again so table-aware chunks replace the previous text-only chunks.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.domain.corpus import (
    GROUP_MANDATORY_RAW,
    GROUP_PROCUREMENT_JUDGMENTS,
    CorpusFile,
    list_mandatory_sources,
)
from app.infra import set_mongo_client, set_neo4j_driver, set_session_factory
from app.models.kb_chunk import KBChunk
from app.models.knowledge_base_document import KnowledgeBaseDocument
from app.rag.document_pipeline import ingest_file_bytes
from app.rag.graph_store import GraphRAGStore
from app.rag.seed_corpus import sha256_bytes
from app.storage.mongo_store import OriginalDocumentStore

RATE_PDF_NAME = "อัตราค่าจ้างที่ปรึกษา ประชาสัมพันธ์ อบรม .pdf"
_RAW_DIR_NAME = "ข้อมูลดิบ"
_JUDGMENT_DIR_NAME = "คำพิพากษา"


def _safe_print(message: str) -> None:
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(
            message.encode(encoding, errors="replace").decode(encoding, errors="replace"),
            flush=True,
        )


def _require_loopback_host() -> None:
    settings = get_settings()
    host = (settings.postgres_host or "").strip().lower()
    if host not in {"127.0.0.1", "localhost"}:
        raise SystemExit(
            "Refusing ingest: POSTGRES_HOST must be 127.0.0.1 on this machine. "
            "This script does not target EC2."
        )


def _folder_kind(path: Path) -> str:
    parts = set(path.parts)
    if _JUDGMENT_DIR_NAME in parts:
        return "judgment"
    if _RAW_DIR_NAME in parts:
        return "raw"
    return "other"


async def _baseline_index(db: AsyncSession) -> tuple[set[str], set[str]]:
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


async def _delete_ownerless_named(
    db: AsyncSession,
    name: str,
    *,
    store: OriginalDocumentStore | None,
    graph: GraphRAGStore | None,
) -> int:
    stored_name = name[:500]
    result = await db.execute(
        select(KnowledgeBaseDocument).where(
            KnowledgeBaseDocument.owner_id.is_(None),
            KnowledgeBaseDocument.name == stored_name,
        )
    )
    documents = list(result.scalars().all())
    for document in documents:
        await db.execute(delete(KBChunk).where(KBChunk.document_id == document.id))
        if store is not None:
            try:
                store.delete_file(document.mongo_gridfs_id)
            except Exception as exc:  # noqa: BLE001
                _safe_print(f"  mongo delete skipped for {name}: {exc}")
        if graph is not None:
            try:
                await graph.delete_document(str(document.id))
            except Exception as exc:  # noqa: BLE001
                _safe_print(f"  graph delete skipped for {name}: {exc}")
        await db.delete(document)
    if documents:
        await db.commit()
    return len(documents)


async def _ingest_one(
    db: AsyncSession,
    session_factory: async_sessionmaker[AsyncSession],
    path: Path,
    *,
    corpus_group: str,
) -> str:
    data = path.read_bytes()
    digest = sha256_bytes(data)
    document = await ingest_file_bytes(
        db=db,
        filename=path.name,
        content=data,
        mime_type="application/pdf",
        scope="baseline",
        owner_id=None,
        session_factory=session_factory,
        corpus_group=corpus_group,
        content_sha256=digest,
        extract_graph=False,
    )
    await db.commit()
    return f"{document.processing_status} chunks={document.chunk_count}"


class _Tally:
    def __init__(self) -> None:
        self.ingested = 0
        self.skipped = 0
        self.failed = 0
        self.replaced_rate = 0


def _connect_mongo(settings):
    try:
        from pymongo import MongoClient

        mongo = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=8000)
        mongo.admin.command("ping")
        set_mongo_client(mongo)
        store = OriginalDocumentStore(mongo)
        _safe_print("mongo up")
        return mongo, store
    except Exception as exc:  # noqa: BLE001
        _safe_print(f"MongoDB unavailable: {exc}")
        return None, None


async def _connect_neo4j(settings):
    try:
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        await driver.verify_connectivity()
        set_neo4j_driver(driver)
        graph = GraphRAGStore(driver)
        _safe_print("neo4j up")
        return driver, graph
    except Exception as exc:  # noqa: BLE001
        _safe_print(f"Neo4j unavailable: {exc}")
        return None, None


def _corpus_group_for(item: CorpusFile, kind: str) -> str:
    if kind == "judgment":
        return GROUP_PROCUREMENT_JUDGMENTS
    return item.group


def _already_loaded(digest: str, name: str, names: set[str], hashes: set[str]) -> bool:
    return digest in hashes or name in names


async def _refresh_other_copy(
    db: AsyncSession,
    item: CorpusFile,
    digest: str,
    names: set[str],
    hashes: set[str],
    *,
    store: OriginalDocumentStore | None,
    graph: GraphRAGStore | None,
) -> tuple[bool, set[str], set[str]]:
    if digest in hashes:
        _safe_print(f"skip unchanged {item.path.name}")
        return True, names, hashes
    if item.path.name in names:
        removed_other = await _delete_ownerless_named(
            db, item.path.name, store=store, graph=graph
        )
        _safe_print(f"replaced changed {item.path.name} removed={removed_other}")
        names, hashes = await _baseline_index(db)
    return False, names, hashes


async def _commit_source(
    db: AsyncSession,
    factory: async_sessionmaker[AsyncSession],
    item: CorpusFile,
    data: bytes,
    digest: str,
    group: str,
    names: set[str],
    hashes: set[str],
    tally: _Tally,
) -> tuple[set[str], set[str]]:
    _safe_print(f"ingest [{group}] {item.path.name} ({len(data)} bytes)")
    try:
        status = await _ingest_one(db, factory, item.path, corpus_group=group)
        tally.ingested += 1
        names.add(item.path.name[:500])
        hashes.add(digest)
        _safe_print(f"  {status}")
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        tally.failed += 1
        names, hashes = await _baseline_index(db)
        _safe_print(f"  FAILED {item.path.name}: {exc}")
    return names, hashes


async def _ingest_one_source(
    db: AsyncSession,
    factory: async_sessionmaker[AsyncSession],
    item: CorpusFile,
    *,
    store: OriginalDocumentStore | None,
    graph: GraphRAGStore | None,
    names: set[str],
    hashes: set[str],
    tally: _Tally,
) -> tuple[set[str], set[str]]:
    if item.path.name == RATE_PDF_NAME:
        return names, hashes
    kind = _folder_kind(item.path)
    try:
        data = item.path.read_bytes()
    except OSError as exc:
        tally.failed += 1
        _safe_print(f"FAILED read {item.path.name}: {exc}")
        return names, hashes
    digest = sha256_bytes(data)
    group = _corpus_group_for(item, kind)
    if kind == "other":
        skipped, names, hashes = await _refresh_other_copy(
            db, item, digest, names, hashes, store=store, graph=graph
        )
        if skipped:
            tally.skipped += 1
            return names, hashes
    elif _already_loaded(digest, item.path.name, names, hashes):
        tally.skipped += 1
        _safe_print(f"skip [{group}] {item.path.name}")
        return names, hashes
    return await _commit_source(
        db, factory, item, data, digest, group, names, hashes, tally
    )


async def _reingest_rate(
    db: AsyncSession,
    factory: async_sessionmaker[AsyncSession],
    sources: list[CorpusFile],
    store: OriginalDocumentStore | None,
    graph: GraphRAGStore | None,
    tally: _Tally,
) -> tuple[set[str], set[str]]:
    removed = await _delete_ownerless_named(
        db, RATE_PDF_NAME, store=store, graph=graph
    )
    _safe_print(f"deleted rate baseline documents={removed}")
    rate_items = [item for item in sources if item.path.name == RATE_PDF_NAME]
    if not rate_items:
        raise SystemExit(f"Rate PDF not found: {RATE_PDF_NAME}")
    try:
        status = await _ingest_one(
            db,
            factory,
            rate_items[0].path,
            corpus_group=GROUP_MANDATORY_RAW,
        )
        tally.replaced_rate = 1
        tally.ingested += 1
        _safe_print(f"reingested rate pdf {status}")
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        tally.failed += 1
        _safe_print(f"FAILED rate pdf: {exc}")
    return await _baseline_index(db)


async def run_ingest() -> None:
    _require_loopback_host()
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_size=4)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    set_session_factory(factory)
    mongo, store = _connect_mongo(settings)
    driver, graph = await _connect_neo4j(settings)
    sources = list_mandatory_sources()
    if not sources:
        raise SystemExit("No mandatory PDFs found")
    tally = _Tally()
    async with factory() as db:
        names, hashes = await _reingest_rate(db, factory, sources, store, graph, tally)
        for item in sources:
            names, hashes = await _ingest_one_source(
                db,
                factory,
                item,
                store=store,
                graph=graph,
                names=names,
                hashes=hashes,
                tally=tally,
            )
    if driver is not None:
        await driver.close()
    if mongo is not None:
        mongo.close()
    await engine.dispose()
    _safe_print(
        "ingest_local_additions complete "
        f"ingested={tally.ingested} skipped={tally.skipped} failed={tally.failed} "
        f"rate_replaced={tally.replaced_rate} scanned={len(sources)}"
    )
    if tally.failed:
        raise SystemExit(1)



def main() -> None:
    asyncio.run(run_ingest())


if __name__ == "__main__":
    main()
