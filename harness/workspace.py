from __future__ import annotations

import subprocess
from pathlib import Path


class Workspace:
    def __init__(self, root: str | Path) -> None:
        requested = Path(root).expanduser().resolve()
        if not requested.exists() or not requested.is_dir():
            raise FileNotFoundError(f"Workspace does not exist: {requested}")
        self.root = self._find_git_root(requested)

    @staticmethod
    def _find_git_root(path: Path) -> Path:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path, text=True, capture_output=True)
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip()).resolve()
        return path

    @property
    def is_git_repo(self) -> bool:
        return (self.root / ".git").exists()

    def safe_path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise PermissionError("Path escapes workspace")
        return candidate

    def list_files(self) -> list[str]:
        ignored={".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build"}
        return sorted(str(p.relative_to(self.root)).replace("\\","/") for p in self.root.rglob("*") if p.is_file() and not any(x in ignored for x in p.parts))

    def read_file(self, path: str) -> str:
        return self.safe_path(path).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> str:
        target=self.safe_path(path)
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(content,encoding="utf-8")
        return str(target.relative_to(self.root)).replace("\\","/")

    def git(self,*args: str) -> str:
        result=subprocess.run(["git",*args],cwd=self.root,text=True,capture_output=True,timeout=30)
        return (result.stdout+result.stderr).strip()

    def run(self, command: str, timeout: int = 30) -> tuple[int,str]:
        try:
            result=subprocess.run(command,cwd=self.root,shell=True,text=True,capture_output=True,timeout=timeout)
            return result.returncode,(result.stdout+result.stderr).strip()
        except subprocess.TimeoutExpired as exc:
            output=(exc.stdout or "") + (exc.stderr or "")
            return 124,(output + f"\nCommand timed out after {timeout}s").strip()
