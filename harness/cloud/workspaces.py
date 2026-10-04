from __future__ import annotations
import os, shutil, subprocess, uuid
from dataclasses import dataclass
from pathlib import Path
from .sandbox import DockerSandbox

@dataclass(frozen=True)
class WorkspaceSpec:
    id:str
    path:Path
    repo:str
    branch:str

class DockerWorkspaceManager:
    def __init__(self,root:str|Path|None=None)->None:
        self.root=Path(root or os.getenv("FORGE_WORKSPACE_ROOT","~/.forge/workspaces")).expanduser().resolve()
        self.root.mkdir(parents=True,exist_ok=True)

    def _run(self,args:list[str],timeout:int=120,env:dict[str,str]|None=None)->str:
        result=subprocess.run(args,text=True,capture_output=True,timeout=timeout,env=env)
        if result.returncode: raise RuntimeError((result.stderr or result.stdout).strip())
        return result.stdout.strip()

    def _askpass(self,token:str)->dict[str,str]:
        script=self.root/"git-askpass.sh"
        script.write_text("#!/bin/sh\ncase \"$1\" in\n  *Username*) echo \"x-access-token\" ;;\n  *) echo \"$GIT_PASSWORD\" ;;\nesac\n",encoding="utf-8")
        try: script.chmod(0o700)
        except OSError: pass
        return {**os.environ,"GIT_ASKPASS":str(script),"GIT_TERMINAL_PROMPT":"0","GIT_USERNAME":"x-access-token","GIT_PASSWORD":token}

    def create(self,repo_full_name:str,base_branch:str="main",token:str|None=None,clone_url:str|None=None)->WorkspaceSpec:
        wid=uuid.uuid4().hex[:12]; path=self.root/wid; path.mkdir(parents=True,exist_ok=False)
        url=clone_url or f"https://github.com/{repo_full_name}.git"
        try:
            self._run(["git","clone","--depth","1","--branch",base_branch,url,str(path)],env=self._askpass(token) if token else None)
            branch=f"forge/{wid}"
            self._run(["git","-C",str(path),"checkout","-b",branch])
            return WorkspaceSpec(wid,path,repo_full_name,branch)
        except Exception:
            shutil.rmtree(path,ignore_errors=True); raise

    def status(self,workspace_id:str)->dict[str,str]:
        path=self.root/workspace_id
        if not path.exists(): raise FileNotFoundError(workspace_id)
        return {"workspace_id":workspace_id,"path":str(path),"branch":self._run(["git","-C",str(path),"branch","--show-current"]),"status":self._run(["git","-C",str(path),"status","--short"])}

    def destroy(self,workspace_id:str)->None:
        path=self.root/workspace_id
        if path.exists(): shutil.rmtree(path,ignore_errors=True)

    def run_sandbox(self,workspace_id:str,command:str,timeout:int=60)->dict[str,object]:
        path=self.root/workspace_id
        if not path.exists(): raise FileNotFoundError(workspace_id)
        result=DockerSandbox().run(path,command,timeout)
        return {"exit_code":result.exit_code,"output":result.output}

    def commit_and_push(self,workspace_id:str,token:str,message:str)->dict[str,str]:
        path=self.root/workspace_id
        if not path.exists(): raise FileNotFoundError(workspace_id)
        env=self._askpass(token)
        status=self._run(["git","-C",str(path),"status","--porcelain"])
        if not status: raise RuntimeError("No changes to publish")
        self._run(["git","-C",str(path),"add","-A"])
        self._run(["git","-C",str(path),"commit","-m",message],env=env)
        self._run(["git","-C",str(path),"push","-u","origin","HEAD"],env=env)
        branch=self._run(["git","-C",str(path),"branch","--show-current"])
        return {"branch":branch,"status":status}
