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
            source=data.get("source", "user"),
            confidence=data.get("confidence", 1.0),
            tags=set(data.get("tags", [])),
        )


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