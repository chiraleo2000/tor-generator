"""Azure AI Foundry / Azure OpenAI chat provider."""

from __future__ import annotations

from httpx import Timeout
from openai import AsyncAzureOpenAI, AsyncOpenAI

from app.providers.llm.openai_provider import OpenAILLMProvider


class AzureFoundryLLMProvider(OpenAILLMProvider):
    """OpenAI-compatible Azure Foundry deployments."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str,
        deployment: str,
        api_version: str = "v1",
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
        client_timeout = Timeout(timeout, connect=10.0)
        if api_version.lower() == "v1":
            # GPT-5.6 is exposed through Azure OpenAI's current v1 surface.
            # The model argument remains the Azure deployment name.
            base_url = endpoint.rstrip("/")
            if not base_url.endswith("/openai/v1"):
                base_url = f"{base_url}/openai/v1"
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=f"{base_url}/",
                timeout=client_timeout,
            )
        else:
            # Preserve compatibility with existing versioned Azure deployments.
            self._client = AsyncAzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=api_version,
                timeout=client_timeout,
            )

    def _prepare_request_kwargs(
        self,
        kwargs: dict,
        *,
        has_tools: bool = False,
    ) -> dict:
        request_kwargs = dict(kwargs)
        if not self._model_name.lower().startswith("gpt-5"):
            return request_kwargs

        # Azure reasoning models reject legacy sampling controls and max_tokens.
        max_tokens = request_kwargs.pop("max_tokens", None)
        if max_tokens is not None:
            request_kwargs.setdefault("max_completion_tokens", max_tokens)
        for unsupported in (
            "temperature",
            "top_p",
            "presence_penalty",
            "frequency_penalty",
            "logprobs",
            "top_logprobs",
            "logit_bias",
        ):
            request_kwargs.pop(unsupported, None)

        # GPT-5.6 Chat Completions only permits function tools when reasoning is
        # disabled. The TOR application stays on Chat Completions for now.
        if has_tools and self._model_name.lower().startswith("gpt-5.6"):
            request_kwargs["reasoning_effort"] = "none"
        return request_kwargs
