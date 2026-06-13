"""Conversation and Message schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.conversation import MessageRole


class ConversationCreate(BaseModel):
    title: str = Field(default="New Chat", max_length=200)
    agent_id: uuid.UUID | None = None
    workspace_id: uuid.UUID


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    agent_id: uuid.UUID | None
    owner_id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class MessageCreate(BaseModel):
    role: MessageRole
    content: str = Field(min_length=1)
    extra: dict[str, Any] = {}


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: MessageRole
    content: str
    extra: dict[str, Any]
    tokens: int | None
    model: str | None
    created_at: datetime
