"""Seed from raw procurement PDFs + GraphRAG.

Usage (from app/backend/ on the host):

  set POSTGRES_HOST=127.0.0.1
  set LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
  set MONGO_URI=mongodb://127.0.0.1:27017
  set NEO4J_URI=bolt://127.0.0.1:7687
  python -m app.seed_raw_docs

Default is incremental (new/changed PDFs only). Use --wipe-baseline to replace
the shared corpus without deleting officer private uploads.

Does not ingest documents/knowledge-base JSON extracts. Does not wipe demo users.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.domain.corpus import list_mandatory_sources
from app.infra import set_mongo_client, set_neo4j_driver, set_session_factory
from app.rag.seed_corpus import sync_mandatory_sources
from app.storage.mongo_store import OriginalDocumentStore

_HOST_HINT = (
    "Seed raw PDFs from the host (Thai bind-mounts often raise OSError [Errno 5]):\n"
    "  set POSTGRES_HOST=127.0.0.1\n"
    "  set LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1\n"
    "  set MONGO_URI=mongodb://127.0.0.1:27017\n"
    "  set NEO4J_URI=bolt://127.0.0.1:7687\n"
    "  python -m app.seed_raw_docs\n"
    "  python -m app.seed_raw_docs --wipe-baseline"
)


def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(message.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def list_raw_pdfs() -> list[Path]:
    return [item.path for item in list_mandatory_sources()]


async def run_seed(*, wipe_baseline: bool = False) -> None:
    sources = list_mandatory_sources()
    if not sources:
        _safe_print(_HOST_HINT)
        _safe_print("No PDFs found under documents/sources/")
        return

    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_size=5)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    set_session_factory(factory)

    mongo = None
    try:
        from pymongo import MongoClient

        mongo = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=8000)
        mongo.admin.command("ping")
        set_mongo_client(mongo)
        if wipe_baseline:
            OriginalDocumentStore(mongo).wipe_baseline()
            _safe_print("wiped MongoDB baseline originals")
    except Exception as exc:  # noqa: BLE001
        _safe_print(f"MongoDB unavailable: {exc}")

    driver = None
    try:
        from neo4j import AsyncGraphDatabase

        driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
        )
        await driver.verify_connectivity()
        set_neo4j_driver(driver)
    except Exception as exc:  # noqa: BLE001
        _safe_print(f"Neo4j unavailable: {exc}")
        driver = None

    async with factory() as db:
        stats = await sync_mandatory_sources(
            db,
            factory,
            wipe_baseline=wipe_baseline,
            progress=_safe_print,
            neo4j_driver=driver,
        )
        await db.commit()

    if driver is not None:
        await driver.close()
    if mongo is not None:
        mongo.close()
    await engine.dispose()
    _safe_print(
        f"seed_raw_docs complete ingested={stats.ingested} "
        f"skipped={stats.skipped} failed={stats.failed} "
        f"(scanned {len(sources)} PDFs)"
    )


async def wipe_and_seed() -> None:
    """Replace baseline corpus (used by S3 sync). Does not delete user uploads."""
    await run_seed(wipe_baseline=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed mandatory procurement PDFs into pgvector")
    parser.add_argument(
        "--wipe-baseline",
        action="store_true",
        help="Replace shared corpus; keep officer private documents",
    )
    args = parser.parse_args()
    asyncio.run(run_seed(wipe_baseline=args.wipe_baseline))


if __name__ == "__main__":
    main()
