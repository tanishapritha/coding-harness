from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceSpec:
    id: str
    path: Path
    repo: str
    branch: str


class DockerWorkspaceManager:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or os.getenv("FORGE_WORKSPACE_ROOT", "~/.forge/workspaces")).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _run(self, args: list[str], timeout: int = 120) -> str:
        result = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError((result.stderr or result.stdout).strip())
        return result.stdout.strip()

    def create(self, repo_url: str, base_branch: str = "main") -> WorkspaceSpec:
        workspace_id = uuid.uuid4().hex[:12]
        path = self.root / workspace_id
        path.mkdir(parents=True, exist_ok=False)
        try:
            self._run(["git", "clone", "--depth", "1", "--branch", base_branch, repo_url, str(path)])
            branch = f"forge/{workspace_id}"
            self._run(["git", "-C", str(path), "checkout", "-b", branch])
            return WorkspaceSpec(workspace_id, path, repo_url, branch)
        except Exception:
            shutil.rmtree(path, ignore_errors=True)
            raise

    def status(self, workspace_id: str) -> dict[str, str]:
        path = self.root / workspace_id
        if not path.exists():
            raise FileNotFoundError(workspace_id)
        branch = self._run(["git", "-C", str(path), "branch", "--show-current"])
        status = self._run(["git", "-C", str(path), "status", "--short"])
        return {"workspace_id": workspace_id, "path": str(path), "branch": branch, "status": status}

    def destroy(self, workspace_id: str) -> None:
        path = self.root / workspace_id
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
