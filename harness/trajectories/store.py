from __future__ import annotations

import json
from pathlib import Path

class TrajectoryStore:
    def __init__(self, base_dir: str | Path | None=None):
        self.base=Path(base_dir or "~/.forge/runs").expanduser()
        self.base.mkdir(parents=True,exist_ok=True)

    def path(self, run_id):
        p=self.base/run_id
        p.mkdir(parents=True,exist_ok=True)
        return p

    def save_json(self, run_id, name, data):
        p=self.path(run_id)/name
        p.write_text(json.dumps(data,indent=2,default=str),encoding="utf-8")
        return p

    def append_event(self, run_id, event):
        p=self.path(run_id)/"events.jsonl"
        with p.open("a",encoding="utf-8") as f:
            f.write(json.dumps(event,default=str)+"\n")

    def save_run(self, state, context=None):
        p=self.path(state.run_id)
        self.save_json(state.run_id,"metadata.json",{"run_id":state.run_id,"task":state.task,"workspace":state.workspace})
        self.save_json(state.run_id,"state.json",state.as_dict())
        if context is not None: self.save_json(state.run_id,"context.json",context)
        return p
