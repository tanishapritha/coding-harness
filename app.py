from __future__ import annotations
import os
from pathlib import Path
import streamlit as st
from harness.agent import AgentRuntime
from harness.config import Settings

st.set_page_config(page_title="Forge", page_icon="F", layout="wide")

if "events" not in st.session_state:
    st.session_state.events = []
if "state" not in st.session_state:
    st.session_state.state = None
if "runtime" not in st.session_state:
    st.session_state.runtime = None

st.title("Forge")
st.caption("Controlled runtime for AI coding agents")

with st.sidebar:
    st.subheader("Workspace")
    workspace = st.text_input("Repository path", value=os.getcwd())
    model = st.text_input("Model", value=os.getenv("FORGE_MODEL", "openai/gpt-4o-mini"))
    max_iterations = st.number_input("Max iterations", 1, 100, 20)
    command_timeout = st.number_input("Command timeout (s)", 5, 300, 30)
    st.divider()
    st.caption("Runtime")
    st.write("Filesystem: local workspace")
    st.write("Execution: subprocess")
    st.write("Policy: enabled")
    st.write("Verification: enabled")

build_tab, system_tab, runs_tab = st.tabs(["Build", "System", "Runs"])

with build_tab:
    left, center, right = st.columns([0.22, 0.50, 0.28], gap="medium")
    root = Path(workspace).expanduser().resolve()

    with left:
        st.subheader("Files")
        if root.exists():
            files = sorted(
                p.relative_to(root).as_posix()
                for p in root.rglob("*")
                if p.is_file() and ".git" not in p.parts
            )
            st.code("\n".join(files) if files else "Workspace is empty.", language=None)
        else:
            st.error("Workspace does not exist.")

    with center:
        st.subheader("Workspace")
        task = st.text_area("Task", placeholder="Describe the software change.", height=120)
        run_clicked = st.button("Run agent", type="primary", use_container_width=True)
        event_placeholder = st.empty()

        if run_clicked:
            if not task.strip():
                st.warning("Enter a task.")
            elif not root.exists():
                st.error("Workspace does not exist.")
            else:
                base = Settings()
                settings = Settings(
                    model=model,
                    api_key=base.api_key,
                    base_url=base.base_url,
                    max_iterations=int(max_iterations),
                    command_timeout=int(command_timeout),
                )
                runtime = AgentRuntime(str(root), settings)
                st.session_state.runtime = runtime
                st.session_state.events = []

                def on_event(event: dict):
                    st.session_state.events.append(event)
                    recent = st.session_state.events[-12:]
                    lines = ["[" + e["type"] + "] " + str(e["data"]) for e in recent]
                    event_placeholder.code("\n".join(lines), language=None)

                try:
                    st.session_state.state = runtime.run(task, on_event)
                except Exception as exc:
                    st.error(str(exc))

        st.subheader("Open file")
        selected_file = st.text_input("Path", placeholder="backend/main.py")
        if selected_file:
            try:
                target = (root / selected_file).resolve()
                if target != root and root not in target.parents:
                    raise PermissionError("Path is outside workspace")
                content = target.read_text(encoding="utf-8")
                language = target.suffix.lstrip(".") or "text"
                st.code(content, language=language, line_numbers=True)
            except Exception as exc:
                st.error(str(exc))

    with right:
        st.subheader("Agent")
        state = st.session_state.state
        if state:
            st.metric("State", state.status)
            st.metric("Iteration", state.iteration)
            st.metric("Tool calls", state.tool_calls)
            st.write("Task")
            st.write(state.task)
            st.write("Changed files")
            if state.changed_files:
                for path in state.changed_files:
                    st.write("- " + path)
            else:
                st.caption("No file changes recorded.")
            if state.verification:
                st.write("Verification")
                st.json(state.verification)
        else:
            st.caption("No run yet.")

    st.divider()
    diff_col, events_col = st.columns(2)

    with diff_col:
        st.subheader("Git diff")
        runtime = st.session_state.runtime
        if runtime:
            st.code(runtime.workspace.git("diff", "--", "."), language="diff")
        else:
            st.caption("Run the agent to inspect changes.")

    with events_col:
        st.subheader("Events")
        if st.session_state.events:
            lines = ["[" + e["type"] + "] " + str(e["data"]) for e in st.session_state.events]
            st.code("\n".join(lines), language=None)
        else:
            st.caption("No events.")

with system_tab:
    st.subheader("Runtime")
    st.code("Task\n  ↓\nAgent / model\n  ↓\nPolicy engine\n  ↓\nTool registry\n  ↓\nWorkspace executor\n  ↓\nObservation\n  ↓\nVerification\n  ↓\nCompleted / Failed", language=None)

    tools_col, policy_col = st.columns(2)
    with tools_col:
        st.subheader("Tools")
        for name, description in [
            ("list_files", "Explore workspace"),
            ("read_file", "Read repository file"),
            ("write_file", "Create or replace file"),
            ("run_command", "Execute shell command"),
            ("run_tests", "Run supported test suite"),
            ("git_status", "Inspect repository state"),
            ("git_diff", "Inspect changes"),
        ]:
            st.write("**" + name + "** — " + description)

    with policy_col:
        st.subheader("Guardrails")
        for rule in [
            "Workspace path containment",
            "Absolute/path traversal rejection",
            "Destructive command blocking",
            "git push blocking",
            "git reset/clean/checkout blocking",
            "Credential path protection",
            "Command timeout",
            "Maximum agent iterations",
            "Independent verification before completion",
        ]:
            st.write("✓ " + rule)

    st.subheader("Run state")
    state = st.session_state.state
    if state:
        st.json(state.as_dict())
    else:
        st.caption("No active run.")

with runs_tab:
    st.subheader("Current run")
    state = st.session_state.state
    if state:
        st.json(state.as_dict())
    else:
        st.caption("Run history persistence is intentionally deferred.")
