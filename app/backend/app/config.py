"""Application configuration using Pydantic Settings.

Loads all configuration from environment variables with sensible defaults
for local development. Supports three deployment modes: on_prem, cloud, hybrid.
Runtime admin settings overlay env defaults at startup and immediately after PUT /admin/ai-settings.
Local Compose sets PIN_ON_PREM_LLM=true so a leftover Admin Bedrock overlay cannot
call AWS Converse.
"""

from functools import cached_property
import logging
import os
from typing import Any, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.providers.constants import (
    CLOUD_EMBEDDING_PROVIDERS,
    CLOUD_LLM_PROVIDERS,
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_PROVIDERS,
    LOCAL_LLM_DEFAULT_URLS,
    LOCAL_LLM_PROVIDERS,
    SGLANG_DEFAULT_EMBEDDING_URL,
)

_runtime_overlay: dict[str, Any] = {}
_TRUE_FLAGS = frozenset({"1", "true", "yes", "on"})
logger = logging.getLogger("tor_app.config")

# Per-section local LLM headroom for 32k-token TOR drafts / KB answers
LOCAL_LLM_TIMEOUT_CAP_SECONDS = 1800


def env_flag(name: str, *, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_FLAGS


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Deployment Mode
    # -------------------------------------------------------------------------
    deployment_mode: Literal["on_prem", "cloud", "hybrid"] = "on_prem"
    # Compose local: ignore Admin overlay that selected Bedrock/cloud chat.
    pin_on_prem_llm: bool = False

    # -------------------------------------------------------------------------
    # PostgreSQL
    # -------------------------------------------------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "tor_app"
    postgres_user: str = "tor_user"
    postgres_password: str = "changeme_postgres_password"

    # -------------------------------------------------------------------------
    # Redis
    # -------------------------------------------------------------------------
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = "changeme_redis_password"
    redis_tls: bool = False

    # -------------------------------------------------------------------------
    # MinIO (Object Storage)
    # -------------------------------------------------------------------------
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme_minio_secret"
    minio_bucket: str = "tor-documents"
    minio_secure: bool = False
    minio_region: str = ""
    minio_use_iam: bool = False

    # -------------------------------------------------------------------------
    # API Keys (Cloud Mode)
    # -------------------------------------------------------------------------
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_bearer_token_bedrock: str = ""
    azure_foundry_api_key: str = ""
    openai_compatible_api_key: str = ""

    # -------------------------------------------------------------------------
    # Local OpenAI-compatible servers (On-Prem)
    # -------------------------------------------------------------------------
    lm_studio_base_url: str = LOCAL_LLM_DEFAULT_URLS["lm_studio"]
    lm_studio_model: str = DEFAULT_CHAT_MODEL
    lm_studio_embedding_model: str = DEFAULT_EMBEDDING_MODEL
    lm_studio_timeout: float = 1800.0
    ollama_base_url: str = LOCAL_LLM_DEFAULT_URLS["ollama"]
    llama_cpp_base_url: str = LOCAL_LLM_DEFAULT_URLS["llama_cpp"]
    sglang_base_url: str = LOCAL_LLM_DEFAULT_URLS["sglang"]
    sglang_embedding_base_url: str = SGLANG_DEFAULT_EMBEDDING_URL
    sglang_model: str = DEFAULT_CHAT_MODEL
    sglang_embedding_model: str = "google/embeddinggemma-300m"
    local_embedding_server: str = "lm_studio"
    local_embedding_base_url: str = ""
    # Custom RAG HTTP (optional extra retrieval source)
    custom_rag_enabled: bool = False
    custom_rag_base_url: str = ""
    custom_rag_retrieve_path: str = ""
    custom_rag_api_key: str = ""
    custom_rag_top_k: int = 24
    custom_rag_timeout_seconds: float = 30.0
    chat_rag_top_k: int = 96
    chat_max_context_chunks: int = 96
    draft_rag_top_k: int = 8
    rag_sources: Literal["local", "custom", "both"] = "both"
    mcp_rag_enabled: bool = False
    mcp_rag_config_path: str = ""
    mcp_rag_servers_json: str = ""
    mcp_rag_timeout_seconds: float = 20.0
    mcp_rag_auth_header: str = "Authorization"
    mcp_rag_auth_value: str = ""

    # -------------------------------------------------------------------------
    # Cloud model ids
    # -------------------------------------------------------------------------
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_model: str = "gemini-2.0-flash"
    gemini_embedding_model: str = "text-embedding-004"
    bedrock_region: str = "ap-southeast-1"
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    cloud_llm_timeout: float = 300.0
    azure_foundry_endpoint: str = ""
    azure_foundry_deployment: str = ""
    azure_foundry_embedding_deployment: str = ""
    azure_foundry_api_version: str = "2024-10-21"
    openai_compatible_base_url: str = ""
    openai_compatible_model: str = ""
    openai_compatible_embedding_model: str = "text-embedding-3-small"

    # -------------------------------------------------------------------------
    # MongoDB (original documents) + Neo4j (GraphRAG)
    # -------------------------------------------------------------------------
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "tor_docs"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme_neo4j"

    # -------------------------------------------------------------------------
    # Provider Selection (Hybrid Mode)
    # -------------------------------------------------------------------------
    llm_provider: str = "lm_studio"
    embedding_provider: str = "local"
    vector_store_provider: Literal["pgvector", "qdrant"] = "pgvector"

    # -------------------------------------------------------------------------
    # JWT Authentication
    # -------------------------------------------------------------------------
    jwt_secret: str = "changeme_jwt_secret_at_least_32_characters_long"
    jwt_expiry_hours: int = 24
    cookie_secure: bool = False
    auth_cookie_name: str = "tor_access_token"
    cors_origins: str = "http://localhost:3000"

    # -------------------------------------------------------------------------
    # Rate Limiting
    # -------------------------------------------------------------------------
    rate_limit_requests_per_minute: int = 100
    rate_limit_uploads_per_minute: int = 10
    rate_limit_ai_per_minute: int = 30
    llm_max_concurrent: int = 8
    embedding_max_concurrent: int = 16
    llm_queue_wait_timeout_seconds: float = 120.0

    # -------------------------------------------------------------------------
    # Qdrant (Optional)
    # -------------------------------------------------------------------------
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333

    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------
    @cached_property
    def database_url(self) -> str:
        """Async PostgreSQL connection string for SQLAlchemy."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @cached_property
    def database_url_sync(self) -> str:
        """Sync PostgreSQL connection string for Alembic migrations."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @cached_property
    def redis_url(self) -> str:
        """Redis connection string. Use REDIS_TLS=true for ElastiCache in-transit encryption."""
        scheme = "rediss" if self.redis_tls else "redis"
        return f"{scheme}://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"

    agent_cache_extraction_ttl_hours: int = 24
    agent_cache_mapping_ttl_hours: int = 24
    agent_cache_draft_ttl_hours: int = 48
    agent_local_storage_dir: str = ""

    def drafting_agent_timeout_seconds(self) -> int:
        """Per-section LLM timeout. Local Gemma needs more headroom than cloud."""
        if self.llm_provider in LOCAL_LLM_PROVIDERS:
            return max(1, min(LOCAL_LLM_TIMEOUT_CAP_SECONDS, int(self.lm_studio_timeout)))
        if self.llm_provider == "bedrock":
            return max(1, int(self.cloud_llm_timeout or 300))
        return 60

    def cache_ttl_seconds(self, hours: int) -> int:
        """Clamp cache TTL hours to 1–168 and convert to seconds."""
        return max(1, min(168, int(hours))) * 3600


def apply_runtime_overlay(data: dict[str, Any]) -> None:
    """Replace the in-process overlay (loaded at startup from the database)."""
    global _runtime_overlay
    _runtime_overlay = {key: value for key, value in data.items() if value is not None}


def clear_runtime_overlay() -> None:
    """Clear overlay (tests)."""
    global _runtime_overlay
    _runtime_overlay = {}


def apply_on_prem_llm_pin(settings: Settings) -> Settings:
    """Keep Compose on-prem chat on LM Studio when Admin overlay still says Bedrock."""
    if not env_flag("PIN_ON_PREM_LLM", default=False):
        return settings
    env_mode = (os.environ.get("DEPLOYMENT_MODE") or "on_prem").strip().lower()
    if env_mode != "on_prem":
        return settings
    env_llm = (os.environ.get("LLM_PROVIDER") or "lm_studio").strip() or "lm_studio"
    if env_llm not in LOCAL_LLM_PROVIDERS:
        env_llm = "lm_studio"
    env_embed = (os.environ.get("EMBEDDING_PROVIDER") or "local").strip() or "local"
    if env_embed not in LOCAL_EMBEDDING_PROVIDERS and env_embed != "none":
        env_embed = "local"
    updates: dict[str, Any] = {}
    if settings.llm_provider in CLOUD_LLM_PROVIDERS:
        updates["llm_provider"] = env_llm
    if settings.deployment_mode != "on_prem":
        updates["deployment_mode"] = "on_prem"
    if settings.embedding_provider in CLOUD_EMBEDDING_PROVIDERS:
        updates["embedding_provider"] = env_embed
    if settings.mcp_rag_enabled and not env_flag("MCP_RAG_ENABLED", default=False):
        updates["mcp_rag_enabled"] = False
    if not updates:
        return settings
    logger.warning("PIN_ON_PREM_LLM remapped %s", sorted(updates))
    return settings.model_copy(update=updates)


def get_runtime_overlay() -> dict[str, Any]:
    """Return the current overlay dict."""
    return dict(_runtime_overlay)


def get_settings() -> Settings:
    """Settings from environment, with optional DB overlay applied in-process."""
    settings = Settings()
    if _runtime_overlay:
        settings = settings.model_copy(update=_runtime_overlay)
    return apply_on_prem_llm_pin(settings)
