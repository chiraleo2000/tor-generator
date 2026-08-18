"""Admin AI provider settings: local (LM Studio / Ollama / llama.cpp) vs cloud."""

from __future__ import annotations

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
    CLOUD_EMBEDDING_PROVIDERS,
    CLOUD_LLM_PROVIDERS,
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    LOCAL_LLM_DEFAULT_URLS,
    LOCAL_LLM_PROVIDERS,
)
from app.providers.factory import (
    VALID_EMBEDDING_PROVIDERS,
    VALID_LLM_PROVIDERS,
    VALID_VECTOR_STORE_PROVIDERS,
)
from app.rbac import require_role
from app.schemas.responses import MetaInfo, SuccessResponse

router = APIRouter()

_KEY_FIELDS = ("anthropic_api_key", "openai_api_key", "gemini_api_key")
_MSG_ANTHROPIC_KEY = "ต้องใส่ ANTHROPIC_API_KEY"
_MSG_OPENAI_KEY = "ต้องใส่ OPENAI_API_KEY"
_MSG_GEMINI_KEY = "ต้องใส่ GEMINI_API_KEY"


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
    lm_studio_base_url: str | None = None
    lm_studio_model: str | None = None
    lm_studio_embedding_model: str | None = None
    lm_studio_timeout: float | None = None
    ollama_base_url: str | None = None
    llama_cpp_base_url: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_chat_model: str | None = None
    gemini_model: str | None = None
    gemini_embedding_model: str | None = None
    vector_store_provider: str | None = None


class AiSettingsTest(BaseModel):
    deployment_mode: str = "on_prem"
    llm_provider: str = "lm_studio"
    embedding_provider: str = "local"
    lm_studio_base_url: str | None = None
    ollama_base_url: str | None = None
    llama_cpp_base_url: str | None = None
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None
    gemini_api_key: str | None = None


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
    return str(body.lm_studio_base_url or existing.get("lm_studio_base_url") or "")


def _validate_update(body: AiSettingsUpdate, existing: dict[str, Any]) -> None:
    if body.deployment_mode not in ("on_prem", "cloud", "hybrid"):
        raise ValidationError(message="โหมดการทำงานไม่ถูกต้อง", field="deployment_mode")
    if body.llm_provider not in VALID_LLM_PROVIDERS:
        raise ValidationError(message="ผู้ให้บริการโมเดลไม่ถูกต้อง", field="llm_provider")
    if body.embedding_provider not in VALID_EMBEDDING_PROVIDERS:
        raise ValidationError(
            message="ผู้ให้บริการ embeddings ไม่ถูกต้อง", field="embedding_provider"
        )
    if (
        body.vector_store_provider
        and body.vector_store_provider not in VALID_VECTOR_STORE_PROVIDERS
    ):
        raise ValidationError(
            message="คลังเวกเตอร์ไม่ถูกต้อง", field="vector_store_provider"
        )
    if body.deployment_mode == "on_prem" and body.llm_provider not in LOCAL_LLM_PROVIDERS:
        raise ValidationError(
            message="โหมดในเครื่องต้องเลือก LM Studio, Ollama หรือ llama.cpp",
            field="llm_provider",
        )
    if body.deployment_mode == "cloud" and body.llm_provider not in CLOUD_LLM_PROVIDERS:
        raise ValidationError(
            message="โหมดคลาวด์ต้องเลือก Claude, OpenAI หรือ Gemini",
            field="llm_provider",
        )
    if body.deployment_mode == "cloud" and body.embedding_provider not in CLOUD_EMBEDDING_PROVIDERS:
        raise ValidationError(
            message="โหมดคลาวด์ต้องเลือก embeddings ของ OpenAI หรือ Gemini",
            field="embedding_provider",
        )

    needs_local = body.deployment_mode == "on_prem" or body.llm_provider in LOCAL_LLM_PROVIDERS
    if needs_local and not _resolved_local_url(body, existing):
        raise ValidationError(
            message="ต้องระบุ URL ของเซิร์ฟเวอร์ในเครื่อง",
            field="lm_studio_base_url",
        )
    if needs_local and not (body.lm_studio_model or existing.get("lm_studio_model")):
        raise ValidationError(message="ต้องระบุชื่อโมเดลแชท", field="lm_studio_model")
    if (
        body.deployment_mode == "on_prem" or body.embedding_provider in ("local", "qwen3")
    ) and not (body.lm_studio_embedding_model or existing.get("lm_studio_embedding_model")):
        raise ValidationError(
            message="ต้องระบุชื่อโมเดล embeddings", field="lm_studio_embedding_model"
        )

    def resolved_key(name: str) -> str:
        incoming = getattr(body, name)
        if incoming and not _is_masked_secret(incoming):
            return incoming
        return str(existing.get(name) or "")

    if body.deployment_mode in ("cloud", "hybrid"):
        _require_cloud_key(
            body.llm_provider,
            "claude",
            resolved_key("anthropic_api_key"),
            _MSG_ANTHROPIC_KEY,
            "anthropic_api_key",
        )
        _require_cloud_key(
            body.llm_provider,
            "openai",
            resolved_key("openai_api_key"),
            _MSG_OPENAI_KEY,
            "openai_api_key",
        )
        _require_cloud_key(
            body.llm_provider,
            "gemini",
            resolved_key("gemini_api_key"),
            _MSG_GEMINI_KEY,
            "gemini_api_key",
        )
        _require_cloud_key(
            body.embedding_provider,
            "openai",
            resolved_key("openai_api_key"),
            _MSG_OPENAI_KEY,
            "openai_api_key",
        )
        _require_cloud_key(
            body.embedding_provider,
            "gemini",
            resolved_key("gemini_api_key"),
            _MSG_GEMINI_KEY,
            "gemini_api_key",
        )


def _embedding_changed(existing: dict[str, Any], merged: dict[str, Any]) -> bool:
    old_vendor = str(existing.get("embedding_provider") or "")
    new_vendor = str(merged.get("embedding_provider") or "")
    if old_vendor != new_vendor:
        return True
    if new_vendor in ("local", "qwen3"):
        return str(existing.get("lm_studio_embedding_model") or "") != str(
            merged.get("lm_studio_embedding_model") or ""
        )
    if new_vendor == "gemini":
        return str(existing.get("gemini_embedding_model") or "") != str(
            merged.get("gemini_embedding_model") or ""
        )
    return False


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
            reingest_required=_embedding_changed(existing, merged),
        ),
    )


def _local_base_url(body: AiSettingsTest) -> str:
    if body.llm_provider == "ollama":
        return body.ollama_base_url or LOCAL_LLM_DEFAULT_URLS["ollama"]
    if body.llm_provider == "llama_cpp":
        return body.llama_cpp_base_url or LOCAL_LLM_DEFAULT_URLS["llama_cpp"]
    return body.lm_studio_base_url or LOCAL_LLM_DEFAULT_URLS["lm_studio"]


@router.post("/test")
async def test_ai_settings(
    request: Request,
    body: AiSettingsTest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_role(["admin"]))],
) -> JSONResponse:
    existing = _merged_settings_dict(await _load_row(db))
    try:
        if body.deployment_mode == "on_prem" or body.llm_provider in LOCAL_LLM_PROVIDERS:
            base = _local_base_url(body).rstrip("/")
            models_url = f"{base}/models"
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(models_url)
                response.raise_for_status()
            return _ok(
                request,
                {"ok": True, "message": "เชื่อมต่อเซิร์ฟเวอร์ในเครื่องได้", "url": models_url},
            )
        if body.llm_provider == "claude":
            key = body.anthropic_api_key or existing.get("anthropic_api_key")
            if not key or str(key).startswith("****"):
                raise ValidationError(message=_MSG_ANTHROPIC_KEY, field="anthropic_api_key")
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={
                        "x-api-key": str(key),
                        "anthropic-version": "2023-06-01",
                    },
                )
                response.raise_for_status()
        elif body.llm_provider == "openai":
            key = body.openai_api_key or existing.get("openai_api_key")
            if not key or str(key).startswith("****"):
                raise ValidationError(message=_MSG_OPENAI_KEY, field="openai_api_key")
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                response.raise_for_status()
        elif body.llm_provider == "gemini":
            key = body.gemini_api_key or existing.get("gemini_api_key")
            if not key or str(key).startswith("****"):
                raise ValidationError(message=_MSG_GEMINI_KEY, field="gemini_api_key")
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
                )
                response.raise_for_status()
        else:
            raise ValidationError(message="ผู้ให้บริการไม่ถูกต้อง", field="llm_provider")
        return _ok(request, {"ok": True, "message": "เชื่อมต่อคลาวด์ได้"})
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError(message=f"ทดสอบไม่สำเร็จ: {exc}") from exc
