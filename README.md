# Forge

Forge is a local runtime for AI coding agents. It connects to an existing Git repository, builds task-specific context, retrieves repository memory, lets an agent operate through controlled tools, verifies the result, and records the run.

## Run it

Requirements: Python 3.11+ and Git.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
Copy-Item .env.example .env
```

Put your OpenRouter key in `.env`:

```env
OPENROUTER_API_KEY=...
FORGE_MODEL=openai/gpt-4o-mini
FORGE_MAX_ITERATIONS=20
FORGE_COMMAND_TIMEOUT=30
```

Start the real UI:

```powershell
streamlit run app.py
```

Then connect any local Git repository, enter a task, and run Forge.

CLI:

```powershell
forge run "Fix the failing authentication tests" --workspace C:\projects\my-api
forge inspect <run-id>
```

## What Forge currently does

- detects the Git root of a selected repository
- builds task-focused context instead of dumping the entire repository
- stores repository-scoped memory in SQLite at `~/.forge/forge.db`
- exposes controlled coding tools through a policy layer
- runs commands with timeouts
- independently verifies with `git diff --check` and supported tests
- records trajectories at `~/.forge/runs/<run-id>`
- emits structured terminal logs
- optionally exports traces to Langfuse when its keys are configured
- provides Streamlit UI for repository work, context, memory, runs, diffs and verification

## Development

Run tests:

```powershell
pytest -q
```

The GitHub Actions workflow runs the same tests and Ruff checks on pushes and pull requests.

## Architecture

```
Streamlit / CLI
      |
   Forge Core
      |
  Context ---- Memory
      |
  Agent Runtime
      |
 Model Provider
      |
 Tool Registry -> Policy -> Local Executor
      |
 Verification
      |
 Trajectory + Logs + optional Langfuse
```

Forge is intentionally local-first. Cloud execution, remote sandboxes, GitHub automation, distributed workers and multi-user infrastructure are later layers.
