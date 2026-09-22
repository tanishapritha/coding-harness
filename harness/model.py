from __future__ import annotations

import json
from openai import OpenAI

from .config import Settings


SYSTEM_PROMPT = """You are the coding agent inside Forge, a controlled software-engineering runtime.

Work only through the provided tools. Inspect before editing. Make minimal, coherent changes.
Use tests and repository evidence instead of guessing. Store memory only for durable, evidence-backed repository facts; never store guesses or temporary task details. Never claim a task is complete until
verification evidence exists. If a tool is denied, adapt to the policy rather than attempting
to bypass it.

Your output is tool calls or a concise final status. Do not emit hidden reasoning.
"""


class Model:
    def __init__(self, settings: Settings):
        if not settings.api_key:
            raise RuntimeError("Set OPENROUTER_API_KEY or OPENAI_API_KEY before running the agent.")
        self.client = OpenAI(api_key=settings.api_key, base_url=settings.base_url)
        self.model = settings.model

    def complete(self, messages: list[dict], tools: list[dict]):
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1,
        ).choices[0].message
