from __future__ import annotations

import os
import time
from typing import Any

import httpx
import jwt


GITHUB_API = "https://api.github.com"


def oauth_url(state: str) -> str:
    client_id = os.getenv("GITHUB_CLIENT_ID", "")
    if not client_id:
        raise RuntimeError("GITHUB_CLIENT_ID is required")
    return (
        "https://github.com/login/oauth/authorize"
        f"?client_id={client_id}&state={state}&scope=read:user,user:email"
    )


async def exchange_code(code: str) -> str:
    client_id = os.getenv("GITHUB_CLIENT_ID", "")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data={"client_id": client_id, "client_secret": client_secret, "code": code},
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        return response.json()["access_token"]


async def user(access_token: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{GITHUB_API}/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        return response.json()


def app_jwt() -> str:
    app_id = os.getenv("GITHUB_APP_ID", "")
    private_key = os.getenv("GITHUB_APP_PRIVATE_KEY", "").replace("\\n", "\n")
    if not app_id or not private_key:
        raise RuntimeError("GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY are required")
    now = int(time.time())
    return jwt.encode(
        {"iat": now - 30, "exp": now + 540, "iss": app_id},
        private_key,
        algorithm="RS256",
    )


async def installation_token(installation_id: str) -> str:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        response.raise_for_status()
        return response.json()["token"]


async def repositories(access_token: str) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{GITHUB_API}/user/repos?sort=updated&per_page=100",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/vnd.github+json"},
        )
        response.raise_for_status()
        return response.json()
