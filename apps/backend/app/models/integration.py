"""Integration and Execution History models for audit trails and service connections."""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base, GUID


class IntegrationType(str, PyEnum):
    SLACK = "slack"
    GITHUB = "github"
    GMAIL = "gmail"
    NOTION = "notion"
    HUBSPOT = "hubspot"
    ASANA = "asana"
    LINEAR = "linear"
    JIRA = "jira"
    CUSTOM = "custom"


class ConnectionStatus(str, PyEnum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    EXPIRED = "expired"


class Integration(Base):
    """Connected third-party service (OAuth or API Key based)."""
    __tablename__ = "integrations"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    integration_type: Mapped[IntegrationType] = mapped_column(Enum(IntegrationType), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)  # user-friendly name
    status: Mapped[ConnectionStatus] = mapped_column(Enum(ConnectionStatus), default=ConnectionStatus.DISCONNECTED)

    # Encrypted credentials (API key, OAuth token, etc.)
    credentials: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    # Metadata about the connection (scopes, workspace, channel, etc.)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", backref="integrations")

    def __repr__(self):
        return f"<Integration {self.integration_type.value}:{self.label} ({self.status.value})>"


class WorkflowExecution(Base):
    """Record of a single workflow run — the audit trail."""
    __tablename__ = "workflow_executions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(20), default="running", nullable=False)  # running, completed, failed, cancelled

    # Full execution trace (list of step results)
    execution_log: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    # Input context provided to the workflow
    input_context: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    # Final output
    output: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    duration_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow = relationship("Workflow", backref="executions")

    def __repr__(self):
        return f"<WorkflowExecution {self.id} ({self.status})>"
