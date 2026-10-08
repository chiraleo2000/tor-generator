"""Verify hybrid RAG retrieve against the live EmbeddingGemma index.

Usage (host, with services on localhost ports):

  set POSTGRES_HOST=127.0.0.1
  set LM_STUDIO_BASE_URL=http://127.0.0.1:1234/v1
  python -m scripts.verify_rag_embeddings

From Docker:

  docker compose -p tor-app --env-file .env exec backend \\
    python -m scripts.verify_rag_embeddings
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.infra import set_session_factory
from app.providers.constants import DEFAULT_EMBEDDING_MODEL
from app.providers.factory import ProviderFactory
from app.rag.hybrid import hybrid_retrieve, unpack_hybrid

QUERIES = (
    "คุณสมบัติของผู้เสนอราคา ตาม พ.ร.บ. การจัดซื้อจัดจ้าง พ.ศ. 2560",
    "วงเงินจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง",
    "อัตราค่าปรับส่งมอบงานล่าช้า",
    "หลักเกณฑ์ราคากลางการจ้างที่ปรึกษา",
)


def _safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(message.encode(encoding, errors="replace").decode(encoding, errors="replace"))


async def _counts(engine) -> tuple[int, int, int]:
    async with engine.connect() as conn:
        docs = (
            await conn.execute(text("SELECT count(*) FROM knowledge_base_documents"))
        ).scalar()
        chunks = (await conn.execute(text("SELECT count(*) FROM kb_chunks"))).scalar()
        embedded = (
            await conn.execute(
                text("SELECT count(*) FROM kb_chunks WHERE embedding IS NOT NULL")
            )
        ).scalar()
    return int(docs or 0), int(chunks or 0), int(embedded or 0)


async def main() -> None:
    settings = get_settings()
    emb = ProviderFactory().get_embedding()
    _safe_print(f"default_model={DEFAULT_EMBEDDING_MODEL}")
    _safe_print(f"env_model={settings.lm_studio_embedding_model}")
    _safe_print(f"provider_model={getattr(emb, 'model', None)}")

    engine = create_async_engine(settings.database_url)
    docs, chunks, embedded = await _counts(engine)
    _safe_print(f"docs={docs} chunks={chunks} embedded={embedded}")
    if docs < 1 or embedded < 1:
        raise SystemExit("KB is empty — run: python -m app.seed_raw_docs --wipe-baseline")

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    set_session_factory(factory)

    ok = 0
    for question in QUERIES:
        payload = await hybrid_retrieve(question, top_k=5)
        result, citations, graph_degraded, mcp_degraded = unpack_hybrid(payload)
        hits = list(result.chunks or [])
        _safe_print(f"\nQ: {question}")
        _safe_print(
            f"hits={len(hits)} citations={len(citations)} "
            f"graph_degraded={graph_degraded} mcp_degraded={mcp_degraded}"
        )
        if not hits:
            continue
        ok += 1
        for chunk in hits[:2]:
            preview = str(chunk.text or "").replace("\n", " ")[:160]
            _safe_print(f"  score={chunk.score} src={chunk.source_document}")
            _safe_print(f"  {preview}")

    await engine.dispose()
    _safe_print(f"\nqueries_with_hits={ok}/{len(QUERIES)}")
    if ok < len(QUERIES):
        raise SystemExit("some RAG queries returned no hits")
    _safe_print("RAG_OK")


if __name__ == "__main__":
    asyncio.run(main())
