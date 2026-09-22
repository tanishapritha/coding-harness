from __future__ import annotations

import argparse
import json
from .agent import AgentRuntime
from .config import Settings
from .trajectories.store import TrajectoryStore


def main():
    parser=argparse.ArgumentParser(prog="forge")
    sub=parser.add_subparsers(dest="command",required=True)
    run=sub.add_parser("run"); run.add_argument("task"); run.add_argument("--workspace",default=".")
    inspect=sub.add_parser("inspect"); inspect.add_argument("run_id")
    args=parser.parse_args()
    if args.command=="run":
        runtime=AgentRuntime(args.workspace,Settings())
        def show(e): print(f"[{e['type']}] {json.dumps(e['data'],ensure_ascii=False,default=str)}")
        state=runtime.run(args.task,show)
        print(json.dumps(state.as_dict(),indent=2,default=str))
    elif args.command=="inspect":
        p=TrajectoryStore().path(args.run_id)
        state=p/"state.json"
        if not state.exists(): raise SystemExit(f"Run not found: {args.run_id}")
        print(state.read_text(encoding="utf-8"))

if __name__=="__main__": main()
