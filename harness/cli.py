from __future__ import annotations

import argparse
import json

from .agent import AgentRuntime
from .config import Settings


def main() -> None:
    parser = argparse.ArgumentParser(prog="forge")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run")
    run.add_argument("task")
    run.add_argument("--workspace", default=".")

    args = parser.parse_args()

    if args.command == "run":
        runtime = AgentRuntime(args.workspace, Settings())

        def show(event: dict):
            print(f"[{event['type']}] {json.dumps(event['data'], ensure_ascii=False)}")

        state = runtime.run(args.task, show)
        print(json.dumps(state.as_dict(), indent=2, default=str))


if __name__ == "__main__":
    main()
