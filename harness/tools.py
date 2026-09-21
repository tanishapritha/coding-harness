from __future__ import annotations

import json
from typing import Any, Callable

from .policy import PolicyEngine
from .workspace import Workspace


class ToolRegistry:
    def __init__(self, workspace: Workspace, policy: PolicyEngine, timeout: int = 30):
        self.workspace = workspace
        self.policy = policy
        self.timeout = timeout
        self.handlers: dict[str, Callable[..., Any]] = {
            "list_files": self.list_files,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "run_command": self.run_command,
            "run_tests": self.run_tests,
            "git_status": self.git_status,
            "git_diff": self.git_diff,
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
