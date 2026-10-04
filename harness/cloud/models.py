from __future__ import annotations
from pydantic import BaseModel, Field

class WorkspaceCreate(BaseModel):
    repo_full_name: str = Field(min_length=3, pattern=r"^[^/]+/[^/]+$")
    base_branch: str = Field(default="main", min_length=1, max_length=255)

class CloudRunRequest(BaseModel):
    workspace_id: str = Field(min_length=1)
    task: str = Field(min_length=1)
    model: str | None = None
    max_iterations: int = Field(default=20, ge=1, le=100)

class CloudPublishRequest(BaseModel):
    workspace_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=200)
    body: str = ""
    base_branch: str = "main"
