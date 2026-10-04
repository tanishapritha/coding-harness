from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    github_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    login: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class GitHubInstallation(Base):
    __tablename__ = "github_installations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    installation_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    account_login: Mapped[str] = mapped_column(String(255))
    account_type: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


def database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL is required for Forge cloud mode")
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(), pool_pre_ping=True)
    return _engine


def init_db() -> None:
    Base.metadata.create_all(engine())


def get_user(github_id: str) -> User | None:
    with Session(engine()) as session:
        return session.query(User).filter_by(github_id=github_id).one_or_none()


def upsert_user(data: dict[str, Any]) -> User:
    with Session(engine()) as session:
        user = session.query(User).filter_by(github_id=str(data["id"])).one_or_none()
        if user is None:
            user = User(github_id=str(data["id"]), login=data["login"])
            session.add(user)
        user.login = data["login"]
        user.name = data.get("name")
        user.avatar_url = data.get("avatar_url")
        session.commit()
        session.refresh(user)
        return user


def save_installation(installation_id: str, account_login: str, account_type: str, user_id: int | None = None) -> GitHubInstallation:
    with Session(engine()) as session:
        item = session.query(GitHubInstallation).filter_by(installation_id=str(installation_id)).one_or_none()
        if item is None:
            item = GitHubInstallation(installation_id=str(installation_id), account_login=account_login, account_type=account_type, user_id=user_id)
            session.add(item)
        else:
            item.account_login = account_login
            item.account_type = account_type
            if user_id is not None:
                item.user_id = user_id
        session.commit()
        session.refresh(item)
        return item


def installations_for_user(user_id: int) -> list[GitHubInstallation]:
    with Session(engine()) as session:
        return session.query(GitHubInstallation).filter_by(user_id=user_id).all()
