"""Audit KB docs that look incomplete / thin (chunk + char coverage)."""

from __future__ import annotations

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings


def _safe(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_size=2)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        rows = (
            await db.execute(
                text(
                    """
                    SELECT
                      d.name,
                      d.chunk_count,
                      COALESCE((
                        SELECT SUM(length(c.chunk_text))
                        FROM kb_chunks c WHERE c.document_id = d.id
                      ), 0) AS chars
                    FROM knowledge_base_documents d
                    WHERE d.processing_status = 'completed'
                    ORDER BY d.chunk_count ASC, chars ASC
                    """
                )
            )
        ).fetchall()
        _safe(f"completed_docs={len(rows)}")
        _safe("--- thin (<=2 chunks OR <1500 chars) ---")
        thin = 0
        for r in rows:
            name = (r.name or "").lstrip("\ufeff")
            if r.chunk_count <= 2 or int(r.chars or 0) < 1500:
                thin += 1
                _safe(f"chunks={r.chunk_count:3d} chars={int(r.chars):6d}  {name[:100]}")
        _safe(f"thin_count={thin}")
        fail = (
            await db.execute(
                text(
                    """
                    SELECT name, processing_status, chunk_count
                    FROM knowledge_base_documents
                    WHERE processing_status != 'completed' OR chunk_count = 0
                    ORDER BY name
                    """
                )
            )
        ).fetchall()
        _safe("--- incomplete/failed ---")
        if not fail:
            _safe("(none)")
        for r in fail:
            name = (r.name or "").lstrip("\ufeff")
            _safe(f"{r.processing_status} chunks={r.chunk_count}  {name[:100]}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
