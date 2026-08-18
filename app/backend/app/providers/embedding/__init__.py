"""Embedding provider implementations (OpenAI, Gemini, local OpenAI-compat)."""

from app.providers.embedding.gemini_provider import GeminiEmbeddingProvider
from app.providers.embedding.openai_provider import OpenAIEmbeddingProvider
from app.providers.embedding.qwen3_provider import Qwen3LocalEmbeddingProvider

LocalEmbeddingProvider = Qwen3LocalEmbeddingProvider

__all__ = [
    "OpenAIEmbeddingProvider",
    "Qwen3LocalEmbeddingProvider",
    "LocalEmbeddingProvider",
    "GeminiEmbeddingProvider",
]
