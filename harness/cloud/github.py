from __future__ import annotations
import os, time
from typing import Any
import httpx, jwt

GITHUB_API="https://api.github.com"

def _headers(token:str)->dict[str,str]:
    return {"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2026-03-10"}

def oauth_url(state:str)->str:
    client_id=os.getenv("GITHUB_CLIENT_ID","")
    if not client_id: raise RuntimeError("GITHUB_CLIENT_ID is required")
    return f"https://github.com/login/oauth/authorize?client_id={client_id}&state={state}&scope=read:user,user:email"

async def exchange_code(code:str)->str:
    async with httpx.AsyncClient(timeout=20) as c:
        r=await c.post("https://github.com/login/oauth/access_token",data={"client_id":os.getenv("GITHUB_CLIENT_ID",""),"client_secret":os.getenv("GITHUB_CLIENT_SECRET",""),"code":code},headers={"Accept":"application/json"})
        r.raise_for_status(); return r.json()["access_token"]

async def user(access_token:str)->dict[str,Any]:
    async with httpx.AsyncClient(timeout=20) as c:
        r=await c.get(f"{GITHUB_API}/user",headers=_headers(access_token)); r.raise_for_status(); return r.json()

def app_jwt()->str:
    app_id=os.getenv("GITHUB_APP_ID",""); key=os.getenv("GITHUB_APP_PRIVATE_KEY","").replace("\\n","\n")
    if not app_id or not key: raise RuntimeError("GITHUB_APP_ID and GITHUB_APP_PRIVATE_KEY are required")
    now=int(time.time())
    return jwt.encode({"iat":now-30,"exp":now+540,"iss":app_id},key,algorithm="RS256")

async def installation_token(installation_id:str)->str:
    async with httpx.AsyncClient(timeout=20) as c:
        r=await c.post(f"{GITHUB_API}/app/installations/{installation_id}/access_tokens",headers={"Authorization":f"Bearer {app_jwt()}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2026-03-10"})
        r.raise_for_status(); return r.json()["token"]

async def repositories(access_token:str)->list[dict[str,Any]]:
    async with httpx.AsyncClient(timeout=20) as c:
        r=await c.get(f"{GITHUB_API}/user/repos?sort=updated&per_page=100",headers=_headers(access_token)); r.raise_for_status(); return r.json()

async def installation_repositories(installation_id:str)->list[dict[str,Any]]:
    token=await installation_token(installation_id)
    async with httpx.AsyncClient(timeout=20) as c:
        r=await c.get(f"{GITHUB_API}/installation/repositories?per_page=100",headers=_headers(token)); r.raise_for_status(); return r.json().get("repositories",[])

async def installation_for_repo(installation_ids:list[str],repo_full_name:str)->tuple[str,str]:
    target=repo_full_name.lower()
    for iid in installation_ids:
        for repo in await installation_repositories(iid):
            if repo.get("full_name","").lower()==target:
                return iid, repo.get("clone_url") or f"https://github.com/{repo_full_name}.git"
    raise PermissionError(f"GitHub App is not installed for {repo_full_name}")

async def create_pull_request(token:str,repo_full_name:str,title:str,body:str,head:str,base:str)->dict[str,Any]:
    async with httpx.AsyncClient(timeout=20) as c:
        r=await c.post(f"{GITHUB_API}/repos/{repo_full_name}/pulls",json={"title":title,"body":body,"head":head,"base":base,"draft":False},headers=_headers(token))
        r.raise_for_status(); return r.json()
