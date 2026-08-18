"""Live LM Studio coverage against the host OpenAI-compatible server on :1234.

These tests fail clearly when LM Studio is down. They do not skip.
"""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from openai import OpenAI

from app.providers.constants import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
)

_CANDIDATE_BASES = (
    "http://127.0.0.1:1234/v1",
    "http://host.docker.internal:1234/v1",
)


def _require_lm_studio() -> str:
    errors: list[str] = []
    for base in _CANDIDATE_BASES:
        try:
            response = httpx.get(f"{base}/models", timeout=5.0)
            response.raise_for_status()
            return base
        except Exception as exc:
            errors.append(f"{base}: {exc}")
    pytest.fail(
        "LM Studio is not reachable on port 1234. Start the local server and load "
        f"{DEFAULT_CHAT_MODEL} plus {DEFAULT_EMBEDDING_MODEL}. "
        + " | ".join(errors)
    )


@pytest.mark.integration
@pytest.mark.live_llm
def test_live_lm_studio_models_endpoint():
    base = _require_lm_studio()
    payload = httpx.get(f"{base}/models", timeout=5.0).json()
    ids = [item.get("id") for item in payload.get("data", [])]
    assert ids, f"LM Studio returned no models at {base}"


@pytest.mark.integration
@pytest.mark.live_llm
def test_live_embeddinggemma_dimension_is_768():
    base = _require_lm_studio()
    client = OpenAI(base_url=base, api_key="not-needed", timeout=60.0)
    result = client.embeddings.create(
        model=DEFAULT_EMBEDDING_MODEL,
        input="ทดสอบการจัดซื้อจัดจ้างภาครัฐ",
    )
    vector = result.data[0].embedding
    assert len(vector) == EMBEDDING_DIMENSIONS, (
        f"Expected {EMBEDDING_DIMENSIONS}-d EmbeddingGemma vector, got {len(vector)}"
    )


@pytest.mark.integration
@pytest.mark.live_llm
def test_live_gemma_chat_tiny_prompt():
    base = _require_lm_studio()
    client = OpenAI(base_url=base, api_key="not-needed", timeout=180.0)
    result = client.chat.completions.create(
        model=DEFAULT_CHAT_MODEL,
        messages=[{"role": "user", "content": "ตอบคำเดียว: สวัสดี"}],
        max_tokens=16,
        temperature=0,
    )
    content = (result.choices[0].message.content or "").strip()
    assert content, "Gemma returned an empty chat completion"


@pytest.mark.integration
@pytest.mark.live_llm
def test_live_lm_studio_loads_chat_and_embedding_models():
    base = _require_lm_studio()
    payload = httpx.get(f"{base}/models", timeout=5.0).json()
    ids = [item.get("id") or "" for item in payload.get("data", [])]
    assert any(DEFAULT_CHAT_MODEL in model_id for model_id in ids), (
        f"Chat model {DEFAULT_CHAT_MODEL} not loaded. Models: {ids}"
    )
    assert any(DEFAULT_EMBEDDING_MODEL in model_id for model_id in ids), (
        f"Embedding model {DEFAULT_EMBEDDING_MODEL} not loaded. Models: {ids}"
    )


@pytest.mark.integration
@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_live_embedding_provider_batch_is_768():
    from app.providers.embedding.qwen3_provider import Qwen3LocalEmbeddingProvider

    base = _require_lm_studio()
    provider = Qwen3LocalEmbeddingProvider(
        base_url=base,
        model=DEFAULT_EMBEDDING_MODEL,
        timeout=60.0,
    )
    vectors = await provider.embed_documents(
        ["วิธีประกาศเชิญชวนทั่วไป", "วิธีคัดเลือก", "วิธีเฉพาะเจาะจง"]
    )
    assert len(vectors) == 3
    assert all(len(vector) == EMBEDDING_DIMENSIONS for vector in vectors)


@pytest.mark.integration
@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_live_gemma_answers_thai_procurement_prompt():
    from app.providers.llm.lm_studio_provider import LMStudioLocalProvider

    base = _require_lm_studio()
    provider = LMStudioLocalProvider(
        base_url=base,
        model_name=DEFAULT_CHAT_MODEL,
        timeout=180.0,
    )
    response = await provider.invoke(
        [
            {
                "role": "system",
                "content": "คุณเป็นผู้ช่วยจัดซื้อจัดจ้างภาครัฐ ตอบสั้นเป็นภาษาไทย",
            },
            {
                "role": "user",
                "content": "ชื่อวิธีการจัดซื้อจัดจ้าง 3 วิธีตาม พ.ร.บ. 2560 คืออะไร ตอบสั้นๆ",
            },
        ],
        max_tokens=1024,
        temperature=0,
    )
    text = (response.content or "").strip()
    assert text, "Gemma returned an empty procurement answer"
    thai = sum(1 for char in text if "\u0e00" <= char <= "\u0e7f")
    assert thai >= 8, f"Expected Thai in the reply, got: {text!r}"


@pytest.mark.integration
@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_live_gemma_uses_retrieved_regulation_chunk():
    from app.providers.embedding.qwen3_provider import Qwen3LocalEmbeddingProvider
    from app.providers.llm.lm_studio_provider import LMStudioLocalProvider
    from app.rag.ingestion import ingest_document
    from app.rag.retrieval import RAGRetriever
    from tests.test_property_embedding_round_trip import InMemoryVectorStore

    repo = Path(__file__).resolve().parents[3]
    pdf = (
        repo
        / "documents"
        / "sources"
        / "การจัดซื้อจัดจ้าง"
        / "ข้อมูลดิบ"
        / "กฎกระทรวงกำหนดวงเงินการจัดซื้อจัดจ้างพัสดุโดยวิธีเฉพาะเจาะจงวงเงิน.pdf"
    )
    assert pdf.is_file(), f"Missing {pdf}"
    base = _require_lm_studio()
    embedding = Qwen3LocalEmbeddingProvider(
        base_url=base,
        model=DEFAULT_EMBEDDING_MODEL,
        timeout=60.0,
    )
    store = InMemoryVectorStore()
    ingested = await ingest_document(
        document_id="aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
        document_name=pdf.stem,
        file_path=str(pdf),
        mime_type="application/pdf",
        embedding_provider=embedding,
        vector_store_provider=store,
        session=None,
    )
    assert ingested.success, ingested.error_message
    retrieved = await RAGRetriever(embedding, store).retrieve(
        "วงเงินจัดซื้อจัดจ้างโดยวิธีเฉพาะเจาะจง",
        top_k=2,
    )
    assert retrieved.actual_count >= 1
    context = retrieved.chunks[0].text[:1200]
    provider = LMStudioLocalProvider(
        base_url=base,
        model_name=DEFAULT_CHAT_MODEL,
        timeout=180.0,
    )
    response = await provider.invoke(
        [
            {
                "role": "system",
                "content": "ตอบจากบริบทที่ให้เท่านั้น เป็นภาษาไทยสั้นๆ",
            },
            {
                "role": "user",
                "content": f"บริบท:\n{context}\n\nคำถาม: เอกสารนี้เกี่ยวกับวิธีใด",
            },
        ],
        max_tokens=1024,
        temperature=0,
    )
    text = (response.content or "").strip()
    assert text
    thai = sum(1 for char in text if "\u0e00" <= char <= "\u0e7f")
    assert thai >= 8, f"Expected Thai grounded reply, got: {text!r}"


@pytest.mark.integration
@pytest.mark.live_llm
@pytest.mark.asyncio
async def test_live_gemma_extracts_graph_json():
    from app.providers.llm.lm_studio_provider import LMStudioLocalProvider
    from app.rag.graph_extract import extract_graph_from_text

    base = _require_lm_studio()
    provider = LMStudioLocalProvider(
        base_url=base,
        model_name=DEFAULT_CHAT_MODEL,
        timeout=180.0,
    )
    nodes, rels = await extract_graph_from_text(
        provider,
        "พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ พ.ศ. 2560 มาตรา 65 "
        "กำหนดหลักเกณฑ์การพิจารณาคัดเลือกข้อเสนอ สำหรับหมวด TOR หลักเกณฑ์คัดเลือก (s11) "
        "และค่าปรับตามระเบียบเกี่ยวข้องกับหมวดอัตราค่าปรับ (s10)",
        document_name="พรบ2560",
    )
    labels = {item.get("label") for item in nodes if isinstance(item, dict)}
    assert labels & {"Law", "Article", "TorSlot", "Concept", "Document"}, (
        f"Gemma did not return graph nodes. nodes={nodes!r} rels={rels!r}"
    )

