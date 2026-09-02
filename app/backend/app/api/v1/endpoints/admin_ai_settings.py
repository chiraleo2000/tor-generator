"""Admin AI provider settings: local (LM Studio / Ollama / llama.cpp) vs cloud."""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import apply_runtime_overlay, get_settings
from app.deps import get_db
from app.exceptions import ValidationError
from app.models.ai_runtime_settings import AiRuntimeSettings
from app.models.user import User
from app.providers.constants import (
    AI_OVERLAY_FIELDS,
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_PROVIDERS,
    LOCAL_EMBEDDING_SERVERS,
    LOCAL_LLM_DEFAULT_URLS,
    LOCAL_LLM_PROVIDERS,
    SGLANG_DEFAULT_EMBEDDING_URL,
)
from app.providers.factory import (
    VALID_EMBEDDING_PROVIDERS,
    VALID_LLM_PROVIDERS,
    VALID_VECTOR_STORE_PROVIDERS,
)
from app.rag.custom_rag_client import CustomRagClient
from app.rbac import require_role
from app.schemas.responses import MetaInfo, SuccessResponse

router = APIRouter()

_KEY_FIELDS = (
    "anthropic_api_key",
    "openai_api_key",
    "gemini_api_key",
    "aws_secret_access_key",
    "azure_foundry_api_key",
    "openai_compatible_api_key",
    "custom_rag_api_key",
)
_MSG_ANTHROPIC_KEY = "ต้องใส่ ANTHROPIC_API_KEY"
_MSG_OPENAI_KEY = "ต้องใส่ OPENAI_API_KEY"
_MSG_GEMINI_KEY = "ต้องใส่ GEMINI_API_KEY"
_MSG_AZURE_KEY = "ต้องใส่ Azure Foundry API key"
_MSG_COMPAT_URL = "ต้องใส่ OpenAI-compatible base URL"


def _mask_key(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"


def _is_masked_secret(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("****")


def _merge_saved_payload(
    existing_payload: dict[str, Any], dumped: dict[str, Any]
) -> dict[str, Any]:
    payload = dict(existing_payload)
    for key, value in dumped.items():
        if key in _KEY_FIELDS and _is_masked_secret(value):
            continue
        payload[key] = value
    return payload


def _meta(request: Request) -> MetaInfo:
    return MetaInfo(
        request_id=getattr(request.state, "request_id", str(uuid.uuid4())),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _ok(request: Request, data: Any) -> JSONResponse:
    payload = SuccessResponse(ok=True, data=data, meta=_meta(request))
    return JSONResponse(content=payload.model_dump(mode="json"))


def _merged_settings_dict(row: AiRuntimeSettings | None) -> dict[str, Any]:
    env = get_settings()
    merged: dict[str, Any] = {field: getattr(env, field) for field in AI_OVERLAY_FIELDS}
    if row and isinstance(row.payload, dict):
        for key, value in row.payload.items():
            if key in AI_OVERLAY_FIELDS and value not in (None, ""):
                merged[key] = value
    return merged


def _public_payload(
    merged: dict[str, Any],
    restart_required: bool = False,
    reingest_required: bool = False,
) -> dict[str, Any]:
    public = dict(merged)
    for key in _KEY_FIELDS:
        public[key] = _mask_key(str(merged.get(key) or ""))
        public[f"{key}_set"] = bool(merged.get(key))
    public["restart_required"] = restart_required
    public["reingest_required"] = reingest_required
    public["local_llm_defaults"] = dict(LOCAL_LLM_DEFAULT_URLS)
    public["default_chat_model"] = DEFAULT_CHAT_MODEL
    public["default_embedding_model"] = DEFAULT_EMBEDDING_MODEL
    return public


class AiSettingsUpdate(BaseModel):
    deployment_mode: str = Field(default="on_prem")
    llm_provider: str = Field(default="lm_studio")
    embedding_provider: str = Field(default="local")
    local_embedding_server: str | None = None
    local_embedding_base_url: str | None = None
    lm_studio_base_url: str | None = None
    lm_studio_model: str | None = None
    lm_studio_embedding_model: str | None = None
    lm_studio_timeout: float | None = None
    ollama_base_url: str | None = None
    llama_cpp_base_url: str | None = None
    sglang_base_url: str | None = None
    sglang_embedding_base_url: str | None = None
    sglang_model: str | None = None
    sglang_embedding_model: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_chat_model: str | None = None
    openai_embedding_model: str | None = None
    gemini_model: str | None = None
    gemini_embedding_model: str | None = None
    vector_store_provider: str | None = None
    bedrock_region: str | None = None
    bedrock_model_id: str | None = None
    bedrock_embedding_model_id: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    azure_foundry_endpoint: str | None = None
    azure_foundry_api_key: str | None = None
    azure_foundry_deployment: str | None = None
    azure_foundry_embedding_deployment: str | None = None
    azure_foundry_api_version: str | None = None
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    openai_compatible_model: str | None = None
    openai_compatible_embedding_model: str | None = None
    custom_rag_enabled: bool | None = None
    custom_rag_base_url: str | None = None
    custom_rag_api_key: str | None = None
    custom_rag_top_k: int | None = None
    custom_rag_timeout_seconds: float | None = None
    chat_rag_top_k: int | None = None
    chat_max_context_chunks: int | None = None
    draft_rag_top_k: int | None = None
    rag_sources: str | None = None


class AiSettingsTest(BaseModel):
    deployment_mode: str = "on_prem"
    llm_provider: str = "lm_studio"
    embedding_provider: str = "local"
    local_embedding_server: str | None = None
    local_embedding_base_url: str | None = None
    lm_studio_base_url: str | None = None
    ollama_base_url: str | None = None
    llama_cpp_base_url: str | None = None
    sglang_base_url: str | None = None
    sglang_embedding_base_url: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    bedrock_region: str | None = None
    bedrock_model_id: str | None = None
    azure_foundry_endpoint: str | None = None
    azure_foundry_api_key: str | None = None
    azure_foundry_deployment: str | None = None
    azure_foundry_api_version: str | None = None
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    openai_compatible_model: str | None = None
    custom_rag_enabled: bool | None = None
    custom_rag_base_url: str | None = None
    custom_rag_api_key: str | None = None
    rag_sources: str | None = None


def _require_cloud_key(
    selected: str, expected: str, resolved: str, message: str, field: str
) -> None:
    if selected == expected and not resolved:
        raise ValidationError(message=message, field=field)


def _resolved_local_url(body: AiSettingsUpdate, existing: dict[str, Any]) -> str:
    if body.llm_provider == "ollama":
        return str(body.ollama_base_url or existing.get("ollama_base_url") or "")
    if body.llm_provider == "llama_cpp":
        return str(body.llama_cpp_base_url or existing.get("llama_cpp_base_url") or "")
    if body.llm_provider == "sglang":
        return str(body.sglang_base_url or existing.get("sglang_base_url") or "")
    return str(body.lm_studio_base_url or existing.get("lm_studio_base_url") or "")


def _resolved_embed_url(body: AiSettingsUpdate, existing: dict[str, Any]) -> str:
    override = str(
        body.local_embedding_base_url or existing.get("local_embedding_base_url") or ""
    ).strip()
    if override:
        return override
    server = str(
        body.local_embedding_server or existing.get("local_embedding_server") or "lm_studio"
    )
    if server == "ollama":
        return str(body.ollama_base_url or existing.get("ollama_base_url") or "")
    if server == "llama_cpp":
        return str(body.llama_cpp_base_url or existing.get("llama_cpp_base_url") or "")
    if server == "sglang":
        return str(
            body.sglang_embedding_base_url
            or existing.get("sglang_embedding_base_url")
            or ""
        )
    return str(body.lm_studio_base_url or existing.get("lm_studio_base_url") or "")


def _resolved_chat_model(body: AiSettingsUpdate, existing: dict[str, Any]) -> str:
    if body.llm_provider == "sglang":
        return str(body.sglang_model or existing.get("sglang_model") or "")
    return str(body.lm_studio_model or existing.get("lm_studio_model") or "")


def _resolved_embed_model(body: AiSettingsUpdate, existing: dict[str, Any]) -> str:
    server = str(
        body.local_embedding_server or existing.get("local_embedding_server") or "lm_studio"
    )
    if server == "sglang":
        return str(
            body.sglang_embedding_model or existing.get("sglang_embedding_model") or ""
        )
    return str(
        body.lm_studio_embedding_model or existing.get("lm_studio_embedding_model") or ""
    )


def _require_local_chat(body: AiSettingsUpdate, existing: dict[str, Any]) -> None:
    if body.llm_provider not in LOCAL_LLM_PROVIDERS:
        return
    if not _resolved_local_url(body, existing):
        raise ValidationError(
            message="ต้องระบุ URL ของเซิร์ฟเวอร์แชทในเครื่อง",
            field="lm_studio_base_url",
        )
    if not _resolved_chat_model(body, existing):
        raise ValidationError(message="ต้องระบุชื่อโมเดลแชท", field="lm_studio_model")


def _require_local_embed(body: AiSettingsUpdate, existing: dict[str, Any]) -> None:
    if body.embedding_provider not in LOCAL_EMBEDDING_PROVIDERS:
        return
    if not _resolved_embed_url(body, existing):
        raise ValidationError(
            message="ต้องระบุ URL ของเซิร์ฟเวอร์ embeddings ในเครื่อง",
            field="local_embedding_base_url",
        )
    if not _resolved_embed_model(body, existing):
        raise ValidationError(
            message="ต้องระบุชื่อโมเดล embeddings", field="lm_studio_embedding_model"
        )


def _validate_custom_rag(body: AiSettingsUpdate, existing: dict[str, Any]) -> None:
    if not (body.custom_rag_enabled or existing.get("custom_rag_enabled")):
        return
    enabled = (
        body.custom_rag_enabled
        if body.custom_rag_enabled is not None
        else bool(existing.get("custom_rag_enabled"))
    )
    if not enabled:
        return
    base = str(body.custom_rag_base_url or existing.get("custom_rag_base_url") or "").strip()
    if not base:
        raise ValidationError(
            message="ต้องระบุ Custom RAG base URL",
            field="custom_rag_base_url",
        )
    sources = str(body.rag_sources or existing.get("rag_sources") or "both")
    if sources not in ("local", "custom", "both"):
        raise ValidationError(
            message="rag_sources ต้องเป็น local, custom หรือ both",
            field="rag_sources",
        )


def _validate_local_fields(body: AiSettingsUpdate, existing: dict[str, Any]) -> None:
    _require_local_chat(body, existing)
    _require_local_embed(body, existing)
    _validate_custom_rag(body, existing)


def _resolved_secret(body: AiSettingsUpdate, existing: dict[str, Any], name: str) -> str:
    incoming = getattr(body, name)
    if incoming and not _is_masked_secret(incoming):
        return incoming
    return str(existing.get(name) or "")


def _require_provider_url(
    selected: str, expected: str, resolved: str, message: str, field: str
) -> None:
    if selected != expected or resolved:
        return
    raise ValidationError(message=message, field=field)


def _validate_selected_cloud_keys(body: AiSettingsUpdate, existing: dict[str, Any]) -> None:
    _require_cloud_key(
        body.llm_provider,
        "claude",
        _resolved_secret(body, existing, "anthropic_api_key"),
        _MSG_ANTHROPIC_KEY,
        "anthropic_api_key",
    )
    _require_cloud_key(
        body.llm_provider,
        "openai",
        _resolved_secret(body, existing, "openai_api_key"),
        _MSG_OPENAI_KEY,
        "openai_api_key",
    )
    _require_cloud_key(
        body.llm_provider,
        "gemini",
        _resolved_secret(body, existing, "gemini_api_key"),
        _MSG_GEMINI_KEY,
        "gemini_api_key",
    )
    _require_cloud_key(
        body.embedding_provider,
        "openai",
        _resolved_secret(body, existing, "openai_api_key"),
        _MSG_OPENAI_KEY,
        "openai_api_key",
    )
    _require_cloud_key(
        body.embedding_provider,
        "gemini",
        _resolved_secret(body, existing, "gemini_api_key"),
        _MSG_GEMINI_KEY,
        "gemini_api_key",
    )
    _require_cloud_key(
        body.llm_provider,
        "azure_foundry",
        _resolved_secret(body, existing, "azure_foundry_api_key"),
        _MSG_AZURE_KEY,
        "azure_foundry_api_key",
    )
    _require_cloud_key(
        body.embedding_provider,
        "azure_foundry",
        _resolved_secret(body, existing, "azure_foundry_api_key"),
        _MSG_AZURE_KEY,
        "azure_foundry_api_key",
    )
    compat = str(
        body.openai_compatible_base_url or existing.get("openai_compatible_base_url") or ""
    )
    azure_ep = str(body.azure_foundry_endpoint or existing.get("azure_foundry_endpoint") or "")
    _require_provider_url(
        body.llm_provider,
        "openai_compatible",
        compat,
        _MSG_COMPAT_URL,
        "openai_compatible_base_url",
    )
    _require_provider_url(
        body.embedding_provider,
        "openai_compatible",
        compat,
        _MSG_COMPAT_URL,
        "openai_compatible_base_url",
    )
    _require_provider_url(
        body.llm_provider,
        "azure_foundry",
        azure_ep,
        "ต้องใส่ Azure Foundry endpoint",
        "azure_foundry_endpoint",
    )
    _require_provider_url(
        body.embedding_provider,
        "azure_foundry",
        azure_ep,
        "ต้องใส่ Azure Foundry endpoint",
        "azure_foundry_endpoint",
    )


def _validate_update(body: AiSettingsUpdate, existing: dict[str, Any]) -> None:
    if body.deployment_mode not in ("on_prem", "cloud", "hybrid"):
        raise ValidationError(message="โหมดการทำงานไม่ถูกต้อง", field="deployment_mode")
    if body.llm_provider not in VALID_LLM_PROVIDERS:
        raise ValidationError(message="ผู้ให้บริการโมเดลไม่ถูกต้อง", field="llm_provider")
    if body.embedding_provider not in VALID_EMBEDDING_PROVIDERS:
        raise ValidationError(
            message="ผู้ให้บริการ embeddings ไม่ถูกต้อง", field="embedding_provider"
        )
    rag_sources = str(body.rag_sources or existing.get("rag_sources") or "both")
    if body.embedding_provider == "none" and rag_sources != "custom":
        raise ValidationError(
            message="ปิด embeddings ได้เฉพาะเมื่อใช้ PageIndex RAG เท่านั้น",
            field="embedding_provider",
        )
    if (
        body.vector_store_provider
        and body.vector_store_provider not in VALID_VECTOR_STORE_PROVIDERS
    ):
        raise ValidationError(
            message="คลังเวกเตอร์ไม่ถูกต้อง", field="vector_store_provider"
        )
    if (
        body.local_embedding_server
        and body.local_embedding_server not in LOCAL_EMBEDDING_SERVERS
    ):
        raise ValidationError(
            message="เซิร์ฟเวอร์ embeddings ในเครื่องไม่ถูกต้อง",
            field="local_embedding_server",
        )
    _validate_selected_cloud_keys(body, existing)
    _validate_local_fields(body, existing)


def _embedding_changed(existing: dict[str, Any], merged: dict[str, Any]) -> bool:
    old_vendor = str(existing.get("embedding_provider") or "")
    new_vendor = str(merged.get("embedding_provider") or "")
    if old_vendor != new_vendor:
        return True
    keys_by_vendor = {
        "local": (
            "lm_studio_embedding_model",
            "local_embedding_server",
            "local_embedding_base_url",
        ),
        "qwen3": (
            "lm_studio_embedding_model",
            "local_embedding_server",
            "local_embedding_base_url",
        ),
        "gemini": ("gemini_embedding_model",),
        "openai": ("openai_embedding_model",),
        "bedrock": ("bedrock_embedding_model_id",),
        "openai_compatible": ("openai_compatible_embedding_model",),
        "azure_foundry": (
            "azure_foundry_embedding_deployment",
            "azure_foundry_deployment",
        ),
    }
    return any(
        str(existing.get(key) or "") != str(merged.get(key) or "")
        for key in keys_by_vendor.get(new_vendor, ())
    )


def _overlay_from_merged(merged: dict[str, Any]) -> dict[str, Any]:
    return {key: merged[key] for key in AI_OVERLAY_FIELDS if key in merged}


async def _load_row(db: AsyncSession) -> AiRuntimeSettings | None:
    result = await db.execute(select(AiRuntimeSettings).where(AiRuntimeSettings.id == 1))
    return result.scalar_one_or_none()


@router.get("")
async def get_ai_settings(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
) -> JSONResponse:
    row = await _load_row(db)
    return _ok(request, _public_payload(_merged_settings_dict(row)))


@router.put("")
async def put_ai_settings(
    request: Request,
    body: AiSettingsUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
) -> JSONResponse:
    row = await _load_row(db)
    existing = _merged_settings_dict(row)
    _validate_update(body, existing)
    payload = _merge_saved_payload(
        dict(row.payload) if row and isinstance(row.payload, dict) else {},
        body.model_dump(exclude_none=True),
    )
    if row is None:
        row = AiRuntimeSettings(id=1, payload=payload)
        db.add(row)
    else:
        row.payload = payload
    await db.flush()
    merged = _merged_settings_dict(row)
    apply_runtime_overlay(_overlay_from_merged(merged))
    return _ok(
        request,
        _public_payload(
            merged,
            restart_required=False,
            reingest_required=(
                str(merged.get("rag_sources") or "both") != "custom"
                and _embedding_changed(existing, merged)
            ),
        ),
    )


def _local_base_url(body: AiSettingsTest) -> str:
    if body.llm_provider == "ollama":
        return body.ollama_base_url or LOCAL_LLM_DEFAULT_URLS["ollama"]
    if body.llm_provider == "llama_cpp":
        return body.llama_cpp_base_url or LOCAL_LLM_DEFAULT_URLS["llama_cpp"]
    if body.llm_provider == "sglang":
        return body.sglang_base_url or LOCAL_LLM_DEFAULT_URLS["sglang"]
    return body.lm_studio_base_url or LOCAL_LLM_DEFAULT_URLS["lm_studio"]


def _embed_local_base_url(body: AiSettingsTest) -> str:
    if body.local_embedding_base_url:
        return body.local_embedding_base_url
    server = body.local_embedding_server or "lm_studio"
    if server == "ollama":
        return body.ollama_base_url or LOCAL_LLM_DEFAULT_URLS["ollama"]
    if server == "llama_cpp":
        return body.llama_cpp_base_url or LOCAL_LLM_DEFAULT_URLS["llama_cpp"]
    if server == "sglang":
        return body.sglang_embedding_base_url or SGLANG_DEFAULT_EMBEDDING_URL
    return body.lm_studio_base_url or LOCAL_LLM_DEFAULT_URLS["lm_studio"]


def _usable_secret(value: Any) -> str:
    text = str(value or "")
    if not text or text.startswith("****"):
        return ""
    return text


async def _http_get_ok(url: str, headers: dict[str, str] | None = None) -> None:
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.get(url, headers=headers or {})
        response.raise_for_status()


async def _probe_local_models(base_url: str) -> str:
    url = f"{base_url.rstrip('/')}/models"
    await _http_get_ok(url)
    return url


async def _probe_claude(body: AiSettingsTest, existing: dict[str, Any]) -> None:
    key = _usable_secret(body.anthropic_api_key or existing.get("anthropic_api_key"))
    if not key:
        raise ValidationError(message=_MSG_ANTHROPIC_KEY, field="anthropic_api_key")
    await _http_get_ok(
        "https://api.anthropic.com/v1/models",
        {"x-api-key": key, "anthropic-version": "2023-06-01"},
    )


async def _probe_openai(body: AiSettingsTest, existing: dict[str, Any]) -> None:
    key = _usable_secret(body.openai_api_key or existing.get("openai_api_key"))
    if not key:
        raise ValidationError(message=_MSG_OPENAI_KEY, field="openai_api_key")
    await _http_get_ok(
        "https://api.openai.com/v1/models",
        {"Authorization": f"Bearer {key}"},
    )


async def _probe_gemini(body: AiSettingsTest, existing: dict[str, Any]) -> None:
    key = _usable_secret(body.gemini_api_key or existing.get("gemini_api_key"))
    if not key:
        raise ValidationError(message=_MSG_GEMINI_KEY, field="gemini_api_key")
    await _http_get_ok(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
    )


async def _probe_openai_compatible(body: AiSettingsTest, existing: dict[str, Any]) -> None:
    base = (
        body.openai_compatible_base_url
        or existing.get("openai_compatible_base_url")
        or ""
    ).rstrip("/")
    if not base:
        raise ValidationError(message=_MSG_COMPAT_URL, field="openai_compatible_base_url")
    key = _usable_secret(
        body.openai_compatible_api_key or existing.get("openai_compatible_api_key")
    )
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    await _http_get_ok(f"{base}/models", headers)


async def _probe_azure_foundry(body: AiSettingsTest, existing: dict[str, Any]) -> None:
    endpoint = body.azure_foundry_endpoint or existing.get("azure_foundry_endpoint")
    key = _usable_secret(
        body.azure_foundry_api_key or existing.get("azure_foundry_api_key")
    )
    version = (
        body.azure_foundry_api_version
        or existing.get("azure_foundry_api_version")
        or "v1"
    )
    if not endpoint or not key:
        raise ValidationError(message=_MSG_AZURE_KEY, field="azure_foundry_api_key")
    base = str(endpoint).rstrip("/")
    url = (
        f"{base}/openai/v1/models"
        if str(version).lower() == "v1"
        else f"{base}/openai/models?api-version={version}"
    )
    await _http_get_ok(url, {"api-key": key})


async def _probe_cloud_chat(body: AiSettingsTest, existing: dict[str, Any]) -> None:
    probes = {
        "claude": _probe_claude,
        "openai": _probe_openai,
        "gemini": _probe_gemini,
        "openai_compatible": _probe_openai_compatible,
        "azure_foundry": _probe_azure_foundry,
        "bedrock": _probe_bedrock,
    }
    probe = probes.get(body.llm_provider)
    if probe is None:
        raise ValidationError(message="ผู้ให้บริการไม่ถูกต้อง", field="llm_provider")
    await probe(body, existing)


def _sts_caller_identity(region: str, access: str, secret: str) -> None:
    import boto3

    kwargs: dict[str, Any] = {"region_name": region}
    if access and secret:
        kwargs["aws_access_key_id"] = access
        kwargs["aws_secret_access_key"] = secret
    boto3.client("sts", **kwargs).get_caller_identity()


def _bedrock_runtime_probe(region: str, model_id: str) -> None:
    import boto3

    boto3.client("bedrock-runtime", region_name=region).converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": "ping"}]}],
        inferenceConfig={"maxTokens": 1},
    )


async def _probe_bedrock(body: AiSettingsTest, existing: dict[str, Any]) -> None:
    region = str(body.bedrock_region or existing.get("bedrock_region") or "ap-southeast-1")
    bearer_token = os.getenv("AWS_BEARER_TOKEN_BEDROCK", "").strip()
    if bearer_token:
        model_id = str(
            body.bedrock_model_id
            or existing.get("bedrock_model_id")
            or "global.anthropic.claude-sonnet-4-6"
        )
        try:
            await asyncio.to_thread(_bedrock_runtime_probe, region, model_id)
        except Exception as exc:
            raise ValidationError(message=f"ทดสอบ Bedrock API key ไม่สำเร็จ: {exc}") from exc
        return
    access = str(body.aws_access_key_id or existing.get("aws_access_key_id") or "")
    secret = _usable_secret(
        body.aws_secret_access_key or existing.get("aws_secret_access_key")
    )
    try:
        await asyncio.to_thread(_sts_caller_identity, region, access, secret)
    except Exception as exc:
        raise ValidationError(message=f"ทดสอบ Bedrock/STS ไม่สำเร็จ: {exc}") from exc


async def _probe_cloud_embeddings(body: AiSettingsTest, existing: dict[str, Any]) -> None:
    provider = body.embedding_provider
    if provider == "openai":
        key = _usable_secret(body.openai_api_key or existing.get("openai_api_key"))
        if not key:
            raise ValidationError(message=_MSG_OPENAI_KEY, field="openai_api_key")
        await _http_get_ok(
            "https://api.openai.com/v1/models",
            {"Authorization": f"Bearer {key}"},
        )
        return
    if provider == "gemini":
        key = _usable_secret(body.gemini_api_key or existing.get("gemini_api_key"))
        if not key:
            raise ValidationError(message=_MSG_GEMINI_KEY, field="gemini_api_key")
        await _http_get_ok(
            f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        )
        return
    if provider in ("azure_foundry", "openai_compatible", "bedrock"):
        return


async def _probe_external_rag(body: AiSettingsTest, existing: dict[str, Any]) -> str:
    base_url = str(body.custom_rag_base_url or existing.get("custom_rag_base_url") or "")
    if not base_url.strip():
        raise ValidationError(
            message="ต้องระบุ URL ของ PageIndex RAG",
            field="custom_rag_base_url",
        )
    incoming_key = _usable_secret(body.custom_rag_api_key)
    api_key = incoming_key or str(existing.get("custom_rag_api_key") or "")
    client = CustomRagClient(base_url=base_url, api_key=api_key, top_k=1, timeout=8.0)
    chunks = await client.retrieve("ทดสอบการเชื่อมต่อระบบจัดทำ TOR", top_k=1)
    if chunks and chunks[0].metadata.get("rag_source") == "pageindex_rag":
        return "PageIndex RAG ได้"
    return "Custom RAG ได้"


@router.post("/test")
async def test_ai_settings(
    request: Request,
    body: AiSettingsTest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
) -> JSONResponse:
    existing = _merged_settings_dict(await _load_row(db))
    try:
        parts: list[str] = []
        chat_url = ""
        embed_url = ""
        rag_sources = str(body.rag_sources or existing.get("rag_sources") or "both")
        custom_enabled = (
            body.custom_rag_enabled
            if body.custom_rag_enabled is not None
            else bool(existing.get("custom_rag_enabled"))
        )
        if body.llm_provider in LOCAL_LLM_PROVIDERS:
            chat_url = await _probe_local_models(_local_base_url(body))
            parts.append("แชทในเครื่องได้")
        else:
            await _probe_cloud_chat(body, existing)
            parts.append("แชทคลาวด์ได้")
        # PageIndex-only retrieval does not require the TOR app's embedding server.
        if rag_sources != "custom":
            if body.embedding_provider in LOCAL_EMBEDDING_PROVIDERS:
                embed_base = _embed_local_base_url(body)
                embed_url = f"{embed_base.rstrip('/')}/models"
                if embed_url != chat_url:
                    await _probe_local_models(embed_base)
                parts.append("embeddings ในเครื่องได้")
            else:
                await _probe_cloud_embeddings(body, existing)
                parts.append("embeddings คลาวด์ได้")
        if custom_enabled and rag_sources in ("custom", "both"):
            parts.append(await _probe_external_rag(body, existing))
        return _ok(
            request,
            {
                "ok": True,
                "message": "เชื่อมต่อ: " + " · ".join(parts),
                "url": chat_url or embed_url,
                "embedding_url": embed_url,
            },
        )
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(message=f"ทดสอบไม่สำเร็จ: {exc}") from exc
