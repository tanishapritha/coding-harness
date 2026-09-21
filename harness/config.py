from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    model: str = os.getenv("FORGE_MODEL", "openai/gpt-4o-mini")
    api_key: str = os.getenv("OPENROUTER_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    base_url: str = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    max_iterations: int = int(os.getenv("FORGE_MAX_ITERATIONS", "20"))
    command_timeout: int = int(os.getenv("FORGE_COMMAND_TIMEOUT", "30"))
