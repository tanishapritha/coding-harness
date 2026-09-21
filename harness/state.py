from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Status = Literal[
    "CREATED", "PLANNING", "EXECUTING", "VERIFYING",
    "COMPLETED", "FAILED", "STOPPED"
]


@dataclass
class RunState:
    run_id: str
    task: str
    workspace: str
    status: Status = "CREATED"
    iteration: int = 0
    max_iterations: int = 20
    plan: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: int = 0
    changed_files: list[str] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)

    def transition(self, status: Status) -> None:
        self.status = status

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()
