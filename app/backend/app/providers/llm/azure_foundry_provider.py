"""Azure AI Foundry / Azure OpenAI chat provider."""

from __future__ import annotations

from openai import AsyncAzureOpenAI
from httpx import Timeout

from app.providers.llm.openai_provider import OpenAILLMProvider


class AzureFoundryLLMProvider(OpenAILLMProvider):
    """OpenAI-compatible Azure Foundry deployments."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str,
        deployment: str,
        api_version: str = "2024-10-21",
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("Azure Foundry API key is required")
        if not endpoint:
            raise ValueError("Azure Foundry endpoint is required")
        if not deployment:
            raise ValueError("Azure Foundry deployment is required")
        self._model_name = deployment
        self._timeout = timeout
        self._client = AsyncAzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version=api_version,
            timeout=Timeout(timeout, connect=10.0),
        )
