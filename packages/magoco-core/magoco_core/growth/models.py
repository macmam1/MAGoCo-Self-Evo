"""Agent Growth models - patterns, growth events, suggestions."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class GrowthEventType(str, Enum):
    SKILL_CREATED = "skill_created"
    SKILL_IMPROVED = "skill_improved"
    PATTERN_FOUND = "pattern_found"
    WORKFLOW_OPTIMIZED = "workflow_optimized"
    MEMORY_CONSOLIDATED = "memory_consolidated"
    MILESTONE = "milestone"


class SuggestionStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


@dataclass
class UsageEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = "default"
    action: str = ""
    target: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None

    def to_dict(self):
        d = self.__dict__.copy()
        d["timestamp"] = self.timestamp.isoformat()
        return d


@dataclass
class Pattern:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sequence: List[str] = field(default_factory=list)
    count: int = 0
    last_seen: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 0.0
    example_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        d = self.__dict__.copy()
        d["last_seen"] = self.last_seen.isoformat()
        return d


@dataclass
class GrowthSuggestion:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    kind: str = "auto_skill"  # auto_skill | workflow | memory_rule
    title: str = ""
    description: str = ""
    pattern_id: Optional[str] = None
    draft: Dict[str, Any] = field(default_factory=dict)
    status: SuggestionStatus = SuggestionStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        d = self.__dict__.copy()
        d["status"] = self.status.value
        d["created_at"] = self.created_at.isoformat()
        return d


@dataclass
class GrowthEvent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: GrowthEventType = GrowthEventType.MILESTONE
    title: str = ""
    detail: str = ""
    ref_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self):
        d = self.__dict__.copy()
        d["type"] = self.type.value
        d["created_at"] = self.created_at.isoformat()
        return d
