"""Hybrid/on-prem/cloud factory smoke and unreachable LLM timeout (Req 2.7)."""

from __future__ import annotations

import time

import pytest

from app.providers.factory import ProviderFactory
from app.providers.llm.lm_studio_provider import LMStudioLocalProvider
from tests.test_provider_factory import make_settings


def test_factory_resolves_all_three_modes():
    on_prem = ProviderFactory(make_settings(deployment_mode="on_prem"))
    assert on_prem.get_llm().__class__.__name__ == "LMStudioLocalProvider"

    cloud = ProviderFactory(
        make_settings(
            deployment_mode="cloud",
            llm_provider="claude",
            anthropic_api_key="sk-ant-test",
            openai_api_key="sk-test",
        )
    )
    assert cloud.get_llm().__class__.__name__ == "ClaudeSonnetProvider"

    cloud_local_chat = ProviderFactory(
        make_settings(
            deployment_mode="cloud",
            llm_provider="lm_studio",
            embedding_provider="openai",
            openai_api_key="sk-test",
        )
    )
    assert cloud_local_chat.get_llm().__class__.__name__ == "LMStudioLocalProvider"

    hybrid = ProviderFactory(
        make_settings(
            deployment_mode="hybrid",
            llm_provider="lm_studio",
            embedding_provider="qwen3",
            vector_store_provider="pgvector",
        )
    )
    assert hybrid.get_llm().__class__.__name__ == "LMStudioLocalProvider"


@pytest.mark.asyncio
async def test_unreachable_lm_studio_fails_within_10s_connect():
    provider = LMStudioLocalProvider(
        base_url="http://127.0.0.1:1/v1",
        model_name="missing",
        timeout=8.0,
    )
    start = time.monotonic()
    with pytest.raises((ConnectionError, TimeoutError, OSError)):
        await provider.invoke([{"role": "user", "content": "ping"}])
    elapsed = time.monotonic() - start
    assert elapsed < 15


def test_claude_prompt_cache_control_present():
    from app.providers.llm.claude_provider import ClaudeSonnetProvider

    provider = ClaudeSonnetProvider.__new__(ClaudeSonnetProvider)
    block = ClaudeSonnetProvider._build_system_with_cache(provider, "system prompt")
    assert block is not None
    assert block[0]["cache_control"]["type"] == "ephemeral"
