"""Shared AI provider constants."""

EMBEDDING_DIMENSIONS = 768

DEFAULT_CHAT_MODEL = "google/gemma-4-e4b"
DEFAULT_EMBEDDING_MODEL = "text-embedding-embeddinggemma-300m"

LOCAL_LLM_DEFAULT_URLS = {
    "lm_studio": "http://host.docker.internal:1234/v1",
    "ollama": "http://host.docker.internal:11434/v1",
    "llama_cpp": "http://host.docker.internal:8080/v1",
}

LOCAL_LLM_PROVIDERS = frozenset({"lm_studio", "ollama", "llama_cpp"})
CLOUD_LLM_PROVIDERS = frozenset({"claude", "openai", "gemini"})
LOCAL_EMBEDDING_PROVIDERS = frozenset({"local", "qwen3"})
CLOUD_EMBEDDING_PROVIDERS = frozenset({"openai", "gemini"})

AI_OVERLAY_FIELDS = (
    "deployment_mode",
    "llm_provider",
    "embedding_provider",
    "lm_studio_base_url",
    "lm_studio_model",
    "lm_studio_embedding_model",
    "lm_studio_timeout",
    "ollama_base_url",
    "llama_cpp_base_url",
    "anthropic_api_key",
    "openai_api_key",
    "gemini_api_key",
    "openai_chat_model",
    "gemini_model",
    "gemini_embedding_model",
    "vector_store_provider",
)
