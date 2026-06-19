from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from model_provider import ProviderConfig


@dataclass
class LabConfig:
    """Student TODO: define the shared configuration for the lab.

    Hints:
    - Keep paths for the repo root, dataset directory, and state directory.
    - Add compact-memory settings such as threshold and number of messages to keep.
    - Add provider settings for `openai`, `custom`, `gemini`, `anthropic`, `ollama`, and `openrouter`.
    """

    base_dir: Path
    data_dir: Path
    state_dir: Path
    compact_threshold_tokens: int
    compact_keep_messages: int
    model: ProviderConfig
    judge_model: ProviderConfig


def load_config(base_dir: Path | None = None) -> LabConfig:
    """Student TODO: load environment variables and return a LabConfig.

    Pseudocode:
    1. Resolve the repo root or default to the current file parent.
    2. Optionally load values from `.env`.
    3. Create `state/` if it does not exist.
    4. Return a populated LabConfig instance.
    """
    import os
    from dotenv import load_dotenv

    root = (base_dir or Path(__file__).resolve().parent.parent).resolve()
    
    # Load .env
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    # Paths
    data_dir = root / "data"
    state_dir = root / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    # Compact Memory Settings
    compact_threshold_tokens = int(os.getenv("COMPACT_THRESHOLD_TOKENS", "1000"))
    compact_keep_messages = int(os.getenv("COMPACT_KEEP_MESSAGES", "4"))

    # Provider configurations
    llm_provider = os.getenv("LLM_PROVIDER", "custom")
    llm_model = os.getenv("LLM_MODEL", "gemini-1.5-flash")

    # Resolve API key and Base URL based on provider
    def resolve_creds(provider: str, prefix: str = "") -> tuple[str | None, str | None]:
        # prefix can be "JUDGE_" or ""
        prov = provider.lower().strip()
        api_key = os.getenv(f"{prefix}API_KEY")
        base_url = os.getenv(f"{prefix}BASE_URL")
        
        # Fallback to provider-specific env variables
        if prov == "openai":
            api_key = api_key or os.getenv(f"{prefix}OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        elif prov == "custom":
            api_key = api_key or os.getenv(f"{prefix}CUSTOM_API_KEY") or os.getenv("CUSTOM_API_KEY")
            base_url = base_url or os.getenv(f"{prefix}CUSTOM_BASE_URL") or os.getenv("CUSTOM_BASE_URL")
        elif prov == "gemini":
            api_key = api_key or os.getenv(f"{prefix}GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        elif prov == "anthropic":
            api_key = api_key or os.getenv(f"{prefix}ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        elif prov == "ollama":
            base_url = base_url or os.getenv(f"{prefix}OLLAMA_BASE_URL") or os.getenv("OLLAMA_BASE_URL")
        elif prov == "openrouter":
            api_key = api_key or os.getenv(f"{prefix}OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
            base_url = base_url or os.getenv(f"{prefix}OPENROUTER_BASE_URL") or os.getenv("OPENROUTER_BASE_URL")
        
        return api_key, base_url

    # Setup primary LLM config
    api_key, base_url = resolve_creds(llm_provider, "")
    model_config = ProviderConfig(
        provider=llm_provider,
        model_name=llm_model,
        temperature=0.0,
        api_key=api_key,
        base_url=base_url,
    )

    # Setup Judge LLM config
    judge_provider = os.getenv("JUDGE_PROVIDER", llm_provider)
    judge_model_name = os.getenv("JUDGE_MODEL", llm_model)
    
    # Try with JUDGE_ prefix first
    j_api_key, j_base_url = resolve_creds(judge_provider, "JUDGE_")
    if not j_api_key and not j_base_url:
        # Fallback to main creds if same provider
        if judge_provider == llm_provider:
            j_api_key = api_key
            j_base_url = base_url
        else:
            j_api_key, j_base_url = resolve_creds(judge_provider, "")
            
    judge_config = ProviderConfig(
        provider=judge_provider,
        model_name=judge_model_name,
        temperature=0.0,
        api_key=j_api_key,
        base_url=j_base_url,
    )

    return LabConfig(
        base_dir=root,
        data_dir=data_dir,
        state_dir=state_dir,
        compact_threshold_tokens=compact_threshold_tokens,
        compact_keep_messages=compact_keep_messages,
        model=model_config,
        judge_model=judge_config,
    )

