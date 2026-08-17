"""Workflow and Task models - for defining and running automated pipelines."""

import uuid
import json
from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any, List, Dict

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, GUID


if TYPE_CHECKING:
    from app.models.user import User
    from app.models.agent import Agent


class TaskStatus(str, PyEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Workflow(Base):
    """Represents a saved workflow pipeline."""

    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="workflows", lazy="joined")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="workflow", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Workflow {self.name}>"


class Task(Base):
    """Represents a single task within a workflow."""

    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name: Mapped[str | None] = mapped_column(String(100), ForeignKey("agents.name", ondelete="SET NULL"), nullable=True, index=True) # If task is assigned to a specific agent
    tool_name: Mapped[str | None] = mapped_column(String(100), ForeignKey("tools.name", ondelete="SET NULL"), nullable=True, index=True) # If task is to call a specific tool

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus, name="task_status"), default=TaskStatus.PENDING, nullable=False, index=True)
    params: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    dependencies: Mapped[List[uuid.UUID]] = mapped_column(JSON, default=list, nullable=False) # List of task IDs this task depends on

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task {self.name} ({self.status.value})>"
