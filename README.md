# Forge

**A persistent local runtime for reliable AI coding agents.**

Forge is not a Cursor clone. It is the runtime underneath a coding agent: repository context, controlled tools, persistent memory, execution policy, verification, trajectories, and a UI for seeing what the agent actually did.

## What it does

`task → context → model → tools → edits → tests → verification → persistent trajectory`

The runtime can:
- inspect a repository and retrieve task-relevant context
- call filesystem, shell, git, test, and memory tools
- enforce workspace and command policies
- keep repository-scoped persistent memory in SQLite
- run multi-step coding tasks with iteration and timeout limits
- stop an active run
- independently verify git diffs and tests
- persist every run under `~/.forge/runs/<run_id>`
- expose the runtime through FastAPI
- provide a Next.js UI with live trajectory streaming

## Architecture

```
Next.js UI
    │
    ▼
FastAPI
    │
    ▼
AgentRuntime
 ├── ContextEngine ─── SQLiteMemory (~/.forge/forge.db)
 ├── Model
 ├── ToolRegistry ─── PolicyEngine ─── Workspace
 ├── Verification
 └── TrajectoryStore (~/.forge/runs)
```

## Setup

### 1. Backend

Python 3.11+ is required.

```bash
git clone https://github.com/tanishapritha/coding-harness.git
cd coding-harness

python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e .
```

Create `.env`:

```env
OPENROUTER_API_KEY=your_key
FORGE_MODEL=openai/gpt-4o-mini
```

Start the API:

```bash
uvicorn harness.api:app --reload --port 8000
```

API health: `http://127.0.0.1:8000/health`

### 2. Frontend

Node 20+ is recommended.

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`.

The UI connects to the backend at `http://127.0.0.1:8000`. To change it:

```env
NEXT_PUBLIC_FORGE_API=http://127.0.0.1:8000
```

## CLI

The original CLI remains available:

```bash
forge /path/to/repository "Fix the failing tests"
```

## Persistent state

Forge stores data outside the target repository:

- `~/.forge/forge.db` — repository-scoped long-term memory
- `~/.forge/runs/<run_id>/state.json` — final run state
- `~/.forge/runs/<run_id>/events.jsonl` — event trajectory
- `~/.forge/runs/<run_id>/context.json` — retrieved context

The same repository gets the same memory namespace across runs.

## Safety boundary

Forge is a local development harness, **not a production sandbox**. Shell commands execute on the host with policy checks and timeouts. Do not point it at an untrusted repository unless you add container/VM isolation.

## Test

```bash
pytest -q
```

## Next engineering layer

The base system is intentionally complete before adding a single hard research problem. Candidate directions include context selection, long-horizon reliability, failure diagnosis, trajectory evaluation, or safe autonomous execution.
