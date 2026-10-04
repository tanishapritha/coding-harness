from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import docker


@dataclass(frozen=True)
class SandboxResult:
    exit_code: int
    output: str


class DockerSandbox:
    """Run workspace commands inside a disposable container.

    The workspace directory is mounted at /workspace. Network is disabled by
    default. This is the execution boundary for hosted Forge workspaces.
    """

    def __init__(self, image: str = "python:3.13-slim") -> None:
        self.client = docker.from_env()
        self.image = image

    def ensure_image(self) -> None:
        try:
            self.client.images.get(self.image)
        except docker.errors.ImageNotFound:
            self.client.images.pull(self.image)

    def run(self, workspace: str | Path, command: str, timeout: int = 60) -> SandboxResult:
        self.ensure_image()
        container = self.client.containers.run(
            self.image,
            ["sh", "-lc", command],
            volumes={str(Path(workspace).resolve()): {"bind": "/workspace", "mode": "rw"}},
            working_dir="/workspace",
            network_disabled=True,
            mem_limit="1g",
            nano_cpus=1_000_000_000,
            pids_limit=256,
            detach=True,
            remove=False,
        )
        try:
            result = container.wait(timeout=timeout)
            output = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
            return SandboxResult(int(result["StatusCode"]), output[-20000:])
        except Exception as exc:
            try:
                container.kill()
            except Exception:
                pass
            raise RuntimeError(f"sandbox command failed: {exc}") from exc
        finally:
            try:
                container.remove(force=True)
            except Exception:
                pass
