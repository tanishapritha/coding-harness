from __future__ import annotations

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import Cookie, FastAPI, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from itsdangerous import BadSignature, URLSafeSerializer
from pydantic import BaseModel, Field

from .cloud.db import get_user_by_id, init_db, installations_for_user, save_installation, upsert_user
from .cloud.github import exchange_code, installation_token, oauth_url, repositories as github_repositories, user as github_user

from .agent import AgentRuntime
from .config import Settings
from .memory.sqlite import SQLiteMemory
from .trajectories.store import TrajectoryStore
from .workspace import Workspace

app = FastAPI(title="Forge API", version="1.1.0")

def _session_serializer() -> URLSafeSerializer:
    import os
    secret = os.getenv("FORGE_SESSION_SECRET")
    if not secret:
        raise RuntimeError("FORGE_SESSION_SECRET is required for cloud auth")
    return URLSafeSerializer(secret, salt="forge-session")

@app.on_event("startup")
def _startup() -> None:
    import os
    if os.getenv("DATABASE_URL"):
        init_db()

def _current_user(forge_session: str | None):
    if not forge_session:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = _session_serializer().loads(forge_session)
    except BadSignature as exc:
        raise HTTPException(401, "Invalid session") from exc
    user = get_user_by_id(int(payload["user_id"]))
    if user is None:
        raise HTTPException(401, "User not found")
    return user
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=4)
active: dict[str, AgentRuntime] = {}
lock = threading.Lock()
store = TrajectoryStore()


class RunRequest(BaseModel):
    workspace: str
    task: str = Field(min_length=1)
    model: str | None = None
    max_iterations: int = Field(default=20, ge=1, le=100)
    command_timeout: int = Field(default=30, ge=5, le=300)


def _state_path(run_id: str) -> Path:
    return store.path(run_id) / "state.json"


def _load_state(run_id: str) -> dict[str, Any]:
    path = _state_path(run_id)
    if not path.exists():
        raise HTTPException(404, "Run not found")
    return json.loads(path.read_text(encoding="utf-8"))


def _run(runtime: AgentRuntime, task: str) -> None:
    try:
        runtime.run(task)
    finally:
        with lock:
            active.pop(runtime.run_id, None)



@app.get("/auth/github/login")
def github_login() -> dict[str, str]:
    import secrets
    state = _session_serializer().dumps({"oauth_state": secrets.token_urlsafe(24)})
    return {"url": oauth_url(state), "state": state}

@app.get("/auth/github/callback")
async def github_callback(code: str, state: str, response: Response):
    try:
        _session_serializer().loads(state)
    except BadSignature as exc:
        raise HTTPException(400, "Invalid OAuth state") from exc
    token = await exchange_code(code)
    profile = await github_user(token)
    user = upsert_user(profile)
    session = _session_serializer().dumps({"user_id": user.id})
    response.set_cookie("forge_session", session, httponly=True, secure=False, samesite="lax", max_age=60 * 60 * 24 * 30)
    import os
    frontend = os.getenv("FORGE_FRONTEND_URL", "http://localhost:3000")
    redirect = RedirectResponse(url=frontend, status_code=302)
    redirect.set_cookie("forge_session", session, httponly=True, secure=False, samesite="lax", max_age=60 * 60 * 24 * 30)
    return redirect

@app.get("/auth/me")
def auth_me(forge_session: str | None = Cookie(default=None)) -> dict[str, Any]:
    user = _current_user(forge_session)
    return {"id": user.id, "login": user.login, "name": user.name, "avatar_url": user.avatar_url}

@app.get("/github/install")
def github_install(forge_session: str | None = Cookie(default=None)) -> dict[str, str]:
    _current_user(forge_session)
    import os
    slug = os.getenv("GITHUB_APP_SLUG")
    if not slug:
        raise HTTPException(500, "GITHUB_APP_SLUG is required")
    return {"url": f"https://github.com/apps/{slug}/installations/new"}

@app.get("/github/installation/callback")
def github_installation_callback(installation_id: str, setup_action: str = "install", forge_session: str | None = Cookie(default=None)) -> dict[str, Any]:
    user = _current_user(forge_session)
    save_installation(installation_id, "unknown", "unknown", user.id)
    return {"status": "connected", "installation_id": installation_id, "setup_action": setup_action}

@app.get("/github/repositories")
async def github_repos(forge_session: str | None = Cookie(default=None)) -> list[dict[str, Any]]:
    user = _current_user(forge_session)
    installations = installations_for_user(user.id)
    repos: list[dict[str, Any]] = []
    for item in installations:
        token = await installation_token(item.installation_id)
        repos.extend(await github_repositories(token))
    return repos

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "forge"}


@app.post("/runs", status_code=202)
def create_run(request: RunRequest) -> dict[str, Any]:
    ws = Workspace(request.workspace)
    base = Settings()
    settings = Settings(
        model=request.model or base.model,
        api_key=base.api_key,
        base_url=base.base_url,
        max_iterations=request.max_iterations,
        command_timeout=request.command_timeout,
    )
    runtime = AgentRuntime(str(ws.root), settings)
    with lock:
        active[runtime.run_id] = runtime
    executor.submit(_run, runtime, request.task)
    return {"run_id": runtime.run_id, "status": "CREATED", "workspace": str(ws.root)}


@app.get("/runs")
def list_runs(limit: int = 30) -> list[dict[str, Any]]:
    runs = []
    for path in sorted(
        [p for p in store.base.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]:
        state = path / "state.json"
        if state.exists():
            try:
                runs.append(json.loads(state.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
    return runs


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    return _load_state(run_id)


@app.post("/runs/{run_id}/stop")
def stop_run(run_id: str) -> dict[str, Any]:
    with lock:
        runtime = active.get(run_id)
    if runtime is None:
        state = _load_state(run_id)
        return {"run_id": run_id, "status": state["status"]}
    runtime.request_stop()
    return {"run_id": run_id, "status": "STOP_REQUESTED"}


@app.get("/runs/{run_id}/events")
def get_events(run_id: str) -> list[dict[str, Any]]:
    path = store.path(run_id) / "events.jsonl"
    if not path.exists():
        _load_state(run_id)
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


@app.get("/runs/{run_id}/stream")
async def stream_events(run_id: str):
    path = store.path(run_id) / "events.jsonl"
    if not path.exists() and not _state_path(run_id).exists():
        raise HTTPException(404, "Run not found")

    async def generator():
        position = 0
        while True:
            if path.exists():
                text = path.read_text(encoding="utf-8")
                chunk = text[position:]
                position = len(text)
                for line in chunk.splitlines():
                    if line:
                        yield f"data: {line}\\n\\n"
            state = _load_state(run_id)
            if state["status"] in {"COMPLETED", "FAILED", "STOPPED"}:
                yield "event: done\\ndata: {}\\n\\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(generator(), media_type="text/event-stream")


@app.get("/repositories")
def repository_info(path: str) -> dict[str, Any]:
    ws = Workspace(path)
    files = ws.list_files()
    return {
        "path": str(ws.root),
        "name": ws.root.name,
        "is_git_repo": ws.is_git_repo,
        "branch": ws.git("branch", "--show-current") if ws.is_git_repo else None,
        "status": ws.git("status", "--short") if ws.is_git_repo else "",
        "files": files,
    }


@app.get("/repositories/memory")
def repository_memory(path: str, query: str = "", limit: int = 50) -> list[dict[str, Any]]:
    ws = Workspace(path)
    memory = SQLiteMemory("~/.forge/forge.db", str(ws.root).lower())
    return memory.search(query, limit) if query else memory.all()[:limit]


@app.get("/runs/{run_id}/diff")
def run_diff(run_id: str) -> dict[str, Any]:
    state = _load_state(run_id)
    ws = Workspace(state["workspace"])
    return {"diff": ws.git("diff", "--", ".") if ws.is_git_repo else ""}


@app.get("/runs/{run_id}/context")
def run_context(run_id: str) -> dict[str, Any]:
    path = store.path(run_id) / "context.json"
    if not path.exists():
        _load_state(run_id)
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
