"""
Memory System Core Models
Data structures for the unified memory system
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid


class MemoryType(str, Enum):
    """Types of memory in the system"""
    WORKING = "working"           # Current session context
    SEMANTIC = "semantic"         # Long-term facts/knowledge (vector)
    EPISODIC = "episodic"         # Past experiences/events (timestamped)
    KNOWLEDGE_GRAPH = "kg"        # Relational knowledge (entities/relations)
    PROCEDURAL = "procedural"     # Skills/how-to knowledge


class MemoryScope(str, Enum):
    """Scope of memory accessibility"""
    SESSION = "session"           # Current conversation only
    USER = "user"                 # User-specific across sessions
    GLOBAL = "global"             # Shared across all users
    AGENT = "agent"               # Agent-specific


@dataclass
class MemoryEntry:
    """Base memory entry"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MemoryType = MemoryType.SEMANTIC
    scope: MemoryScope = MemoryScope.USER
    
    # Content
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Vector embedding (for semantic memory)
    embedding: Optional[List[float]] = None
    embedding_model: str = ""
    
    # Knowledge graph (for KG memory)
    entities: List[str] = field(default_factory=list)
    relations: List[Dict[str, str]] = field(default_factory=list)
    
    # Episodic
    timestamp: datetime = field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    experience_type: str = ""  # "conversation", "task", "observation", etc.
    
    # Scoring
    importance: float = 1.0      # 0-1, higher = more important
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Versioning
    version: int = 1
    parent_id: Optional[str] = None
    is_deleted: bool = False

    # Supersession / conflict model (ADD-default, explicit replace — Mem0 lesson:
    # never blind-cosine-overwrite. New fact links, old stays for audit.)
    supersedes: List[str] = field(default_factory=list)   # ids this entry replaces
    superseded_by: Optional[str] = None                   # id of newer entry that replaces this
    is_current: bool = True                               # False when superseded
    contradiction_of: Optional[str] = None                # linked id if mutually exclusive

    # Decay / reinforcement (Ebbinghaus-inspired)
    decay_score: float = 1.0     # 0-1, multiplied down over time, bumped on access
    next_review_at: Optional[datetime] = None

    # Source tracking
    source: str = "user"         # "user", "agent", "system", "extracted"
    confidence: float = 1.0      # 0-1

    # Tags for organization
    tags: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "scope": self.scope.value,
            "content": self.content,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "embedding_model": self.embedding_model,
            "entities": self.entities,
            "relations": self.relations,
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "experience_type": self.experience_type,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "version": self.version,
            "parent_id": self.parent_id,
            "is_deleted": self.is_deleted,
            "supersedes": self.supersedes,
            "superseded_by": self.superseded_by,
            "is_current": self.is_current,
            "contradiction_of": self.contradiction_of,
            "decay_score": self.decay_score,
            "next_review_at": self.next_review_at.isoformat() if self.next_review_at else None,
            "source": self.source,
            "confidence": self.confidence,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=MemoryType(data.get("type", "semantic")),
            scope=MemoryScope(data.get("scope", "user")),
            content=data.get("content", ""),
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
            embedding_model=data.get("embedding_model", ""),
            entities=data.get("entities", []),
            relations=data.get("relations", []),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
            session_id=data.get("session_id"),
            experience_type=data.get("experience_type", ""),
            importance=data.get("importance", 1.0),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            version=data.get("version", 1),
            parent_id=data.get("parent_id"),
            is_deleted=data.get("is_deleted", False),
            supersedes=data.get("supersedes", []),
            superseded_by=data.get("superseded_by"),
            is_current=data.get("is_current", True),
            contradiction_of=data.get("contradiction_of"),
            decay_score=data.get("decay_score", 1.0),
            next_review_at=datetime.fromisoformat(data["next_review_at"]) if data.get("next_review_at") else None,
            source=data.get("source", "user"),
            confidence=data.get("confidence", 1.0),
            tags=set(data.get("tags", [])),
        )


@dataclass
class CoreBlock:
    """Letta-style always-in-context memory block (persona/human/custom, shared support)."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""              # e.g. persona, human, project_brief
    content: str = ""
    description: str = ""        # when to read/write — guides the agent
    scope: MemoryScope = MemoryScope.USER
    agent_id: Optional[str] = None   # None + shared=True => cross-agent
    shared: bool = False
    char_limit: int = 4000
    version: int = 1
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "label": self.label, "content": self.content,
            "description": self.description, "scope": self.scope.value,
            "agent_id": self.agent_id, "shared": self.shared,
            "char_limit": self.char_limit, "version": self.version,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoreBlock":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            label=data.get("label", ""),
            content=data.get("content", ""),
            description=data.get("description", ""),
            scope=MemoryScope(data.get("scope", "user")),
            agent_id=data.get("agent_id"),
            shared=bool(data.get("shared", False)),
            char_limit=int(data.get("char_limit", 4000)),
            version=int(data.get("version", 1)),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )


@dataclass
class CommunitySummary:
    """GraphRAG-light: bottom-up summary of a KG community."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    level: int = 0               # 0 = leaf community, higher = more abstract
    member_entities: List[str] = field(default_factory=list)
    summary: str = ""
    source_memory_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "level": self.level,
            "member_entities": self.member_entities, "summary": self.summary,
            "source_memory_ids": self.source_memory_ids,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class MemoryQuery:
    """Query for memory retrieval"""
    query: str = ""
    query_embedding: Optional[List[float]] = None
    
    # Filters
    types: Optional[List[MemoryType]] = None
    scopes: Optional[List[MemoryScope]] = None
    tags: Optional[Set[str]] = None
    session_id: Optional[str] = None
    date_range: Optional[tuple[datetime, datetime]] = None
    min_importance: float = 0.0
    min_confidence: float = 0.0
    
    # Retrieval params
    top_k: int = 10
    similarity_threshold: float = 0.7
    include_deleted: bool = False
    current_only: bool = False  # when True, hide superseded (non-current) memories
    
    # Hybrid search
    use_vector: bool = True
    use_keyword: bool = True
    use_kg: bool = False
    
    # Reranking
    rerank: bool = True
    rerank_model: str = "cross-encoder"


@dataclass
class MemorySearchResult:
    """Result from memory search"""
    entry: MemoryEntry
    score: float
    match_type: str  # "vector", "keyword", "kg", "hybrid"
    highlights: List[str] = field(default_factory=list)


@dataclass
class KnowledgeGraphNode:
    """Node in knowledge graph"""
    id: str
    label: str
    type: str  # "entity", "concept", "event"
    properties: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class KnowledgeGraphEdge:
    """Edge in knowledge graph"""
    id: str
    source: str
    target: str
    relation: str
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    confidence: float = 1.0


@dataclass
class DocumentChunk:
    """Chunk of a document for RAG"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str = ""
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    chunk_index: int = 0
    token_count: int = 0
    start_char: int = 0
    end_char: int = 0