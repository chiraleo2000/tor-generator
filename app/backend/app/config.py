"""Application configuration using Pydantic Settings.

Loads all configuration from environment variables with sensible defaults
for local development. Supports three deployment modes: on_prem, cloud, hybrid.
Runtime admin settings overlay env defaults at startup and immediately after PUT /admin/ai-settings.
"""

from functools import cached_property
from typing import Any, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.providers.constants import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    LOCAL_LLM_DEFAULT_URLS,
    LOCAL_LLM_PROVIDERS,
    SGLANG_DEFAULT_EMBEDDING_URL,
)

_runtime_overlay: dict[str, Any] = {}


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

    # -------------------------------------------------------------------------
    # MinIO (Object Storage)
    # -------------------------------------------------------------------------
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme_minio_secret"
    minio_bucket: str = "tor-documents"

    # -------------------------------------------------------------------------
    # API Keys (Cloud Mode)
    # -------------------------------------------------------------------------
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    azure_foundry_api_key: str = ""
    openai_compatible_api_key: str = ""

    # -------------------------------------------------------------------------
    # Local OpenAI-compatible servers (On-Prem)
    # -------------------------------------------------------------------------
    lm_studio_base_url: str = LOCAL_LLM_DEFAULT_URLS["lm_studio"]
    lm_studio_model: str = DEFAULT_CHAT_MODEL
    lm_studio_embedding_model: str = DEFAULT_EMBEDDING_MODEL
    lm_studio_timeout: float = 300.0
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
    custom_rag_api_key: str = ""
    custom_rag_top_k: int = 5
    custom_rag_timeout_seconds: float = 30.0
    rag_sources: Literal["local", "custom", "both"] = "both"

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
        """Redis connection string."""
        return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"

    agent_cache_extraction_ttl_hours: int = 24
    agent_cache_mapping_ttl_hours: int = 24
    agent_cache_draft_ttl_hours: int = 48
    agent_local_storage_dir: str = ""

    def drafting_agent_timeout_seconds(self) -> int:
        """Per-section LLM timeout. Local Gemma needs more headroom than cloud."""
        if self.llm_provider in LOCAL_LLM_PROVIDERS:
            return max(1, min(420, int(self.lm_studio_timeout)))
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


def get_runtime_overlay() -> dict[str, Any]:
    """Return the current overlay dict."""
    return dict(_runtime_overlay)


def get_settings() -> Settings:
    """Settings from environment, with optional DB overlay applied in-process."""
    settings = Settings()
    if _runtime_overlay:
        return settings.model_copy(update=_runtime_overlay)
    return settings
