from __future__ import annotations

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    repo_url: str = Field(min_length=1)
    base_branch: str = "main"


class CloudRunRequest(BaseModel):
    workspace_id: str = Field(min_length=1)
    task: str = Field(min_length=1)
    model: str | None = None
    max_iterations: int = Field(default=20, ge=1, le=100)
