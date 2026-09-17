"""Backfill Neo4j GraphRAG from existing kb_chunks (no re-embed).

Run inside backend container:
  PYTHONPATH=/app python /tmp/backfill_graphrag.py
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app import infra as runtime
from app.config import get_settings
from app.infra import set_neo4j_driver, set_session_factory
from app.models.knowledge_base_document import KnowledgeBaseDocument
from app.providers.factory import ProviderFactory
from app.rag.graph_extract import extract_graph_from_text
from app.rag.graph_store import GraphRAGStore


def _safe_print(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


async def _doc_text(db: AsyncSession, doc_id) -> str:
    rows = (
        await db.execute(
            text(
                "SELECT chunk_text FROM kb_chunks "
                "WHERE document_id = :id ORDER BY chunk_index"
            ),
            {"id": str(doc_id)},
        )
    ).fetchall()
    return "\n\n".join(str(r[0] or "") for r in rows).strip()


async def _already_graphed(driver, document_id: str) -> bool:
    """Skip only if Document exists AND has at least one extracted entity."""
    async with driver.session() as session:
        result = await session.run(
            """
            MATCH (d:Document {id: $id})
            OPTIONAL MATCH (d)-[:CONTAINED_IN|CITES|APPLIES_TO|DEFINES|SUPERSEDES]-(n)
            WHERE NOT n:Document
            RETURN d.id AS id, count(n) AS n
            """,
            id=document_id,
        )
        record = await result.single()
        return bool(record and record["n"] and int(record["n"]) > 0)


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_size=3)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    set_session_factory(factory)

    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
    )
    await driver.verify_connectivity()
    set_neo4j_driver(driver)

    llm = ProviderFactory(settings).get_llm("structured")
    graph = GraphRAGStore(driver)

    async with factory() as db:
        docs = list(
            (
                await db.execute(
                    select(KnowledgeBaseDocument).where(
                        KnowledgeBaseDocument.processing_status == "completed",
                        KnowledgeBaseDocument.chunk_count > 0,
                    )
                )
            ).scalars().all()
        )
        _safe_print(f"GraphRAG backfill for {len(docs)} documents")
        ok = 0
        empty = 0
        failed = 0
        skipped = 0
        for i, doc in enumerate(docs, 1):
            name = (doc.name or str(doc.id)).lstrip("\ufeff")
            doc_id = str(doc.id)
            if await _already_graphed(driver, doc_id):
                _safe_print(f"[{i}/{len(docs)}] skip-done: {name}")
                skipped += 1
                continue
            body = await _doc_text(db, doc.id)
            if len(body) < 40:
                _safe_print(f"[{i}/{len(docs)}] skip-short: {name}")
                empty += 1
                continue
            try:
                nodes, rels = await extract_graph_from_text(
                    llm, body, document_name=name
                )
                await graph.upsert_extraction(
                    document_id=doc_id,
                    document_name=name,
                    nodes=nodes,
                    rels=rels,
                    owner_id=str(doc.owner_id) if doc.owner_id else None,
                    scope=getattr(doc, "scope", None) or "baseline",
                )
                _safe_print(
                    f"[{i}/{len(docs)}] ok: {name} nodes={len(nodes)} rels={len(rels)}"
                )
                ok += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                _safe_print(f"[{i}/{len(docs)}] fail: {name}: {exc}")
        _safe_print(
            f"done ok={ok} skipped={skipped} empty={empty} failed={failed}"
        )

    await driver.close()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
