from __future__ import annotations

from typing import Any, Callable

from .memory.sqlite import SQLiteMemory
from .policy import PolicyEngine
from .workspace import Workspace


class ToolRegistry:
    def __init__(
        self,
        workspace: Workspace,
        policy: PolicyEngine,
        timeout: int = 30,
        memory: SQLiteMemory | None = None,
        run_id: str | None = None,
    ):
        self.workspace = workspace
        self.policy = policy
        self.timeout = timeout
        self.memory = memory
        self.run_id = run_id
        self.handlers: dict[str, Callable[..., Any]] = {
            "list_files": self.list_files,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "run_command": self.run_command,
            "run_tests": self.run_tests,
            "git_status": self.git_status,
            "git_diff": self.git_diff,
            "remember_memory": self.remember_memory,
            "search_memory": self.search_memory,
        }

    def schemas(self) -> list[dict]:
        return [
            {"type":"function","function":{"name":"list_files","description":"List files in the workspace.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"read_file","description":"Read a UTF-8 text file.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
            {"type":"function","function":{"name":"write_file","description":"Create or replace a UTF-8 text file.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
            {"type":"function","function":{"name":"run_command","description":"Run a shell command in the workspace. Use for project commands and tests.","parameters":{"type":"object","properties":{"command":{"type":"string"}},"required":["command"]}}},
            {"type":"function","function":{"name":"run_tests","description":"Run the repository test suite. Prefer this over raw test commands.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"git_status","description":"Show git status.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"git_diff","description":"Show the current git diff.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"remember_memory","description":"Store a durable repository fact supported by evidence.","parameters":{"type":"object","properties":{"content":{"type":"string"},"confidence":{"type":"number","minimum":0,"maximum":1}},"required":["content"]}}},
            {"type":"function","function":{"name":"search_memory","description":"Search persistent repository memory before making architecture decisions.","parameters":{"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer","minimum":1,"maximum":20}},"required":["query"]}}},
        ]

    def execute(self, name: str, arguments: dict) -> dict:
        if name not in self.handlers:
            return {"ok": False, "error": f"unknown tool: {name}"}
        decision = self.policy.check(name, arguments)
        if not decision.allowed:
            return {"ok": False, "error": decision.reason, "policy": "DENIED"}
        try:
            result = self.handlers[name](**arguments)
            return {"ok": True, "result": result, "policy": "ALLOWED"}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "policy": "ALLOWED"}

    def list_files(self) -> list[str]:
        return self.workspace.list_files()

    def read_file(self, path: str) -> str:
        return self.workspace.read_file(path)

    def write_file(self, path: str, content: str) -> str:
        return self.workspace.write_file(path, content)

    def run_command(self, command: str) -> dict:
        code, output = self.workspace.run(command, self.timeout)
        return {"exit_code": code, "output": output[-12000:]}

    def run_tests(self) -> dict:
        files = self.workspace.list_files()
        if any(f.startswith("tests/") or f.startswith("test_") for f in files):
            command = "pytest -q"
        elif "package.json" in files:
            command = "npm test -- --run"
        else:
            return {"skipped": True, "reason": "No supported test layout detected"}
        code, output = self.workspace.run(command, self.timeout)
        return {"exit_code": code, "output": output[-12000:]}

    def git_status(self) -> str:
        return self.workspace.git("status", "--short")

    def git_diff(self) -> str:
        return self.workspace.git("diff", "--", ".")

    def remember_memory(self, content: str, confidence: float = 0.7) -> dict:
        if self.memory is None:
            return {"stored": False, "reason": "memory disabled"}
        memory_id = self.memory.remember(content, source_run=self.run_id, confidence=confidence)
        return {"stored": True, "memory_id": memory_id, "content": content}

    def update_plan(self, steps: list[str]) -> dict:\n        if self.state is None:\n            return {"updated": False, "reason": "state unavailable"}\n        self.state.plan = [s.strip() for s in steps if s.strip()]\n        return {"updated": True, "plan": self.state.plan}\n\n    def search_memory(self, query: str, limit: int = 8) -> list[dict]:
        if self.memory is None:
            return []
        return self.memory.search(query, limit=limit)
