from __future__ import annotations

import json
import uuid
from typing import Callable

from .config import Settings
from .events import EventBus
from .model import Model, SYSTEM_PROMPT
from .policy import PolicyEngine
from .state import RunState
from .tools import ToolRegistry
from .workspace import Workspace


class AgentRuntime:
    def __init__(self, workspace_path: str, settings: Settings | None = None):
        self.settings = settings or Settings()
        self.run_id = uuid.uuid4().hex[:8]
        self.workspace = Workspace(workspace_path)
        self.events = EventBus()
        self.state = RunState(
            run_id=self.run_id,
            task="",
            workspace=str(self.workspace.root),
            max_iterations=self.settings.max_iterations,
        )
        self.tools = ToolRegistry(self.workspace, PolicyEngine(), self.settings.command_timeout)
        self.model = Model(self.settings)

    def run(self, task: str, on_event: Callable[[dict], None] | None = None) -> RunState:
        self.state.task = task
        emit = lambda typ, **data: self._emit(typ, on_event, **data)
        emit("RUN_STARTED", run_id=self.run_id, task=task, workspace=str(self.workspace.root))
        self.state.transition("PLANNING")

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self._initial_prompt(task)},
        ]

        for iteration in range(self.settings.max_iterations):
            self.state.iteration = iteration + 1
            self.state.transition("EXECUTING")
            emit("STATE_CHANGED", state=self.state.status, iteration=self.state.iteration)

            try:
                message = self.model.complete(messages, self.tools.schemas())
            except Exception as exc:
                self.state.transition("FAILED")
                self.state.failures.append({"type": "MODEL_ERROR", "error": str(exc)})
                emit("RUN_FAILED", error=str(exc))
                return self.state

            messages.append({
                "role": "assistant",
                "content": message.content,
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.function.name, "arguments": call.function.arguments},
                    }
                    for call in (message.tool_calls or [])
                ],
            })

            if not message.tool_calls:
                self.state.transition("VERIFYING")
                emit("VERIFICATION_STARTED")
                verification = self.verify()
                self.state.verification = verification
                if verification["passed"]:
                    self.state.transition("COMPLETED")
                    emit("RUN_COMPLETED", verification=verification)
                else:
                    self.state.transition("FAILED")
                    emit("RUN_FAILED", verification=verification)
                return self.state

            for call in message.tool_calls:
                name = call.function.name
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                self.state.tool_calls += 1
                emit("TOOL_REQUESTED", tool=name, arguments=args)
                result = self.tools.execute(name, args)
                emit(
                    "TOOL_COMPLETED" if result.get("ok") else "TOOL_FAILED",
                    tool=name,
                    result=result,
                )
                if result.get("policy") == "DENIED":
                    self.state.failures.append({"type": "POLICY_DENIED", "tool": name, "result": result})
                if name == "write_file" and result.get("ok"):
                    path = args["path"]
                    if path not in self.state.changed_files:
                        self.state.changed_files.append(path)

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                })

        self.state.transition("FAILED")
        self.state.failures.append({"type": "ITERATION_LIMIT"})
        emit("RUN_FAILED", error="iteration limit reached")
        return self.state

    def verify(self) -> dict:
        diff_check = self.workspace.run("git diff --check", 30)
        files = self.workspace.list_files()
        tests = {"skipped": True, "reason": "No supported test layout detected"}
        if any(f.startswith("tests/") or f.startswith("test_") for f in files):
            code, output = self.workspace.run("pytest -q", 30)
            tests = {"exit_code": code, "output": output[-12000:], "skipped": False}
        return {
            "passed": diff_check[0] == 0 and (tests.get("skipped") or tests.get("exit_code") == 0),
            "diff_check": {"exit_code": diff_check[0], "output": diff_check[1][-4000:]},
            "tests": tests,
        }

    def _initial_prompt(self, task: str) -> str:
        files = self.workspace.list_files()
        return f"""Task:
{task}

Workspace:
{self.workspace.root}

Initial files:
{files[:300]}

Start by inspecting the repository. Create or modify only what is required.
Run tests before finishing when the repository supports them."""

    def _emit(self, typ: str, on_event, **data):
        event = self.events.emit(typ, **data).to_dict()
        if on_event:
            on_event(event)
