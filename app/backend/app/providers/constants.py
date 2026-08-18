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
CLOUD_LLM_PROVIDERS = frozenset(
    {"claude", "openai", "gemini", "bedrock", "azure_foundry", "openai_compatible"}
)
LOCAL_EMBEDDING_PROVIDERS = frozenset({"local", "qwen3"})
CLOUD_EMBEDDING_PROVIDERS = frozenset(
    {"openai", "gemini", "azure_foundry", "openai_compatible", "bedrock"}
)

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
    "bedrock_region",
    "bedrock_model_id",
    "bedrock_embedding_model_id",
    "aws_access_key_id",
    "aws_secret_access_key",
    "azure_foundry_endpoint",
    "azure_foundry_api_key",
    "azure_foundry_deployment",
    "azure_foundry_api_version",
    "openai_compatible_base_url",
    "openai_compatible_api_key",
    "openai_compatible_model",
    "openai_compatible_embedding_model",
)
