from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    github_id: Mapped[str]=mapped_column(String(64),unique=True,index=True)
    login: Mapped[str]=mapped_column(String(255))
    name: Mapped[str|None]=mapped_column(String(255),nullable=True)
    avatar_url: Mapped[str|None]=mapped_column(String(1000),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class GitHubInstallation(Base):
    __tablename__="github_installations"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    installation_id: Mapped[str]=mapped_column(String(64),unique=True,index=True)
    account_login: Mapped[str]=mapped_column(String(255))
    account_type: Mapped[str]=mapped_column(String(32))
    user_id: Mapped[int|None]=mapped_column(Integer,nullable=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class CloudWorkspace(Base):
    __tablename__="cloud_workspaces"
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    workspace_id: Mapped[str]=mapped_column(String(64),unique=True,index=True)
    user_id: Mapped[int]=mapped_column(Integer,index=True)
    repo_full_name: Mapped[str]=mapped_column(String(500))
    path: Mapped[str]=mapped_column(String(2000))
    branch: Mapped[str]=mapped_column(String(255))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

def database_url()->str:
    url=os.getenv("DATABASE_URL","")
    if not url: raise RuntimeError("DATABASE_URL is required for Forge cloud mode")
    if url.startswith("postgres://"): return "postgresql+psycopg://"+url[len("postgres://"):]
    if url.startswith("postgresql://"): return "postgresql+psycopg://"+url[len("postgresql://"):]
    return url

_engine=None
def engine():
    global _engine
    if _engine is None: _engine=create_engine(database_url(),pool_pre_ping=True)
    return _engine

def init_db()->None: Base.metadata.create_all(engine())

def get_user(github_id:str)->User|None:
    with Session(engine()) as s: return s.query(User).filter_by(github_id=github_id).one_or_none()

def get_user_by_id(user_id:int)->User|None:
    with Session(engine()) as s: return s.get(User,user_id)

def upsert_user(data:dict[str,Any])->User:
    with Session(engine()) as s:
        u=s.query(User).filter_by(github_id=str(data["id"])).one_or_none()
        if u is None: u=User(github_id=str(data["id"]),login=data["login"]); s.add(u)
        u.login=data["login"]; u.name=data.get("name"); u.avatar_url=data.get("avatar_url")
        s.commit(); s.refresh(u); return u

def save_installation(installation_id:str,account_login:str,account_type:str,user_id:int|None=None)->GitHubInstallation:
    with Session(engine()) as s:
        i=s.query(GitHubInstallation).filter_by(installation_id=str(installation_id)).one_or_none()
        if i is None: i=GitHubInstallation(installation_id=str(installation_id),account_login=account_login,account_type=account_type,user_id=user_id); s.add(i)
        else:
            i.account_login=account_login; i.account_type=account_type
            if user_id is not None: i.user_id=user_id
        s.commit(); s.refresh(i); return i

def installations_for_user(user_id:int)->list[GitHubInstallation]:
    with Session(engine()) as s: return s.query(GitHubInstallation).filter_by(user_id=user_id).all()

def save_workspace(workspace_id:str,user_id:int,repo_full_name:str,path:str,branch:str)->CloudWorkspace:
    with Session(engine()) as s:
        w=CloudWorkspace(workspace_id=workspace_id,user_id=user_id,repo_full_name=repo_full_name,path=path,branch=branch)
        s.add(w); s.commit(); s.refresh(w); return w

def get_workspace(workspace_id:str,user_id:int|None=None)->CloudWorkspace|None:
    with Session(engine()) as s:
        q=s.query(CloudWorkspace).filter_by(workspace_id=workspace_id)
        if user_id is not None: q=q.filter_by(user_id=user_id)
        return q.one_or_none()

def delete_workspace(workspace_id:str,user_id:int)->None:
    with Session(engine()) as s:
        w=s.query(CloudWorkspace).filter_by(workspace_id=workspace_id,user_id=user_id).one_or_none()
        if w: s.delete(w); s.commit()
