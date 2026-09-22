from __future__ import annotations

import json
import os
import streamlit as st

from harness.agent import AgentRuntime
from harness.config import Settings
from harness.memory.sqlite import SQLiteMemory
from harness.trajectories.store import TrajectoryStore
from harness.workspace import Workspace

st.set_page_config(page_title="Forge", page_icon="⚒", layout="wide")

for key, default in {"runtime": None, "state": None, "events": [], "repo": None}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("⚒ Forge")
st.caption("A local runtime for reliable AI coding agents")

with st.sidebar:
    st.header("Repository")
    repo_input = st.text_input("Repository path", value=st.session_state.repo or os.getcwd())
    if st.button("Connect repository", use_container_width=True):
        try:
            ws = Workspace(repo_input)
            st.session_state.repo = str(ws.root)
            st.success(f"Connected: {ws.root.name}")
        except Exception as exc:
            st.error(str(exc))
    model = st.text_input("Model", value=os.getenv("FORGE_MODEL", "openai/gpt-4o-mini"))
    max_iterations = st.number_input("Max iterations", 1, 100, 20)
    timeout = st.number_input("Command timeout (s)", 5, 300, 30)
    st.divider()
    st.caption("Forge v0.2 • local execution • SQLite memory")

repo = st.session_state.repo
if not repo:
    st.info("Connect a Git repository to start.")
    st.stop()

try:
    ws = Workspace(repo)
except Exception as exc:
    st.error(str(exc))
    st.stop()

memory = SQLiteMemory("~/.forge/forge.db", str(ws.root).lower())
status = ws.git("status", "--short") if ws.is_git_repo else "Not a Git repository"
branch = ws.git("branch", "--show-current") if ws.is_git_repo else "-"

m1, m2, m3, m4 = st.columns(4)
m1.metric("Repository", ws.root.name)
m2.metric("Branch", branch or "detached")
m3.metric("Files", len(ws.list_files()))
m4.metric("Memory", len(memory.all()))

build, history, system = st.tabs(["Build", "Runs", "System"])

with build:
    left, main, right = st.columns([0.22, 0.53, 0.25], gap="medium")

    with left:
        st.subheader("Repository")
        st.caption(str(ws.root))
        st.code(status or "clean")
        files = ws.list_files()
        st.write(f"{len(files)} files")
        st.code("\n".join(files[:150]), language=None)

    with main:
        st.subheader("Task")
        task = st.text_area(
            "What should Forge do?",
            placeholder="Fix the failing authentication tests. Inspect the repo, make the smallest change, and verify it.",
            height=130,
            label_visibility="collapsed",
        )
        if st.button("Run Forge", type="primary", use_container_width=True):
            if not task.strip():
                st.warning("Enter a task first.")
            else:
                base = Settings()
                settings = Settings(
                    model=model,
                    api_key=base.api_key,
                    base_url=base.base_url,
                    max_iterations=int(max_iterations),
                    command_timeout=int(timeout),
                )
                try:
                    runtime = AgentRuntime(str(ws.root), settings)
                    st.session_state.runtime = runtime
                    st.session_state.events = []
                    st.session_state.state = None
                    with st.status("Forge is working...", expanded=True) as live:
                        def on_event(event):
                            st.session_state.events.append(event)
                            live.write(f"**{event['type']}** — {event['data']}")
                        state = runtime.run(task, on_event)
                        live.update(
                            label=f"Forge {state.status.lower()}",
                            state="complete" if state.status == "COMPLETED" else "error",
                            expanded=False,
                        )
                    st.session_state.state = state
                except Exception as exc:
                    st.error(str(exc))

        state = st.session_state.state
        if state:
            st.divider()
            st.subheader("Run")
            a, b, c, d = st.columns(4)
            a.metric("Status", state.status)
            b.metric("Iteration", f"{state.iteration}/{state.max_iterations}")
            c.metric("Tools", state.tool_calls)
            d.metric("Run ID", state.run_id)

            ctx = getattr(st.session_state.runtime, "last_context", None)
            if ctx:
                st.subheader("Context")
                st.write(f"{len(ctx.files)} files • {len(ctx.memories)} memories • ~{ctx.token_estimate:,} tokens")
                with st.expander("Files given to agent"):
                    for f in ctx.files:
                        st.write(f"**{f.path}** — {f.score:.2f} — {f.reason}")
                with st.expander("Repository memory"):
                    st.json(ctx.memories)

            st.subheader("Verification")
            st.json(state.verification or {"status": "not finished"})
            st.subheader("Changed files")
            st.write(state.changed_files or "No file changes recorded")

    with right:
        st.subheader("Memory")
        for m in memory.all()[:20]:
            st.write(f"**{m['confidence']:.2f}** — {m['content']}")
        st.divider()
        st.subheader("Events")
        if st.session_state.events:
            for e in st.session_state.events[-30:]:
                st.write(f"`{e['type']}`")
        else:
            st.caption("No run yet.")

    st.divider()
    d1, d2 = st.columns(2)
    with d1:
        st.subheader("Git diff")
        st.code(ws.git("diff", "--", ".") if ws.is_git_repo else "Not a Git repository", language="diff")
    with d2:
        st.subheader("Open file")
        selected = st.text_input("Relative path", placeholder="src/main.py", label_visibility="collapsed")
        if selected:
            try:
                target = ws.safe_path(selected)
                st.code(target.read_text(encoding="utf-8"), language=target.suffix.lstrip(".") or "text", line_numbers=True)
            except Exception as exc:
                st.error(str(exc))

with history:
    st.subheader("Run history")
    store = TrajectoryStore()
    runs = sorted([p for p in store.base.iterdir() if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)[:30]
    if not runs:
        st.caption("No persisted runs yet.")
    for p in runs:
        state_file = p / "state.json"
        if state_file.exists():
            data = json.loads(state_file.read_text(encoding="utf-8"))
            with st.expander(f"{data.get('run_id')} • {data.get('status')} • {data.get('task','')[:80]}"):
                st.json(data)
                events_file = p / "events.jsonl"
                st.code(events_file.read_text(encoding="utf-8") if events_file.exists() else "No events", language="json")
                st.caption(str(p))

with system:
    st.subheader("Forge runtime")
    st.code("""Repository
  ↓
Context Engine ──→ SQLite Memory
  ↓
Agent Runtime
  ↓
Model
  ↓
Tool Registry → Policy → Local Executor
  ↓
Verification
  ↓
Trajectory + Logs + optional Langfuse trace""")
    st.write("**Tools:** list_files, read_file, write_file, run_command, run_tests, git_status, git_diff")
    st.write("**Safety:** workspace containment, credential protection, destructive command blocking, timeouts, iteration limit, independent verification")
    st.write("**Observability:** terminal logs + ~/.forge/runs + optional Langfuse")
