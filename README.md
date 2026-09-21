# Coding Harness

A controlled runtime for AI coding agents.

The first version combines a tool-using coding agent with an execution harness and a Streamlit control surface. The agent can inspect a real repository, modify files, run commands and tests, and receive structured observations. The harness owns tool registration, workspace boundaries, policy checks, runtime state, event tracing, and independent verification.

## Architecture

    Task
      |
    Agent / model
      |
    Policy engine
      |
    Tool registry
      |
    Workspace executor
      |
    Observation
      |
    Verification
      |
    Completed / Failed

The Streamlit application exposes the same runtime through two views:

- Build — repository files, task input, agent state, events, file viewer, and git diff.
- System — runtime architecture, registered tools, guardrails, and run state.

The CLI is also available:

    forge run "Add a health endpoint" --workspace ./my-project

## Setup

Python 3.11+:

    python -m venv .venv
    # Windows
    .venv\\Scripts\\activate
    # macOS/Linux
    source .venv/bin/activate

    pip install -e .
    copy .env.example .env

Set an OpenRouter or OpenAI-compatible key in .env:

    OPENROUTER_API_KEY=...
    FORGE_MODEL=openai/gpt-4o-mini

Run the UI:

    streamlit run app.py

For a local coding workspace, point the sidebar at the repository you want Forge to modify.

## Runtime behavior

1. Create a run and bind it to a workspace.
2. Give the model typed tools rather than unrestricted filesystem access.
3. Inspect the repository before editing.
4. Check every tool request against runtime policy.
5. Execute the approved operation.
6. Return the result to the model as an observation.
7. Continue until the model stops or the iteration limit is reached.
8. Independently verify the resulting workspace with git diff checks and supported tests.

The model decides what it wants to do. The harness decides whether and how that action executes.

## Current tool surface

- list_files
- read_file
- write_file
- run_command
- run_tests
- git_status
- git_diff

## Guardrails in v0.1

- Workspace path containment
- Path traversal rejection
- Absolute path rejection
- Destructive command blocking
- git push blocking
- git reset / git clean / git checkout blocking
- Credential path protection for .env and .ssh
- Command timeout
- Maximum agent iterations
- Independent verification before completion

This version is a local development runtime, not a production sandbox. Strong process isolation, persistent state, authentication, distributed execution, and remote execution are intentionally deferred.

## Next layers

The runtime is designed to grow without coupling the UI to execution:

- persistent run/event storage
- checkpoint and rollback
- richer failure classification and recovery
- repository indexing and codebase retrieval
- context management and memory
- Docker or stronger sandboxed execution
- FastAPI service boundary and worker queue
- GitHub, PR, CI/CD and deployment tools
- evaluation and reliability benchmarks
- a dedicated React/TypeScript UI replacing the initial Streamlit surface
