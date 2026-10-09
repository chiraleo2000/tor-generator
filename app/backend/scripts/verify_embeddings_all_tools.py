"""Live check that EmbeddingGemma 2 powers every RAG tool path in the app.

Covers:
  1) Provider embed_query (dims + model id + 4096 truncate)
  2) Shared hybrid_retrieve (KB / draft / intake / review backbone)
  3) Draft section RAG pack (draft_chat_service)
  4) Intake fill-reference style retrieve
  5) Law-review multi-query retrieve
  6) KB chat multi-query retrieve helper
  7) MCP retrieve status (fail-open OK)

Run:
  docker compose -p tor-app --env-file .env exec backend \\
    python -m scripts.verify_embeddings_all_tools
"""

from __future__ import annotations

import asyncio
import sys
import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.infra import set_session_factory
from app.llm_tokens import EMBEDDING_MAX_TOKENS, chars_for_tokens, truncate_for_embedding
from app.providers.constants import DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSIONS
from app.providers.factory import ProviderFactory
from app.rag.hybrid import hybrid_retrieve, hybrid_retrieve_multi, unpack_hybrid
from app.rag.law_review import collect_law_review_chunks
from app.services.draft_chat_service import _hybrid_rag_pack


def _out(message: str) -> None:
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "ascii"
        print(
            message.encode(encoding, errors="replace").decode(encoding, errors="replace"),
            flush=True,
        )


def _ok(name: str, detail: str = "") -> None:
    _out(f"PASS  {name}" + (f" — {detail}" if detail else ""))


def _fail(name: str, detail: str) -> None:
    _out(f"FAIL  {name} — {detail}")


async def _kb_counts(engine) -> tuple[int, int]:
    async with engine.connect() as conn:
        docs = (
            await conn.execute(text("SELECT count(*) FROM knowledge_base_documents"))
        ).scalar()
        embedded = (
            await conn.execute(
                text("SELECT count(*) FROM kb_chunks WHERE embedding IS NOT NULL")
            )
        ).scalar()
    return int(docs or 0), int(embedded or 0)


async def check_provider() -> tuple[bool, Any]:
    factory = ProviderFactory()
    emb = factory.get_embedding()
    model = str(getattr(emb, "model", "") or "")
    if model != "text-embedding-embeddinggemma-2":
        _fail("provider.model", f"got {model!r}")
        return False, emb
    if DEFAULT_EMBEDDING_MODEL != "text-embedding-embeddinggemma-2":
        _fail("constants.default", f"got {DEFAULT_EMBEDDING_MODEL!r}")
        return False, emb
    if EMBEDDING_MAX_TOKENS != 4_096:
        _fail("constants.max_tokens", f"got {EMBEDDING_MAX_TOKENS}")
        return False, emb

    short = await emb.embed_query("ทดสอบฝังเวกเตอร์ TOR EmbeddingGemma 2")
    if len(short) != EMBEDDING_DIMENSIONS:
        _fail("provider.dims", f"len={len(short)} expected={EMBEDDING_DIMENSIONS}")
        return False, emb

    long_raw = "ก" * (chars_for_tokens(EMBEDDING_MAX_TOKENS) + 200)
    clipped = truncate_for_embedding(long_raw)
    if len(clipped) != chars_for_tokens(EMBEDDING_MAX_TOKENS):
        _fail("truncate.length", f"len={len(clipped)}")
        return False, emb
    long_vec = await emb.embed_query(clipped)
    if len(long_vec) != EMBEDDING_DIMENSIONS:
        _fail("provider.long_dims", f"len={len(long_vec)}")
        return False, emb

    _ok(
        "provider.embed_query",
        f"model={model} dims={len(short)} max_tokens={EMBEDDING_MAX_TOKENS}",
    )
    return True, emb


async def check_hybrid() -> bool:
    started = time.perf_counter()
    payload = await hybrid_retrieve(
        "คุณสมบัติผู้เสนอราคา พ.ร.บ. การจัดซื้อจัดจ้าง 2560",
        search_scope="global",
        top_k=5,
    )
    result, citations, _graph, mcp_degraded = unpack_hybrid(payload)
    hits = list(result.chunks or [])
    elapsed = time.perf_counter() - started
    if len(hits) < 1:
        _fail("hybrid_retrieve", "no hits")
        return False
    top = hits[0]
    _ok(
        "hybrid_retrieve",
        f"hits={len(hits)} score={top.score} src={top.source_document} "
        f"citations={len(citations)} mcp_degraded={mcp_degraded} {elapsed:.2f}s",
    )
    return True


async def check_draft_rag() -> bool:
    pack = await _hybrid_rag_pack(
        "ขอบเขตงาน จัดซื้อจัดจ้างภาครัฐ พ.ร.บ. 2560",
        user_id=None,
        section_relevance="s4",
        top_k=6,
        chunk_n=4,
        chunk_chars=400,
    )
    if len(pack.strip()) < 40:
        _fail("draft_rag_pack", f"too short ({len(pack)})")
        return False
    _ok("draft_rag_pack", f"chars={len(pack)}")
    return True


async def check_intake_style() -> bool:
    payload = await hybrid_retrieve(
        "มาตรฐานกลาง คุณสมบัติผู้เสนอราคา ทุนจดทะเบียน",
        search_scope="global",
        top_k=3,
    )
    result, _, _, _ = unpack_hybrid(payload)
    hits = list(result.chunks or [])
    if not hits:
        _fail("intake_retrieve", "no hits")
        return False
    _ok("intake_retrieve", f"hits={len(hits)} score={hits[0].score}")
    return True


async def check_law_review() -> bool:
    chunks = await collect_law_review_chunks("hire_develop")
    if len(chunks) < 3:
        _fail("law_review_retrieve", f"only {len(chunks)} chunks")
        return False
    _ok("law_review_retrieve", f"chunks={len(chunks)} sample={chunks[0].source_document}")
    return True


async def check_kb_chat_multi() -> bool:
    payload = await hybrid_retrieve_multi(
        "วิธีเฉพาะเจาะจง วงเงินจัดซื้อจัดจ้างไม่เกินห้าหมื่นบาท",
        search_scope="global",
        top_k=4,
    )
    result, citations, _, mcp_degraded = unpack_hybrid(payload)
    hits = list(result.chunks or [])
    if not hits:
        _fail("kb_chat_multi_retrieve", "no hits")
        return False
    _ok(
        "kb_chat_multi_retrieve",
        f"hits={len(hits)} citations={len(citations)} mcp_degraded={mcp_degraded}",
    )
    return True


async def main() -> None:
    settings = get_settings()
    _out("=== EmbeddingGemma 2 — all-tools check ===")
    _out(f"env_model={settings.lm_studio_embedding_model}")
    _out(f"embedding_provider={settings.embedding_provider}")

    engine = create_async_engine(settings.database_url)
    docs, embedded = await _kb_counts(engine)
    _out(f"kb_docs={docs} kb_embedded_chunks={embedded}")
    if docs < 1 or embedded < 1:
        await engine.dispose()
        raise SystemExit("KB empty — run seed_raw_docs --wipe-baseline first")

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    set_session_factory(factory)

    results: list[bool] = []
    ok, _ = await check_provider()
    results.append(ok)
    results.append(await check_hybrid())
    results.append(await check_draft_rag())
    results.append(await check_intake_style())
    results.append(await check_law_review())
    results.append(await check_kb_chat_multi())

    await engine.dispose()
    passed = sum(1 for item in results if item)
    total = len(results)
    _out(f"\nSUMMARY {passed}/{total}")
    if passed != total:
        raise SystemExit(1)
    _out("ALL_TOOLS_EMBEDDING_OK")


if __name__ == "__main__":
    asyncio.run(main())
