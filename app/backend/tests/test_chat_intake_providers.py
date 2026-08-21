"""Chat rooms, coverage, graph JSON, and cloud provider factory tests."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.domain.slots import FACT_REQUIRED_SLOTS
from app.rag.graph_extract import parse_json_object
from app.services.intake_service import coverage_table, empty_slot_map, ready_criteria_met


def test_parse_json_object_extracts_blob():
    payload = parse_json_object('คำอธิบาย\n{"nodes":[{"id":"a"}],"rels":[]}\nจบ')
    assert payload["nodes"][0]["id"] == "a"


def test_parse_json_lenient_strips_fence():
    from app.rag.graph_extract import parse_json_lenient

    payload = parse_json_lenient('```json\n{"ok": true}\n```')
    assert payload["ok"] is True


def test_owner_filter_dict_scopes():
    from app.rag.hybrid import owner_filter_dict

    both = owner_filter_dict(user_id="abc", search_scope="both")
    assert both["search_scope"] == "both"
    assert both["owner_user_id"] == "abc"
    mine = owner_filter_dict(user_id="abc", search_scope="mine")
    assert mine["search_scope"] == "mine"
    assert mine["owner_user_id"] == "abc"
    orphan = owner_filter_dict(user_id=None, search_scope="mine")
    assert orphan == {"search_scope": "mine"}
    assert "owner_user_id" not in orphan


@pytest.mark.asyncio
async def test_hybrid_retrieve_degraded_without_session_factory():
    from app import infra as runtime
    from app.rag import hybrid as hybrid_mod

    previous = runtime.session_factory
    runtime.set_session_factory(None)
    try:
        result, citations, degraded = await hybrid_mod.hybrid_retrieve("งวดจ่าย")
    finally:
        runtime.set_session_factory(previous)
    assert degraded is True
    assert result.actual_count == 0
    assert citations == []


def test_empty_slot_map_has_scope_subs():
    slots = empty_slot_map()
    assert "s1" in slots
    assert "s4.1" in slots
    assert "s4.14" in slots
    assert slots["s1"]["status"] == "gap"


def test_ready_criteria_requires_facts_not_reference_only():
    slots = empty_slot_map()
    for key in FACT_REQUIRED_SLOTS:
        slots[key] = {"content": "x" * 20, "status": "reference_only", "sources": ["พ.ร.บ."]}
    assert ready_criteria_met(slots) is False
    for key in FACT_REQUIRED_SLOTS:
        slots[key]["status"] = "filled"
    assert ready_criteria_met(slots) is True


def test_coverage_table_flags_fact_required():
    rows = coverage_table(empty_slot_map())
    s1 = next(item for item in rows if item["key"] == "s1")
    assert s1["fact_required"] is True
    assert s1["filled"] is False


def test_chat_room_model_defaults():
    from app.models.chat_room import ChatRoom

    room = ChatRoom(user_id=uuid.uuid4(), kind="kb", title="ทดสอบ")
    assert room.kind == "kb"
    assert room.title == "ทดสอบ"


def test_kb_document_owner_id_nullable():
    from app.models.knowledge_base_document import KnowledgeBaseDocument

    doc = KnowledgeBaseDocument(
        name="กลาง",
        category="law",
        file_type="pdf",
        storage_path="/a.pdf",
        owner_id=None,
        scope="baseline",
    )
    assert doc.owner_id is None
    assert doc.scope == "baseline"


def test_factory_accepts_new_cloud_providers():
    from app.providers.factory import VALID_EMBEDDING_PROVIDERS, VALID_LLM_PROVIDERS

    assert "bedrock" in VALID_LLM_PROVIDERS
    assert "azure_foundry" in VALID_LLM_PROVIDERS
    assert "openai_compatible" in VALID_LLM_PROVIDERS
    assert "bedrock" in VALID_EMBEDDING_PROVIDERS


def test_factory_creates_openai_compatible_llm():
    from app.config import Settings
    from app.providers.factory import ProviderFactory
    from app.providers.llm.openai_provider import OpenAILLMProvider

    settings = Settings(
        deployment_mode="hybrid",
        llm_provider="openai_compatible",
        embedding_provider="local",
        openai_compatible_base_url="http://127.0.0.1:9999/v1",
        openai_compatible_api_key="sk-test",
        openai_compatible_model="demo",
        lm_studio_base_url="http://127.0.0.1:1234/v1",
        lm_studio_model="google/gemma-4-e4b",
        lm_studio_embedding_model="text-embedding-embeddinggemma-300m",
        jwt_secret="changeme_jwt_secret_at_least_32_characters_long",
    )
    factory = ProviderFactory(settings=settings)
    llm = factory.get_llm()
    assert isinstance(llm, OpenAILLMProvider)


@pytest.mark.asyncio
async def test_bedrock_llm_uses_converse():
    from app.providers.llm.bedrock_provider import BedrockLLMProvider

    fake_client = MagicMock()
    fake_client.converse.return_value = {
        "output": {"message": {"content": [{"text": "สวัสดี"}]}},
        "usage": {"inputTokens": 1, "outputTokens": 2, "totalTokens": 3},
        "stopReason": "end_turn",
    }
    fake_boto3 = MagicMock()
    fake_boto3.client.return_value = fake_client
    with patch.dict("sys.modules", {"boto3": fake_boto3}):
        provider = BedrockLLMProvider(region="ap-southeast-1", model_id="demo-model")
        response = await provider.invoke([{"role": "user", "content": "hi"}])
    assert response.content == "สวัสดี"


def test_persist_keys_for_section_maps_scope_subkeys():
    from app.api.v1.endpoints.drafting import _persist_keys_for_section

    assert _persist_keys_for_section("s1") == ("s1", None)
    assert _persist_keys_for_section("s4.1") == ("s4", "s4.1")
    assert _persist_keys_for_section("4.2") == ("s4", "s4.2")


def test_fit_bedrock_embedding_dimensions():
    from app.providers.constants import EMBEDDING_DIMENSIONS
    from app.providers.embedding.bedrock_provider import _fit_dimensions

    short = _fit_dimensions([1.0, 2.0], size=4)
    assert len(short) == 4
    long = _fit_dimensions([0.0] * 1024)
    assert len(long) == EMBEDDING_DIMENSIONS
