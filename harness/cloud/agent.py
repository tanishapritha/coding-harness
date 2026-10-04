from __future__ import annotations
from pathlib import Path
from .sandbox import DockerSandbox
from ..workspace import Workspace

class SandboxedWorkspace(Workspace):
    """Workspace filesystem + git remain on the worker; shell commands execute in Docker."""
    def __init__(self,root:str|Path,image:str|None=None)->None:
        super().__init__(root)
        self.sandbox=DockerSandbox(image or "python:3.13-slim")

    def run(self,command:str,timeout:int=30)->tuple[int,str]:
        result=self.sandbox.run(self.root,command,timeout)
        return result.exit_code,result.output
