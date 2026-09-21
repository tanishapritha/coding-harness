from __future__ import annotations

import os
import subprocess
from pathlib import Path


class Workspace:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def safe_path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise PermissionError("Path escapes workspace")
        return candidate

    def list_files(self) -> list[str]:
        return sorted(
            str(p.relative_to(self.root))
            for p in self.root.rglob("*")
            if p.is_file() and ".git" not in p.parts
        )

    def read_file(self, path: str) -> str:
        return self.safe_path(path).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> str:
        target = self.safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return str(target.relative_to(self.root))

    def git(self, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=self.root,
            text=True,
            capture_output=True,
            timeout=30,
        )
        return (result.stdout + result.stderr).strip()

    def run(self, command: str, timeout: int = 30) -> tuple[int, str]:
        result = subprocess.run(
            command,
            cwd=self.root,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return result.returncode, (result.stdout + result.stderr).strip()
