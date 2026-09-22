from __future__ import annotations

from pathlib import Path
from ..workspace import Workspace

IGNORED_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist", "build"}
TEXT_EXTENSIONS = {".py",".js",".jsx",".ts",".tsx",".json",".yaml",".yml",".toml",".md",".txt",".sql",".html",".css",".scss",".java",".cpp",".c",".h",".hpp",".dart",".go",".rs",".env.example"}

class RepositoryScanner:
    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def files(self) -> list[str]:
        out=[]
        for p in self.workspace.root.rglob("*"):
            if not p.is_file() or any(part in IGNORED_DIRS for part in p.parts):
                continue
            try:
                rel=p.relative_to(self.workspace.root).as_posix()
                if p.suffix.lower() in TEXT_EXTENSIONS or p.name in {"Dockerfile","Makefile","README"}:
                    out.append(rel)
            except ValueError:
                pass
        return sorted(out)
