"""Agent schemas."""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.agent import LLMProvider


class AgentBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    role: str = Field(min_length=1, max_length=100)
    description: str | None = None
    system_prompt: str = ""


class AgentCreate(AgentBase):
    llm_provider: LLMProvider = LLMProvider.OPENAI
    model_name: str = "gpt-4o-mini"
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=128000)
    tools: list[str] = []
    config: dict[str, Any] = {}
    workspace_id: uuid.UUID
    is_public: bool = False


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    system_prompt: str | None = None
    llm_provider: LLMProvider | None = None
    model_name: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, ge=1, le=128000)
    tools: list[str] | None = None
    config: dict[str, Any] | None = None
    is_active: bool | None = None
    is_public: bool | None = None


class AgentResponse(AgentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    llm_provider: LLMProvider
    model_name: str
    temperature: float
    max_tokens: int
    tools: list[str]
    config: dict[str, Any]
    is_active: bool
    is_public: bool
    owner_id: uuid.UUID
    workspace_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
