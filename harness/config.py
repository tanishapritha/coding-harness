from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _provider() -> str:
    value = os.getenv("FORGE_PROVIDER", "").strip().lower()
    if value:
        return value
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "openrouter"


def _default_model(provider: str) -> str:
    return {
        "groq": "openai/gpt-oss-20b",
        "openrouter": "openai/gpt-4o-mini",
        "openai": "gpt-4o-mini",
    }.get(provider, "openai/gpt-4o-mini")


def _api_key(provider: str) -> str:
    keys = {
        "groq": os.getenv("GROQ_API_KEY", ""),
        "openrouter": os.getenv("OPENROUTER_API_KEY", ""),
        "openai": os.getenv("OPENAI_API_KEY", ""),
    }
    return keys.get(provider, "")


def _base_url(provider: str) -> str:
    return {
        "groq": "https://api.groq.com/openai/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "openai": "https://api.openai.com/v1",
    }.get(provider, "")


@dataclass(frozen=True)
class Settings:
    provider: str = _provider()
    model: str = os.getenv("FORGE_MODEL", _default_model(_provider()))
    api_key: str = _api_key(_provider())
    base_url: str = os.getenv("FORGE_BASE_URL", _base_url(_provider()))
    max_iterations: int = int(os.getenv("FORGE_MAX_ITERATIONS", "20"))
    command_timeout: int = int(os.getenv("FORGE_COMMAND_TIMEOUT", "30"))

    def __post_init__(self) -> None:
        if self.provider not in {"groq", "openrouter", "openai"}:
            raise ValueError(
                f"Unsupported FORGE_PROVIDER={self.provider!r}. "
                "Use groq, openrouter, or openai."
            )
