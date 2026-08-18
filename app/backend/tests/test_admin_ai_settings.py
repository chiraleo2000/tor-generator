"""Unit tests for admin AI settings helpers (masking, validation, merge)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.admin_ai_settings import (
    AiSettingsTest,
    AiSettingsUpdate,
    _embedding_changed,
    _local_base_url,
    _mask_key,
    _merge_saved_payload,
    _merged_settings_dict,
    _overlay_from_merged,
    _public_payload,
    _resolved_local_url,
    _validate_update,
)
from app.config import get_settings
from app.deps import get_current_user, get_db
from app.exceptions import ValidationError
from app.main import app
from app.models.ai_runtime_settings import AiRuntimeSettings
from app.models.user import User
from app.providers.constants import AI_OVERLAY_FIELDS


def _local_body(**overrides) -> AiSettingsUpdate:
    data = {
        "deployment_mode": "on_prem",
        "llm_provider": "lm_studio",
        "embedding_provider": "local",
        "lm_studio_base_url": "http://127.0.0.1:1234/v1",
        "lm_studio_model": "google/gemma-4-e4b",
        "lm_studio_embedding_model": "text-embedding-embeddinggemma-300m",
    }
    data.update(overrides)
    return AiSettingsUpdate(**data)


def test_mask_key_empty():
    assert _mask_key("") == ""
    assert _mask_key(None) == ""


def test_mask_key_keeps_last_four():
    assert _mask_key("sk-abcdefghijklmnopqrstuvwxyz") == "****wxyz"


def test_public_payload_masks_keys_and_sets_flags():
    public = _public_payload(
        {
            "anthropic_api_key": "sk-ant-secret-key",
            "openai_api_key": "",
            "gemini_api_key": "abcd1234",
            "deployment_mode": "on_prem",
        }
    )
    assert public["anthropic_api_key"] == "****-key"
    assert public["anthropic_api_key_set"] is True
    assert public["openai_api_key"] == ""
    assert public["openai_api_key_set"] is False
    assert public["gemini_api_key"] == "****1234"
    assert public["restart_required"] is False
    assert "lm_studio" in public["local_llm_defaults"]


def test_merge_skips_masked_keys():
    merged = _merge_saved_payload(
        {"anthropic_api_key": "real-secret-key", "lm_studio_model": "old"},
        {"anthropic_api_key": "****-key", "lm_studio_model": "google/gemma-4-e4b"},
    )
    assert merged["anthropic_api_key"] == "real-secret-key"
    assert merged["lm_studio_model"] == "google/gemma-4-e4b"


def test_validate_local_ok():
    _validate_update(_local_body(), {})


def test_validate_local_requires_url():
    body = _local_body(lm_studio_base_url=None)
    with pytest.raises(ValidationError) as exc:
        _validate_update(body, {})
    assert exc.value.field == "lm_studio_base_url"


def test_validate_cloud_claude_requires_key():
    body = AiSettingsUpdate(
        deployment_mode="cloud",
        llm_provider="claude",
        embedding_provider="openai",
    )
    with pytest.raises(ValidationError) as exc:
        _validate_update(body, {})
    assert exc.value.field == "anthropic_api_key"


def test_validate_cloud_openai_requires_key():
    body = AiSettingsUpdate(
        deployment_mode="cloud",
        llm_provider="openai",
        embedding_provider="openai",
    )
    with pytest.raises(ValidationError) as exc:
        _validate_update(body, {})
    assert exc.value.field == "openai_api_key"


def test_validate_cloud_gemini_requires_key():
    body = AiSettingsUpdate(
        deployment_mode="cloud",
        llm_provider="gemini",
        embedding_provider="gemini",
    )
    with pytest.raises(ValidationError) as exc:
        _validate_update(body, {})
    assert exc.value.field == "gemini_api_key"


def test_validate_cloud_accepts_existing_key_when_masked_incoming():
    body = AiSettingsUpdate(
        deployment_mode="cloud",
        llm_provider="openai",
        embedding_provider="openai",
        openai_api_key="****abcd",
    )
    _validate_update(body, {"openai_api_key": "sk-live-abcd"})


def test_validate_on_prem_rejects_claude():
    body = _local_body(llm_provider="claude")
    with pytest.raises(ValidationError) as exc:
        _validate_update(body, {})
    assert exc.value.field == "llm_provider"


def test_merged_settings_overlays_nonempty_payload():
    row = AiRuntimeSettings(
        id=1,
        payload={
            "lm_studio_model": "overlay-model",
            "anthropic_api_key": "sk-ant-live",
            "openai_api_key": "",
        },
    )
    merged = _merged_settings_dict(row)
    assert merged["lm_studio_model"] == "overlay-model"
    assert merged["anthropic_api_key"] == "sk-ant-live"
    # Empty payload values are ignored so env defaults remain.
    assert merged.get("openai_api_key") != "sk-ant-live"


def test_public_payload_includes_reingest_flag():
    public = _public_payload({"deployment_mode": "on_prem"}, reingest_required=True)
    assert public["restart_required"] is False
    assert public["reingest_required"] is True


def test_embedding_changed_vendor_and_model():
    existing = {
        "embedding_provider": "local",
        "lm_studio_embedding_model": "text-embedding-embeddinggemma-300m",
        "gemini_embedding_model": "text-embedding-004",
    }
    same = dict(existing)
    assert _embedding_changed(existing, same) is False
    assert _embedding_changed(existing, {**existing, "embedding_provider": "gemini"}) is True
    assert _embedding_changed(
        existing,
        {**existing, "lm_studio_embedding_model": "other-embed"},
    ) is True
    assert _embedding_changed(
        {**existing, "embedding_provider": "gemini"},
        {**existing, "embedding_provider": "gemini", "gemini_embedding_model": "text-embedding-005"},
    ) is True


def test_overlay_from_merged_keeps_known_fields_only():
    overlay = _overlay_from_merged(
        {
            "llm_provider": "ollama",
            "unknown": "drop-me",
            "lm_studio_model": "google/gemma-4-e4b",
        }
    )
    assert overlay["llm_provider"] == "ollama"
    assert "unknown" not in overlay
    assert set(overlay).issubset(AI_OVERLAY_FIELDS)


def test_validate_invalid_vector_store():
    body = _local_body(vector_store_provider="pinecone")
    with pytest.raises(ValidationError) as exc:
        _validate_update(body, {})
    assert exc.value.field == "vector_store_provider"


def test_validate_cloud_mode_rejects_lm_studio():
    body = AiSettingsUpdate(
        deployment_mode="cloud",
        llm_provider="lm_studio",
        embedding_provider="openai",
        openai_api_key="sk-test",
    )
    with pytest.raises(ValidationError) as exc:
        _validate_update(body, {})
    assert exc.value.field == "llm_provider"


def _admin_user():
    user = MagicMock(spec=User)
    user.id = "11111111-1111-1111-1111-111111111111"
    user.role = "admin"
    user.email = "admin@example.go.th"
    return user


@pytest.fixture
def admin_client():
    app.state.db_session_factory = None
    app.state.db_engine = None
    app.state.redis = None
    app.state.minio = None

    async def override_user():
        return _admin_user()

    app.dependency_overrides[get_current_user] = override_user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _override_db(session):
    async def override():
        yield session

    app.dependency_overrides[get_db] = override


def test_get_ai_settings_http(admin_client):
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)
    _override_db(mock_db)

    response = admin_client.get("/api/v1/admin/ai-settings")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["restart_required"] is False
    assert data["reingest_required"] is False
    assert data["llm_provider"]


def test_put_ai_settings_applies_overlay_without_restart(admin_client):
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = admin_client.put(
        "/api/v1/admin/ai-settings",
        json={
            "deployment_mode": "on_prem",
            "llm_provider": "lm_studio",
            "embedding_provider": "local",
            "lm_studio_base_url": "http://127.0.0.1:1234/v1",
            "lm_studio_model": "overlay-gemma-test",
            "lm_studio_embedding_model": "text-embedding-embeddinggemma-300m",
            "vector_store_provider": "pgvector",
        },
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["restart_required"] is False
    assert data["reingest_required"] is False
    assert get_settings().lm_studio_model == "overlay-gemma-test"


def test_put_ai_settings_sets_reingest_when_embed_model_changes(admin_client):
    row = AiRuntimeSettings(
        id=1,
        payload={
            "deployment_mode": "on_prem",
            "llm_provider": "lm_studio",
            "embedding_provider": "local",
            "lm_studio_base_url": "http://127.0.0.1:1234/v1",
            "lm_studio_model": "google/gemma-4-e4b",
            "lm_studio_embedding_model": "text-embedding-embeddinggemma-300m",
        },
    )
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    mock_db.execute = AsyncMock(return_value=result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = admin_client.put(
        "/api/v1/admin/ai-settings",
        json={
            "deployment_mode": "on_prem",
            "llm_provider": "lm_studio",
            "embedding_provider": "local",
            "lm_studio_base_url": "http://127.0.0.1:1234/v1",
            "lm_studio_model": "google/gemma-4-e4b",
            "lm_studio_embedding_model": "other-embed-768",
        },
    )
    assert response.status_code == 200
    assert response.json()["data"]["reingest_required"] is True
    assert response.json()["data"]["restart_required"] is False


def test_put_ai_settings_cloud_missing_key(admin_client):
    from app.config import apply_runtime_overlay

    apply_runtime_overlay(
        {
            "openai_api_key": "",
            "anthropic_api_key": "",
            "gemini_api_key": "",
        }
    )
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)
    _override_db(mock_db)

    response = admin_client.put(
        "/api/v1/admin/ai-settings",
        json={
            "deployment_mode": "cloud",
            "llm_provider": "openai",
            "embedding_provider": "openai",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["field"] == "openai_api_key"


def test_put_ai_settings_keeps_masked_key(admin_client):
    row = AiRuntimeSettings(
        id=1,
        payload={
            "deployment_mode": "cloud",
            "llm_provider": "openai",
            "embedding_provider": "openai",
            "openai_api_key": "sk-live-real-key",
        },
    )
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = row
    mock_db.execute = AsyncMock(return_value=result)
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = admin_client.put(
        "/api/v1/admin/ai-settings",
        json={
            "deployment_mode": "cloud",
            "llm_provider": "openai",
            "embedding_provider": "openai",
            "openai_api_key": "****-key",
        },
    )
    assert response.status_code == 200
    assert row.payload["openai_api_key"] == "sk-live-real-key"
    assert response.json()["data"]["openai_api_key"].startswith("****")


def test_test_ai_settings_local_http(admin_client):
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)
    _override_db(mock_db)

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False

    with patch(
        "app.api.v1.endpoints.admin_ai_settings.httpx.AsyncClient",
        return_value=mock_client,
    ):
        response = admin_client.post(
            "/api/v1/admin/ai-settings/test",
            json={
                "deployment_mode": "on_prem",
                "llm_provider": "lm_studio",
                "embedding_provider": "local",
                "lm_studio_base_url": "http://127.0.0.1:1234/v1",
            },
        )
    assert response.status_code == 200
    assert "เชื่อมต่อ" in response.json()["data"]["message"]


def test_validate_ollama_and_llama_urls():
    _validate_update(
        _local_body(llm_provider="ollama", ollama_base_url="http://127.0.0.1:11434/v1"),
        {},
    )
    _validate_update(
        _local_body(llm_provider="llama_cpp", llama_cpp_base_url="http://127.0.0.1:8080/v1"),
        {},
    )
    assert _resolved_local_url(_local_body(llm_provider="ollama"), {}) == ""
    assert "11434" in _local_base_url(AiSettingsTest(llm_provider="ollama"))
    assert "8080" in _local_base_url(AiSettingsTest(llm_provider="llama_cpp"))


def test_validate_invalid_mode_and_providers():
    invalid_mode = _local_body(deployment_mode="invalid")
    with pytest.raises(ValidationError) as mode_exc:
        _validate_update(invalid_mode, {})
    assert mode_exc.value.field == "deployment_mode"

    unknown_llm = _local_body(llm_provider="unknown")
    with pytest.raises(ValidationError) as llm_exc:
        _validate_update(unknown_llm, {})
    assert llm_exc.value.field == "llm_provider"

    unknown_embed = _local_body(embedding_provider="unknown")
    with pytest.raises(ValidationError) as embed_exc:
        _validate_update(unknown_embed, {})
    assert embed_exc.value.field == "embedding_provider"


def test_validate_local_requires_chat_and_embed_models():
    missing_chat = _local_body(lm_studio_model=None)
    with pytest.raises(ValidationError) as chat_exc:
        _validate_update(missing_chat, {})
    assert chat_exc.value.field == "lm_studio_model"

    missing_embed = _local_body(lm_studio_embedding_model=None)
    with pytest.raises(ValidationError) as embed_exc:
        _validate_update(missing_embed, {})
    assert embed_exc.value.field == "lm_studio_embedding_model"


def _mock_httpx_ok():
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    return mock_client


def test_test_ai_settings_cloud_providers(admin_client):
    from app.config import apply_runtime_overlay

    apply_runtime_overlay(
        {
            "anthropic_api_key": "sk-ant-test",
            "openai_api_key": "sk-openai-test",
            "gemini_api_key": "gem-test",
        }
    )
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)
    _override_db(mock_db)

    with patch(
        "app.api.v1.endpoints.admin_ai_settings.httpx.AsyncClient",
        return_value=_mock_httpx_ok(),
    ):
        for provider in ("claude", "openai", "gemini"):
            response = admin_client.post(
                "/api/v1/admin/ai-settings/test",
                json={
                    "deployment_mode": "cloud",
                    "llm_provider": provider,
                    "embedding_provider": "openai",
                },
            )
            assert response.status_code == 200, response.text
            assert "คลาวด์" in response.json()["data"]["message"]


def test_test_ai_settings_cloud_missing_key(admin_client):
    from app.config import apply_runtime_overlay

    apply_runtime_overlay({"anthropic_api_key": "", "openai_api_key": "", "gemini_api_key": ""})
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)
    _override_db(mock_db)
    response = admin_client.post(
        "/api/v1/admin/ai-settings/test",
        json={"deployment_mode": "cloud", "llm_provider": "claude", "embedding_provider": "openai"},
    )
    assert response.status_code == 400


def test_validate_hybrid_requires_cloud_key():
    body = AiSettingsUpdate(
        deployment_mode="hybrid",
        llm_provider="claude",
        embedding_provider="local",
        lm_studio_embedding_model="text-embedding-embeddinggemma-300m",
    )
    with pytest.raises(ValidationError) as exc:
        _validate_update(body, {})
    assert exc.value.field == "anthropic_api_key"


def test_validate_hybrid_local_does_not_need_cloud_key():
    _validate_update(
        _local_body(
            deployment_mode="hybrid",
            llm_provider="ollama",
            ollama_base_url="http://127.0.0.1:11434/v1",
        ),
        {},
    )


def test_validate_cloud_rejects_local_embeddings():
    body = AiSettingsUpdate(
        deployment_mode="cloud",
        llm_provider="openai",
        embedding_provider="local",
        openai_api_key="sk-test",
    )
    with pytest.raises(ValidationError) as exc:
        _validate_update(body, {})
    assert exc.value.field == "embedding_provider"


def test_test_ai_settings_ollama_and_llama(admin_client):
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)
    _override_db(mock_db)

    with patch(
        "app.api.v1.endpoints.admin_ai_settings.httpx.AsyncClient",
        return_value=_mock_httpx_ok(),
    ):
        ollama = admin_client.post(
            "/api/v1/admin/ai-settings/test",
            json={
                "deployment_mode": "on_prem",
                "llm_provider": "ollama",
                "embedding_provider": "local",
                "ollama_base_url": "http://127.0.0.1:11434/v1",
            },
        )
        llama = admin_client.post(
            "/api/v1/admin/ai-settings/test",
            json={
                "deployment_mode": "hybrid",
                "llm_provider": "llama_cpp",
                "embedding_provider": "local",
                "llama_cpp_base_url": "http://127.0.0.1:8080/v1",
            },
        )
    assert ollama.status_code == 200
    assert llama.status_code == 200
    assert "11434" in ollama.json()["data"]["url"]
    assert "8080" in llama.json()["data"]["url"]


def test_test_ai_settings_connection_failure(admin_client):
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)
    _override_db(mock_db)

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("refused"))
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    with patch(
        "app.api.v1.endpoints.admin_ai_settings.httpx.AsyncClient",
        return_value=mock_client,
    ):
        response = admin_client.post(
            "/api/v1/admin/ai-settings/test",
            json={
                "deployment_mode": "on_prem",
                "llm_provider": "lm_studio",
                "embedding_provider": "local",
                "lm_studio_base_url": "http://127.0.0.1:1234/v1",
            },
        )
    assert response.status_code == 400
    assert "ทดสอบไม่สำเร็จ" in response.json()["error"]["message"]


def test_test_ai_settings_invalid_cloud_provider(admin_client):
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)
    _override_db(mock_db)
    response = admin_client.post(
        "/api/v1/admin/ai-settings/test",
        json={
            "deployment_mode": "cloud",
            "llm_provider": "unknown-cloud",
            "embedding_provider": "openai",
        },
    )
    assert response.status_code == 400


def test_put_ai_settings_cloud_with_keys(admin_client):
    mock_db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    _override_db(mock_db)

    response = admin_client.put(
        "/api/v1/admin/ai-settings",
        json={
            "deployment_mode": "cloud",
            "llm_provider": "gemini",
            "embedding_provider": "gemini",
            "gemini_api_key": "gem-live-key",
            "gemini_model": "gemini-2.0-flash",
            "gemini_embedding_model": "text-embedding-004",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["llm_provider"] == "gemini"
    assert response.json()["data"]["gemini_api_key"].startswith("****")
    assert get_settings().llm_provider == "gemini"
