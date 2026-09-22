from __future__ import annotations

import json
import uuid
from typing import Callable

from .config import Settings
from .context import ContextEngine
from .events import EventBus
from .memory.sqlite import SQLiteMemory
from .model import Model, SYSTEM_PROMPT
from .observability.logger import get_logger
from .observability.tracing import TraceRecorder
from .policy import PolicyEngine
from .state import RunState
from .tools import ToolRegistry
from .trajectories.store import TrajectoryStore
from .workspace import Workspace


class AgentRuntime:
    def __init__(self, workspace_path: str, settings: Settings | None = None):
        self.settings=settings or Settings()
        self.run_id=uuid.uuid4().hex[:12]
        self.workspace=Workspace(workspace_path)
        self.events=EventBus()
        self.logger=get_logger()
        self.trace=TraceRecorder(self.run_id)
        repo_id=str(self.workspace.root).lower()
        self.memory=SQLiteMemory("~/.forge/forge.db",repo_id)
        self.context_engine=ContextEngine(self.workspace,self.memory)
        self.state=RunState(self.run_id,"",str(self.workspace.root),max_iterations=self.settings.max_iterations)
        self.tools=ToolRegistry(self.workspace,PolicyEngine(),self.settings.command_timeout)
        self.model=Model(self.settings)
        self.trajectory=TrajectoryStore()
        self.last_context=None

    def run(self, task: str, on_event: Callable[[dict],None] | None=None) -> RunState:
        self.state.task=task
        emit=lambda typ,**data:self._emit(typ,on_event,**data)
        emit("RUN_STARTED",run_id=self.run_id,task=task,workspace=str(self.workspace.root))
        self.logger.info("run started: %s",task,extra={"run_id":self.run_id})
        self.state.transition("PLANNING")

        try:
            with self.trace.span("context.build",{"task":task}):
                context=self.context_engine.build(task)
            self.last_context=context
            emit("CONTEXT_BUILT",files=[f.path for f in context.files],memories=context.memories,token_estimate=context.token_estimate)
            self.trajectory.save_json(self.run_id,"context.json",{
                "task":context.task,"token_estimate":context.token_estimate,
                "files":[{"path":f.path,"score":f.score,"reason":f.reason} for f in context.files],
                "memories":context.memories,"git_status":context.git_status
            })
        except Exception as exc:
            return self._fail(emit,"CONTEXT_ERROR",str(exc))

        messages=[
            {"role":"system","content":SYSTEM_PROMPT},
            {"role":"user","content":context.prompt()+"\n\nStart by inspecting the repository. Make the smallest coherent change. Use tools for all repository interaction. Run tests before finishing."},
        ]
        for iteration in range(self.settings.max_iterations):
            self.state.iteration=iteration+1
            self.state.transition("EXECUTING")
            emit("STATE_CHANGED",state=self.state.status,iteration=self.state.iteration)
            try:
                with self.trace.span(f"agent.iteration.{iteration+1}",{"iteration":iteration+1}):
                    message=self.model.complete(messages,self.tools.schemas())
            except Exception as exc:
                return self._fail(emit,"MODEL_ERROR",str(exc))

            calls=message.tool_calls or []
            messages.append({"role":"assistant","content":message.content,"tool_calls":[{"id":c.id,"type":"function","function":{"name":c.function.name,"arguments":c.function.arguments}} for c in calls]})
            if not calls:
                return self._verify_and_finish(emit)

            for call in calls:
                name=call.function.name
                try: args=json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError: args={}
                self.state.tool_calls+=1
                emit("TOOL_REQUESTED",tool=name,arguments=args)
                with self.trace.span(f"tool.{name}",{"arguments":args}):
                    result=self.tools.execute(name,args)
                emit("TOOL_COMPLETED" if result.get("ok") else "TOOL_FAILED",tool=name,result=result)
                if not result.get("ok"):
                    self.state.failures.append({"type":"TOOL_ERROR","tool":name,"error":result.get("error")})
                if name=="write_file" and result.get("ok"):
                    path=args.get("path")
                    if path and path not in self.state.changed_files:self.state.changed_files.append(path)
                messages.append({"role":"tool","tool_call_id":call.id,"content":json.dumps(result)})

        return self._fail(emit,"ITERATION_LIMIT","maximum agent iterations reached")

    def _verify_and_finish(self,emit):
        self.state.transition("VERIFYING")
        emit("VERIFICATION_STARTED")
        verification=self.verify()
        self.state.verification=verification
        if verification["passed"]:
            self.state.transition("COMPLETED")
            emit("RUN_COMPLETED",verification=verification)
        else:
            self.state.transition("FAILED")
            emit("RUN_FAILED",verification=verification)
        self._persist()
        self.trace.flush()
        return self.state

    def verify(self)->dict:
        diff=self.workspace.run("git diff --check",30) if self.workspace.is_git_repo else (0,"")
        files=self.workspace.list_files()
        tests={"skipped":True,"reason":"No supported test layout detected"}
        if any(f.startswith("tests/") or f.startswith("test_") for f in files):
            code,out=self.workspace.run("pytest -q",self.settings.command_timeout)
            tests={"exit_code":code,"output":out[-12000:],"skipped":False}
        return {"passed":diff[0]==0 and (tests.get("skipped") or tests.get("exit_code")==0),"diff_check":{"exit_code":diff[0],"output":diff[1][-4000:]},"tests":tests}

    def _fail(self,emit,kind,error):
        self.state.transition("FAILED")
        self.state.failures.append({"type":kind,"error":error})
        emit("RUN_FAILED",error=error,type=kind)
        self._persist(); self.trace.flush()
        self.logger.error("%s: %s",kind,error,extra={"run_id":self.run_id})
        return self.state

    def _persist(self):
        self.trajectory.save_run(self.state,self.last_context.prompt() if self.last_context else None)

    def _emit(self,typ,on_event,**data):
        event=self.events.emit(typ,**data).to_dict()
        self.trajectory.append_event(self.run_id,event)
        if on_event:on_event(event)
