"""Azure GPT reasoning-model request compatibility."""

from app.providers.llm.azure_foundry_provider import AzureFoundryLLMProvider


def _provider(model: str) -> AzureFoundryLLMProvider:
    provider = object.__new__(AzureFoundryLLMProvider)
    provider._model_name = model
    return provider


def test_gpt_56_uses_reasoning_token_parameter_and_drops_sampling() -> None:
    provider = _provider("gpt-5.6-luna")

    result = provider._prepare_request_kwargs(
        {"max_tokens": 4096, "temperature": 0.3, "top_p": 0.9}
    )

    assert result == {"max_completion_tokens": 4096}


def test_gpt_56_disables_reasoning_when_chat_tools_are_present() -> None:
    provider = _provider("gpt-5.6-luna")

    result = provider._prepare_request_kwargs({}, has_tools=True)

    assert result == {"reasoning_effort": "none"}


def test_non_reasoning_azure_deployment_keeps_existing_parameters() -> None:
    provider = _provider("gpt-4o-mini")
    original = {"max_tokens": 1024, "temperature": 0.2}

    assert provider._prepare_request_kwargs(original) == original
