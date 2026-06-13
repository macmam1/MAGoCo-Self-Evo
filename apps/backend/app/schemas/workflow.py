"""Workflow schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class WorkflowCreate(WorkflowBase):
    graph: dict[str, Any] = Field(default_factory=dict)
    workspace_id: uuid.UUID
    is_public: bool = False


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    graph: dict[str, Any] | None = None
    is_active: bool | None = None
    is_public: bool | None = None


class WorkflowResponse(WorkflowBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    graph: dict[str, Any]
    version: int
    is_active: bool
    is_public: bool
    owner_id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
