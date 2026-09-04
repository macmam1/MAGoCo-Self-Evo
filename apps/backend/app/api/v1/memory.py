"""
Memory System API Routes
REST API for memory operations
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

from magoco_core.memory import get_memory_store, MemoryEntry, MemoryType, MemoryScope, MemoryQuery

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


class MemoryCreateRequest(BaseModel):
    type: str = "semantic"
    scope: str = "user"
    content: str
    metadata: Dict[str, Any] = {}
    session_id: Optional[str] = None
    experience_type: str = ""
    importance: float = 1.0
    source: str = "user"
    confidence: float = 1.0
    tags: List[str] = []


class MemoryUpdateRequest(BaseModel):
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    importance: Optional[float] = None
    tags: Optional[List[str]] = None
    confidence: Optional[float] = None


class MemorySearchRequest(BaseModel):
    query: str = ""
    query_embedding: Optional[List[float]] = None
    types: Optional[List[str]] = None
    scopes: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    session_id: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    min_importance: float = 0.0
    min_confidence: float = 0.0
    top_k: int = 10
    similarity_threshold: float = 0.7
    use_vector: bool = True
    use_keyword: bool = True
    rerank: bool = True


class EpisodicLogRequest(BaseModel):
    session_id: Optional[str] = None
    limit: int = 100


def get_store():
    return get_memory_store()


@router.get("/stats")
async def get_memory_stats(store=Depends(get_store)):
    """Get memory store statistics"""
    return store.get_stats()


@router.post("/", response_model=Dict[str, Any])
async def create_memory(request: MemoryCreateRequest, store=Depends(get_store)):
    """Create a new memory entry"""
    try:
        memory_type = MemoryType(request.type)
        memory_scope = MemoryScope(request.scope)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid type or scope: {e}")
    
    entry = MemoryEntry(
        type=memory_type,
        scope=memory_scope,
        content=request.content,
        metadata=request.metadata,
        session_id=request.session_id,
        experience_type=request.experience_type,
        importance=request.importance,
        source=request.source,
        confidence=request.confidence,
        tags=set(request.tags),
    )
    
    store.add(entry)
    return {"success": True, "id": entry.id, "entry": entry.to_dict()}


@router.get("/{memory_id}")
async def get_memory(memory_id: str, store=Depends(get_store)):
    """Get a memory entry by ID"""
    entry = store.get(memory_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Memory not found")
    return entry.to_dict()


@router.patch("/{memory_id}")
async def update_memory(memory_id: str, request: MemoryUpdateRequest, store=Depends(get_store)):
    """Update a memory entry"""
    entry = store.get(memory_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    if request.content is not None:
        entry.content = request.content
    if request.metadata is not None:
        entry.metadata = request.metadata
    if request.importance is not None:
        entry.importance = request.importance
    if request.tags is not None:
        entry.tags = set(request.tags)
    if request.confidence is not None:
        entry.confidence = request.confidence
    
    store.update(entry)
    return {"success": True, "entry": entry.to_dict()}


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, hard: bool = False, store=Depends(get_store)):
    """Delete a memory entry"""
    entry = store.get(memory_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Memory not found")
    
    store.delete(memory_id, hard=hard)
    return {"success": True}


@router.post("/search", response_model=List[Dict[str, Any]])
async def search_memory(request: MemorySearchRequest, store=Depends(get_store)):
    """Search memories"""
    try:
        mem_types = [MemoryType(t) for t in request.types] if request.types else None
        mem_scopes = [MemoryScope(s) for s in request.scopes] if request.scopes else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid type or scope: {e}")
    
    query = MemoryQuery(
        query=request.query,
        query_embedding=request.query_embedding,
        types=mem_types,
        scopes=mem_scopes,
        tags=set(request.tags) if request.tags else None,
        session_id=request.session_id,
        min_importance=request.min_importance,
        min_confidence=request.min_confidence,
        top_k=request.top_k,
        similarity_threshold=request.similarity_threshold,
        use_vector=request.use_vector,
        use_keyword=request.use_keyword,
        rerank=request.rerank,
    )
    
    # Parse date range
    if request.date_from:
        query.date_range = (datetime.fromisoformat(request.date_from), None)
    if request.date_to:
        if query.date_range:
            query.date_range = (query.date_range[0], datetime.fromisoformat(request.date_to))
        else:
            query.date_range = (None, datetime.fromisoformat(request.date_to))
    
    results = store.search(query)
    
    return [
        {
            "entry": r.entry.to_dict(),
            "score": r.score,
            "match_type": r.match_type,
            "highlights": r.highlights,
        }
        for r in results
    ]


@router.get("/episodic/log")
async def get_episodic_log(
    session_id: Optional[str] = None,
    limit: int = 100,
    store=Depends(get_store)
):
    """Get episodic memory log"""
    entries = store.get_episodic_log(session_id=session_id, limit=limit)
    return [e.to_dict() for e in entries]


@router.post("/episodic", response_model=Dict[str, Any])
async def add_episodic(request: MemoryCreateRequest, store=Depends(get_store)):
    """Add an episodic memory entry"""
    if request.type != "episodic":
        request.type = "episodic"
    return await create_memory(request, store)


# ============ Knowledge Graph ============

class KGNodeCreate(BaseModel):
    label: str
    type: str
    properties: Dict[str, Any] = {}


class KGEdgeCreate(BaseModel):
    source: str
    target: str
    relation: str
    properties: Dict[str, Any] = {}
    weight: float = 1.0
    confidence: float = 1.0


@router.post("/kg/nodes", response_model=Dict[str, Any])
async def create_kg_node(request: KGNodeCreate, store=Depends(get_store)):
    from magoco_core.memory import KnowledgeGraphNode
    node = KnowledgeGraphNode(
        id=str(uuid.uuid4()),
        label=request.label,
        type=request.type,
        properties=request.properties,
    )
    # Store would need to be extended to handle KG nodes
    return {"success": True, "id": node.id}


@router.get("/kg/nodes/{node_id}")
async def get_kg_node(node_id: str, store=Depends(get_store)):
    node = store.get_kg_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return node.__dict__


@router.get("/kg/nodes/{node_id}/neighbors")
async def get_kg_neighbors(node_id: str, max_depth: int = 1, store=Depends(get_store)):
    edges = store.get_kg_neighbors(node_id, max_depth)
    return [e.__dict__ for e in edges]


@router.post("/kg/edges", response_model=Dict[str, Any])
async def create_kg_edge(request: KGEdgeCreate, store=Depends(get_store)):
    from magoco_core.memory import KnowledgeGraphEdge
    edge = KnowledgeGraphEdge(
        id=str(uuid.uuid4()),
        source=request.source,
        target=request.target,
        relation=request.relation,
        properties=request.properties,
        weight=request.weight,
        confidence=request.confidence,
    )
    store.add_kg_edge(edge)
    return {"success": True, "id": edge.id}


# ============ Document Chunks (RAG) ============

class ChunkCreate(BaseModel):
    document_id: str
    content: str
    metadata: Dict[str, Any] = {}
    embedding: Optional[List[float]] = None
    chunk_index: int = 0
    token_count: int = 0
    start_char: int = 0
    end_char: int = 0


@router.post("/chunks", response_model=Dict[str, Any])
async def add_chunk(request: ChunkCreate, store=Depends(get_store)):
    from magoco_core.memory import DocumentChunk
    chunk = DocumentChunk(
        document_id=request.document_id,
        content=request.content,
        metadata=request.metadata,
        embedding=request.embedding,
        chunk_index=request.chunk_index,
        token_count=request.token_count,
        start_char=request.start_char,
        end_char=request.end_char,
    )
    store.add_document_chunk(chunk)
    return {"success": True, "id": chunk.id}


class ChunkSearchRequest(BaseModel):
    query_embedding: List[float]
    top_k: int = 10


@router.post("/chunks/search", response_model=List[Dict[str, Any]])
async def search_chunks(request: ChunkSearchRequest, store=Depends(get_store)):
    chunks = store.search_chunks(request.query_embedding, request.top_k)
    return chunks


# ============ Utility ============

import uuid

@router.post("/extract", response_model=Dict[str, Any])
async def extract_memories(
    content: str,
    session_id: Optional[str] = None,
    source: str = "extracted",
    store=Depends(get_store)
):
    """Extract memories from text content (placeholder for LLM-based extraction)"""
    # This is a placeholder - in production, use LLM to extract structured memories
    # For now, create a simple episodic entry
    
    entry = MemoryEntry(
        type=MemoryType.EPISODIC,
        scope=MemoryScope.SESSION,
        content=content,
        session_id=session_id,
        experience_type="conversation",
        source=source,
        tags={"extracted", "auto"},
    )
    
    store.add(entry)
    return {"success": True, "id": entry.id, "extracted": 1}