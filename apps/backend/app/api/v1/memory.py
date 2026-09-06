"""
Memory System API Routes
REST API for memory operations
"""

import json
import logging

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

from magoco_core.memory import get_memory_store, MemoryEntry, MemoryType, MemoryScope, MemoryQuery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["memory"])


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
    current_only: bool = False


class CoreBlockUpsert(BaseModel):
    label: str
    content: str = ""
    description: str = ""
    scope: str = "user"
    agent_id: Optional[str] = None
    shared: bool = False
    char_limit: int = 4000


class CoreBlockAppend(BaseModel):
    content: str


class SupersedeRequest(BaseModel):
    old_id: str
    content: str
    reason: str = ""
    scope: str = "user"


class DecayRequest(BaseModel):
    half_life_days: float = 30.0


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
        current_only=request.current_only,
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


# ============ Enhanced Episodic ============

class ConsolidateRequest(BaseModel):
    session_id: str
    importance_threshold: float = 0.7


class SummarizeRequest(BaseModel):
    session_id: str
    max_length: int = 500


@router.post("/episodic/consolidate", response_model=Dict[str, Any])
async def consolidate_session(request: ConsolidateRequest, store=Depends(get_store)):
    """Consolidate episodic memories from a session to long-term semantic memory"""
    count = store.consolidate_working_to_longterm(
        session_id=request.session_id,
        importance_threshold=request.importance_threshold,
    )
    return {"success": True, "consolidated": count, "session_id": request.session_id}


@router.post("/episodic/summarize", response_model=Dict[str, Any])
async def summarize_session(request: SummarizeRequest, store=Depends(get_store)):
    """Generate a summary of a session"""
    summary = store.summarize_session(request.session_id, request.max_length)
    return {"success": True, "session_id": request.session_id, "summary": summary}


@router.get("/episodic/timeline/{session_id}", response_model=List[Dict[str, Any]])
async def get_session_timeline(session_id: str, store=Depends(get_store)):
    """Get timeline of a session"""
    timeline = store.get_session_timeline(session_id)
    return timeline


@router.get("/memory-graph/{entity}", response_model=Dict[str, Any])
async def get_memory_graph(entity: str, max_depth: int = 2, store=Depends(get_store)):
    """Get memory graph around an entity"""
    graph = store.get_memory_graph(entity, max_depth)
    return graph


@router.post("/episodic/extract-facts", response_model=Dict[str, Any])
async def extract_facts_from_session(
    session_id: str,
    store=Depends(get_store)
):
    """Extract structured facts from a session's conversation"""
    # Get all messages from the session
    entries = store.get_episodic_log(session_id=session_id, limit=1000)
    
    messages = []
    for entry in entries:
        messages.append({
            "content": entry.content,
            "role": entry.metadata.get("role", "unknown"),
        })
    
    facts = store.extract_facts_from_conversation(messages, session_id)
    return {
        "success": True,
        "session_id": session_id,
        "facts_extracted": len(facts),
        "facts": [f.to_dict() for f in facts],
    }


# ===== Memory v2: core blocks / supersede / decay / communities =====

@router.get("/core-blocks", response_model=List[Dict[str, Any]])
async def list_core_blocks(agent_id: Optional[str] = None, include_shared: bool = True,
                           store=Depends(get_store)):
    """List Letta-style core blocks (always-in-context)."""
    from magoco_core.memory import MemoryScope
    blocks = store.list_core_blocks(agent_id, include_shared)
    return [b.to_dict() for b in blocks]


@router.get("/core-blocks/{label}", response_model=Dict[str, Any])
async def get_core_block(label: str, agent_id: Optional[str] = None, store=Depends(get_store)):
    block = store.get_core_block(label, agent_id)
    if not block and agent_id:
        block = store.get_core_block(label, None)
    if not block:
        raise HTTPException(status_code=404, detail="Core block not found")
    return block.to_dict()


@router.put("/core-blocks", response_model=Dict[str, Any])
async def upsert_core_block(req: CoreBlockUpsert, store=Depends(get_store)):
    """Create or replace a core block (white-box editing)."""
    from magoco_core.memory import CoreBlock, MemoryScope
    try:
        scope = MemoryScope(req.scope)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scope")
    block = CoreBlock(label=req.label, content=req.content, description=req.description,
                      scope=scope, agent_id=req.agent_id, shared=req.shared,
                      char_limit=req.char_limit)
    store.upsert_core_block(block)
    saved = store.get_core_block(req.label, req.agent_id)
    return saved.to_dict() if saved else block.to_dict()


@router.post("/core-blocks/{label}/append", response_model=Dict[str, Any])
async def append_core_block(label: str, req: CoreBlockAppend, agent_id: Optional[str] = None,
                            store=Depends(get_store)):
    """Append-safe edit (recommended for shared blocks)."""
    updated = store.append_core_block(label, req.content, agent_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Core block not found")
    return updated.to_dict()


@router.post("/supersede", response_model=Dict[str, Any])
async def supersede_memory(req: SupersedeRequest, store=Depends(get_store)):
    """Explicitly replace an outdated memory. Old stays for audit (is_current=false)."""
    from magoco_core.memory import MemoryEntry, MemoryType, MemoryScope
    old = store.get(req.old_id)
    if not old:
        raise HTTPException(status_code=404, detail="Old memory not found")
    try:
        scope = MemoryScope(req.scope)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid scope")
    new_entry = MemoryEntry(type=old.type, scope=scope, content=req.content,
                            importance=old.importance, source="user",
                            tags=set(old.tags) | {"superseding"},
                            contradiction_of=req.old_id)
    new_id = store.supersede(req.old_id, new_entry, reason=req.reason)
    return {"success": True, "old_id": req.old_id, "new_id": new_id}


@router.post("/decay", response_model=Dict[str, Any])
async def apply_decay(req: DecayRequest, store=Depends(get_store)):
    """Apply Ebbinghaus-style decay to current memories."""
    n = store.apply_decay(req.half_life_days)
    return {"success": True, "decayed": n, "half_life_days": req.half_life_days}


@router.post("/{memory_id}/touch", response_model=Dict[str, Any])
async def touch_memory(memory_id: str, boost: float = 0.05, store=Depends(get_store)):
    """Reinforce a memory on access (bump decay + count)."""
    entry = store.get(memory_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Memory not found")
    store.touch(memory_id, boost)
    return {"success": True, "id": memory_id}


@router.get("/communities", response_model=List[Dict[str, Any]])
async def list_communities(level: Optional[int] = None, limit: int = 50,
                           store=Depends(get_store)):
    """List GraphRAG-light community summaries."""
    return [c.to_dict() for c in store.list_community_summaries(level, limit)]


class GuardianAddRequest(BaseModel):
    session_id: str
    role: str = "user"
    content: str
    persist_snapshot: bool = True


class CompensateRequest(BaseModel):
    model: str = ""
    session_id: Optional[str] = None
    task_hint: str = ""
    top_k: int = 5
    task_needs: List[str] = []
    max_preamble_chars: Optional[int] = None


@router.post("/guardian/add", response_model=Dict[str, Any])
async def guardian_add(req: GuardianAddRequest, store=Depends(get_store)):
    """Add a turn to the Context Guardian (topics + snapshot + summary on overflow)."""
    from magoco_core.memory.guardian import get_guardian
    g = get_guardian(req.session_id)
    events = await g.add(req.role, req.content)
    snap_id = None
    if events.get("snapshot") and req.persist_snapshot:
        snap = events["snapshot"]
        snap_id = store.save_snapshot(req.session_id, snap["window_len"] and g.window or [],
                                      g.rolling_summary,
                                      [t for t in g.state()["topics"]],
                                      note=snap.get("note", ""))
    return {"topic": events["topic"], "summarized": events["summarized"],
            "snapshot_id": snap_id, "state": g.state()}


@router.get("/guardian/{session_id}/state", response_model=Dict[str, Any])
async def guardian_state(session_id: str):
    from magoco_core.memory.guardian import get_guardian
    return get_guardian(session_id).state()


@router.get("/guardian/{session_id}/scoped", response_model=List[Dict[str, Any]])
async def guardian_scoped(session_id: str, max_items: int = 12):
    """Active-topic-scoped context (anti-interference) + summary header."""
    from magoco_core.memory.guardian import get_guardian
    return get_guardian(session_id).scoped_context(max_items)


@router.get("/snapshots/{session_id}", response_model=List[Dict[str, Any]])
async def list_snapshots(session_id: str, limit: int = 20, store=Depends(get_store)):
    return store.list_snapshots(session_id, limit)


@router.post("/compensate", response_model=Dict[str, Any])
async def compensate_context(req: CompensateRequest, store=Depends(get_store)):
    """Build model-strength-aware memory preamble (covers weak/medium models)."""
    from magoco_core.memory.compensation import build_augmented_context
    from magoco_core.memory.models import MemoryQuery, MemoryScope
    blocks = [{"label": b.label, "content": b.content}
              for b in store.list_core_blocks(None, include_shared=True)[:10]]
    facts: List[str] = []
    if req.session_id:
        q = MemoryQuery(query=req.task_hint or "key facts decisions",
                        scopes=[MemoryScope.USER, MemoryScope.GLOBAL],
                        top_k=req.top_k, current_only=True,
                        use_vector=False, use_keyword=True)
        facts = [r.entry.content for r in store.search(q)]
    rolling = ""
    try:
        from magoco_core.memory.guardian import get_guardian
        rolling = get_guardian(req.session_id).rolling_summary if req.session_id else ""
    except Exception:
        pass
    return build_augmented_context(req.model, core_blocks=blocks,
                                   distilled_facts=facts,
                                   rolling_summary=rolling,
                                   task_hint=req.task_hint,
                                   task_needs=req.task_needs,
                                   max_preamble_chars=req.max_preamble_chars)


@router.get("/episodic/sessions", response_model=List[Dict[str, Any]])
async def list_sessions(limit: int = 50, store=Depends(get_store)):
    """List all sessions with episodic memories"""
    # Get unique session IDs from episodic log
    sessions = {}
    try:
        with open(store.episodic_log, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                if data.get("type") == "episodic":
                    sid = data.get("session_id")
                    if sid:
                        if sid not in sessions:
                            sessions[sid] = {
                                "session_id": sid,
                                "first_seen": data.get("timestamp"),
                                "last_seen": data.get("timestamp"),
                                "message_count": 0,
                            }
                        sessions[sid]["message_count"] += 1
                        if data.get("timestamp") > sessions[sid]["last_seen"]:
                            sessions[sid]["last_seen"] = data.get("timestamp")
    except Exception as e:
        logger.error(f"Failed to read sessions: {e}")
    
    # Sort by last_seen descending
    session_list = sorted(sessions.values(), key=lambda x: x["last_seen"], reverse=True)
    return session_list[:limit]