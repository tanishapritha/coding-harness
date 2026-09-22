from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class ContextFile:
    path: str
    score: float
    reason: str
    content: str

@dataclass
class ContextBundle:
    task: str
    repository: str
    files: list[ContextFile] = field(default_factory=list)
    memories: list[dict] = field(default_factory=list)
    git_status: str = ""
    git_diff: str = ""
    token_estimate: int = 0

    def prompt(self) -> str:
        parts = [f"TASK:\n{self.task}", f"REPOSITORY:\n{self.repository}"]
        if self.memories:
            parts.append("REPOSITORY MEMORY:\n" + "\n".join(f"- {m['content']}" for m in self.memories))
        if self.git_status:
            parts.append("GIT STATUS:\n" + self.git_status)
        if self.git_diff:
            parts.append("CURRENT DIFF:\n" + self.git_diff[-12000:])
        if self.files:
            body = []
            for f in self.files:
                body.append(f"\n--- {f.path} (relevance {f.score:.2f}: {f.reason}) ---\n{f.content}")
            parts.append("RELEVANT FILES:\n" + "".join(body))
        return "\n\n".join(parts)
