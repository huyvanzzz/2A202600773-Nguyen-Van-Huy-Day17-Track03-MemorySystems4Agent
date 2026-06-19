from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderConfig:
    """Student TODO: define the provider configuration shared by the agents.

    Required providers for this lab:
    - openai
    - custom (OpenAI-compatible base URL)
    - gemini
    - anthropic
    - ollama
    - openrouter
    """

    provider: str
    model_name: str
    temperature: float
    api_key: str | None = None
    base_url: str | None = None


def normalize_provider(value: str) -> str:
    """Student TODO: map aliases like `anthorpic` -> `anthropic`."""
    if not value:
        return "custom"
    val = value.lower().strip()
    if val in ("openai", "gpt"):
        return "openai"
    if val in ("gemini", "google", "google-generative-ai"):
        return "gemini"
    if val in ("anthropic", "claude", "anthorpic"):
        return "anthropic"
    if val == "ollama":
        return "ollama"
    if val == "openrouter":
        return "openrouter"
    return "custom"


def build_chat_model(config: ProviderConfig):
    """Student TODO: instantiate the real chat model for the selected provider.

    Pseudocode:
    - `openai` -> `ChatOpenAI`
    - `custom` -> `ChatOpenAI` with `base_url`
    - `gemini` -> `ChatGoogleGenerativeAI`
    - `anthropic` -> `ChatAnthropic`
    - `ollama` -> `ChatOllama`
    - `openrouter` -> `ChatOpenRouter`
    """
    provider = normalize_provider(config.provider)
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key,
        )
    elif provider == "custom":
        from langchain_openai import ChatOpenAI
        import httpx
        http_client = httpx.Client(verify=False)
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key,
            base_url=config.base_url,
            http_client=http_client,
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        import os
        api_key = config.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        return ChatGoogleGenerativeAI(
            model=config.model_name,
            temperature=config.temperature,
            google_api_key=api_key,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key,
        )
    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        base_url = config.base_url or "http://localhost:11434"
        return ChatOllama(
            model=config.model_name,
            temperature=config.temperature,
            base_url=base_url,
        )
    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI
        base_url = config.base_url or "https://openrouter.ai/api/v1"
        return ChatOpenAI(
            model=config.model_name,
            temperature=config.temperature,
            api_key=config.api_key,
            base_url=base_url,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

