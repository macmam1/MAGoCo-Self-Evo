"""
Memory Store - Unified storage layer for all memory types
Uses LanceDB for vectors, SQLite for relational, JSONL for episodic
"""

import os
import json
import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Iterator
from datetime import datetime
import uuid

try:
    import lancedb
    LANCEDB_AVAILABLE = True
except ImportError:
    LANCEDB_AVAILABLE = False
    lancedb = None

from .models import (
    MemoryEntry, MemoryType, MemoryScope, MemoryQuery,
    MemorySearchResult, KnowledgeGraphNode,
    KnowledgeGraphEdge, DocumentChunk, CoreBlock, CommunitySummary
)

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    Unified memory store with multiple backends:
    - LanceDB: Vector embeddings for semantic search
    - SQLite: Relational data (metadata, KG, episodic index)
    - JSONL: Append-only episodic log
    """
    
    def __init__(
        self,
        data_dir: str = "./data/memory",
        embedding_dim: int = 1536,
        embedding_model: str = "text-embedding-3-small",
    ):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.embedding_dim = embedding_dim
        self.embedding_model = embedding_model
        
        # Initialize backends
        self._init_sqlite()
        self._init_lancedb()
        self._init_episodic_log()
        
        logger.info(f"MemoryStore initialized at {self.data_dir}")
    
    def _init_sqlite(self):
        """Initialize SQLite for relational data"""
        self.db_path = self.data_dir / "memory.db"
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        # Memory entries table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                scope TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                embedding BLOB,
                embedding_model TEXT DEFAULT '',
                entities TEXT DEFAULT '[]',
                relations TEXT DEFAULT '[]',
                timestamp TEXT NOT NULL,
                session_id TEXT,
                experience_type TEXT DEFAULT '',
                importance REAL DEFAULT 1.0,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                version INTEGER DEFAULT 1,
                parent_id TEXT,
                is_deleted INTEGER DEFAULT 0,
                source TEXT DEFAULT 'user',
                confidence REAL DEFAULT 1.0,
                tags TEXT DEFAULT '[]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Knowledge graph nodes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kg_nodes (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                type TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                embedding BLOB
            )
        """)
        
        # Knowledge graph edges
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kg_edges (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                relation TEXT NOT NULL,
                properties TEXT DEFAULT '{}',
                weight REAL DEFAULT 1.0,
                confidence REAL DEFAULT 1.0
            )
        """)
        
        # Document chunks for RAG
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                embedding BLOB,
                chunk_index INTEGER DEFAULT 0,
                token_count INTEGER DEFAULT 0,
                start_char INTEGER DEFAULT 0,
                end_char INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # --- v2 migrations: supersession / decay (backward compatible) ---
        for col, ddl in [
            ("supersedes", "TEXT DEFAULT '[]'"),
            ("superseded_by", "TEXT"),
            ("is_current", "INTEGER DEFAULT 1"),
            ("contradiction_of", "TEXT"),
            ("decay_score", "REAL DEFAULT 1.0"),
            ("next_review_at", "TEXT"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE memories ADD COLUMN {col} {ddl}")
            except Exception:
                pass  # column already exists

        # Core memory blocks (Letta-style, always-in-context)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS core_blocks (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                content TEXT DEFAULT '',
                description TEXT DEFAULT '',
                scope TEXT DEFAULT 'user',
                agent_id TEXT,
                shared INTEGER DEFAULT 0,
                char_limit INTEGER DEFAULT 4000,
                version INTEGER DEFAULT 1,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_core_blocks_label ON core_blocks(label)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_core_blocks_agent ON core_blocks(agent_id)")

        # Community summaries (GraphRAG-light, hierarchical)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS community_summaries (
                id TEXT PRIMARY KEY,
                level INTEGER DEFAULT 0,
                member_entities TEXT DEFAULT '[]',
                summary TEXT DEFAULT '',
                source_memory_ids TEXT DEFAULT '[]',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Context versions (Guardian snapshots — no history loss)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_snapshots (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                window_json TEXT DEFAULT '[]',
                rolling_summary TEXT DEFAULT '',
                topics_json TEXT DEFAULT '[]',
                note TEXT DEFAULT ''
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_session ON context_snapshots(session_id)")

        # Deferred tasks (Capability Gate queue — reviewable, never silent)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS deferred_tasks (
                id TEXT PRIMARY KEY,
                session_id TEXT DEFAULT '',
                model TEXT DEFAULT '',
                task_text TEXT DEFAULT '',
                task_needs TEXT DEFAULT '[]',
                reason TEXT DEFAULT '',
                complexity INTEGER DEFAULT 0,
                status TEXT DEFAULT 'queued',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                resolved_at TEXT,
                resolved_model TEXT DEFAULT ''
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_deferred_status ON deferred_tasks(status)")

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_scope ON memories(scope)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories(tags)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_current ON memories(is_current)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_nodes_label ON kg_nodes(label)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_edges_source ON kg_edges(source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_kg_edges_target ON kg_edges(target)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id)")
        
        self.conn.commit()
    
    def _init_lancedb(self):
        """Initialize LanceDB for vector storage"""
        if not LANCEDB_AVAILABLE:
            logger.warning("LanceDB not available, vector search disabled")
            self.lancedb = None
            self.vector_table = None
            return
        
        try:
            self.lancedb = lancedb.connect(str(self.data_dir / "lancedb"))
            
            # Create vector table if not exists
            if "memory_vectors" not in self.lancedb.table_names():
                import pyarrow as pa
                schema = pa.schema([
                    pa.field("id", pa.string()),
                    pa.field("vector", pa.list_(pa.float32(), self.embedding_dim)),
                    pa.field("memory_id", pa.string()),
                    pa.field("type", pa.string()),
                    pa.field("scope", pa.string()),
                    pa.field("content", pa.string()),
                    pa.field("metadata", pa.string()),
                    pa.field("timestamp", pa.string()),
                ])
                self.vector_table = self.lancedb.create_table("memory_vectors", schema=schema)
                logger.info("Created LanceDB vector table")
            else:
                self.vector_table = self.lancedb.open_table("memory_vectors")
                logger.info("Opened existing LanceDB vector table")
                
        except Exception as e:
            logger.error(f"Failed to initialize LanceDB: {e}")
            self.lancedb = None
            self.vector_table = None
    
    def _init_episodic_log(self):
        """Initialize episodic JSONL log"""
        self.episodic_log = self.data_dir / "episodic.jsonl"
        if not self.episodic_log.exists():
            self.episodic_log.touch()
    
    # ============ Connection Management ============
    
    @contextmanager
    def _get_cursor(self):
        """Context manager for database cursor"""
        cursor = self.conn.cursor()
        try:
            yield cursor
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
    
    # ============ Memory CRUD ============
    
    def add(self, entry: MemoryEntry) -> str:
        """Add a new memory entry (ADD-default: never auto-overwrites)."""
        with self._get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO memories (
                    id, type, scope, content, metadata, embedding, embedding_model,
                    entities, relations, timestamp, session_id, experience_type,
                    importance, access_count, last_accessed, version, parent_id,
                    is_deleted, source, confidence, tags,
                    supersedes, superseded_by, is_current, contradiction_of,
                    decay_score, next_review_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id, entry.type.value, entry.scope.value, entry.content,
                json.dumps(entry.metadata),
                entry.embedding if entry.embedding else None,
                entry.embedding_model,
                json.dumps(entry.entities),
                json.dumps(entry.relations),
                entry.timestamp.isoformat(),
                entry.session_id,
                entry.experience_type,
                entry.importance,
                entry.access_count,
                entry.last_accessed.isoformat() if entry.last_accessed else None,
                entry.version,
                entry.parent_id,
                int(entry.is_deleted),
                entry.source,
                entry.confidence,
                json.dumps(list(entry.tags)),
                json.dumps(entry.supersedes),
                entry.superseded_by,
                int(entry.is_current),
                entry.contradiction_of,
                entry.decay_score,
                entry.next_review_at.isoformat() if entry.next_review_at else None,
            ))
        
        # Add to vector store if embedding exists
        if entry.embedding and self.vector_table:
            try:
                self.vector_table.add([{
                    "id": entry.id,
                    "vector": entry.embedding,
                    "memory_id": entry.id,
                    "type": entry.type.value,
                    "scope": entry.scope.value,
                    "content": entry.content[:1000],
                    "metadata": json.dumps(entry.metadata),
                    "timestamp": entry.timestamp.isoformat(),
                }])
            except Exception as e:
                logger.warning(f"Failed to add to vector store: {e}")
        
        # Append to episodic log if episodic
        if entry.type == MemoryType.EPISODIC:
            self._append_episodic(entry)
        
        return entry.id
    
    def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Get a memory entry by ID"""
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()
            if row:
                return self._row_to_entry(row)
        return None
    
    def update(self, entry: MemoryEntry) -> bool:
        """Update an existing memory entry"""
        entry.version += 1

        with self._get_cursor() as cursor:
            cursor.execute("""
                UPDATE memories SET
                    type=?, scope=?, content=?, metadata=?, embedding=?,
                    embedding_model=?, entities=?, relations=?, timestamp=?,
                    session_id=?, experience_type=?, importance=?, access_count=?,
                    last_accessed=?, version=?, parent_id=?, is_deleted=?,
                    source=?, confidence=?, tags=?,
                    supersedes=?, superseded_by=?, is_current=?, contradiction_of=?,
                    decay_score=?, next_review_at=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (
                entry.type.value, entry.scope.value, entry.content,
                json.dumps(entry.metadata),
                entry.embedding if entry.embedding else None,
                entry.embedding_model,
                json.dumps(entry.entities),
                json.dumps(entry.relations),
                entry.timestamp.isoformat(),
                entry.session_id,
                entry.experience_type,
                entry.importance,
                entry.access_count,
                entry.last_accessed.isoformat() if entry.last_accessed else None,
                entry.version,
                entry.parent_id,
                int(entry.is_deleted),
                entry.source,
                entry.confidence,
                json.dumps(list(entry.tags)),
                json.dumps(entry.supersedes),
                entry.superseded_by,
                int(entry.is_current),
                entry.contradiction_of,
                entry.decay_score,
                entry.next_review_at.isoformat() if entry.next_review_at else None,
                entry.id,
            ))
        
        # Update vector store
        if entry.embedding and self.vector_table:
            try:
                self.vector_table.delete(f"id = '{entry.id}'")
                self.vector_table.add([{
                    "id": entry.id,
                    "vector": entry.embedding,
                    "memory_id": entry.id,
                    "type": entry.type.value,
                    "scope": entry.scope.value,
                    "content": entry.content[:1000],
                    "metadata": json.dumps(entry.metadata),
                    "timestamp": entry.timestamp.isoformat(),
                }])
            except Exception as e:
                logger.warning(f"Failed to update vector store: {e}")
        
        return True
    
    def delete(self, memory_id: str, hard: bool = False) -> bool:
        """Delete a memory entry (soft by default)"""
        if hard:
            with self._get_cursor() as cursor:
                cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            if self.vector_table:
                try:
                    self.vector_table.delete(f"id = '{memory_id}'")
                except Exception:
                    pass
        else:
            with self._get_cursor() as cursor:
                cursor.execute(
                    "UPDATE memories SET is_deleted = 1 WHERE id = ?", (memory_id,)
                )
        return True
    
    # ============ Search ============
    
    def search(self, query: MemoryQuery) -> List[MemorySearchResult]:
        """Search memories using hybrid approach"""
        results = []
        
        # Vector search
        if query.use_vector and query.query_embedding and self.vector_table:
            vector_results = self._vector_search(query)
            results.extend(vector_results)
        
        # Keyword search (SQLite FTS would be better, using LIKE for now)
        if query.use_keyword:
            keyword_results = self._keyword_search(query)
            results.extend(keyword_results)
        
        # Deduplicate and sort
        seen = set()
        unique_results = []
        for r in results:
            if r.entry.id not in seen:
                seen.add(r.entry.id)
                unique_results.append(r)
        
        # Sort by score
        unique_results.sort(key=lambda x: x.score, reverse=True)
        
        # Rerank if enabled
        if query.rerank and len(unique_results) > 1:
            unique_results = self._rerank_results(query, unique_results)
        
        return unique_results[:query.top_k]
    
    def _vector_search(self, query: MemoryQuery) -> List[MemorySearchResult]:
        """Search using vector similarity"""
        if not self.vector_table or not query.query_embedding:
            return []
        
        try:
            results = self.vector_table.search(query.query_embedding).limit(query.top_k * 3).to_list()
            
            results_list = []
            for row in results:
                # Get full entry from SQLite
                entry = self.get(row["memory_id"])
                if entry and self._matches_filters(entry, query):
                    score = 1.0 - row["_distance"]  # Convert distance to similarity
                    if score >= query.similarity_threshold:
                        results_list.append(MemorySearchResult(
                            entry=entry,
                            score=score,
                            match_type="vector",
                        ))
            return results_list
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def _keyword_search(self, query: MemoryQuery) -> List[MemorySearchResult]:
        """Search using keyword matching"""
        if not query.query:
            return []
        
        keywords = query.query.lower().split()
        conditions = []
        params = []
        
        for kw in keywords:
            conditions.append("(LOWER(content) LIKE ? OR LOWER(metadata) LIKE ?)")
            params.extend([f"%{kw}%", f"%{kw}%"])
        
        where_clause = " AND ".join(conditions)
        
        filter_conditions = []
        if query.types:
            type_placeholders = ",".join(["?" for _ in query.types])
            filter_conditions.append(f"type IN ({type_placeholders})")
            params.extend([t.value for t in query.types])
        
        if query.scopes:
            scope_placeholders = ",".join(["?" for _ in query.scopes])
            filter_conditions.append(f"scope IN ({scope_placeholders})")
            params.extend([s.value for s in query.scopes])
        
        if query.session_id:
            filter_conditions.append("session_id = ?")
            params.append(query.session_id)
        
        if not query.include_deleted:
            filter_conditions.append("is_deleted = 0")
        if query.current_only:
            filter_conditions.append("is_current = 1")
        
        if filter_conditions:
            where_clause = f"WHERE {where_clause} AND " + " AND ".join(filter_conditions)
        else:
            where_clause = f"WHERE {where_clause}"
        
        sql = f"""
            SELECT * FROM memories 
            {where_clause}
            ORDER BY importance DESC, timestamp DESC
            LIMIT ?
        """
        params.append(50)
        
        with self._get_cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                entry = self._row_to_entry(row)
                # Simple keyword scoring
                score = self._keyword_score(entry, query.query)
                if score > 0:
                    results.append(MemorySearchResult(
                        entry=entry,
                        score=score,
                        match_type="keyword",
                    ))
            return results
    
    def _matches_filters(self, entry: MemoryEntry, query: MemoryQuery) -> bool:
        """Check if entry matches query filters"""
        if query.current_only and not entry.is_current:
            return False
        if query.types and entry.type not in query.types:
            return False
        if query.scopes and entry.scope not in query.scopes:
            return False
        if query.session_id and entry.session_id != query.session_id:
            return False
        if entry.importance < query.min_importance:
            return False
        if entry.confidence < query.min_confidence:
            return False
        if query.tags and not query.tags.intersection(entry.tags):
            return False
        if query.date_range:
            if entry.timestamp < query.date_range[0] or entry.timestamp > query.date_range[1]:
                return False
        return True
    
    def _keyword_score(self, entry: MemoryEntry, query: str) -> float:
        """Simple keyword scoring"""
        content_lower = entry.content.lower()
        query_lower = query.lower()
        keywords = query_lower.split()
        
        matches = sum(1 for kw in keywords if kw in content_lower)
        if not keywords:
            return 0.0
        
        return matches / len(keywords)
    
    def _rerank_results(self, query: MemoryQuery, results: List[MemorySearchResult]) -> List[MemorySearchResult]:
        """Rerank results (placeholder for cross-encoder)"""
        # In production, use cross-encoder model
        # For now, just sort by score * importance
        for r in results:
            r.score = r.score * (0.7 + 0.3 * r.entry.importance)
        results.sort(key=lambda x: x.score, reverse=True)
        return results
    
    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        """Convert SQLite row to MemoryEntry (tolerant to old DBs)."""
        keys = set(row.keys())
        def _j(k, default):
            try:
                return json.loads(row[k] or json.dumps(default))
            except Exception:
                return default
        return MemoryEntry(
            id=row["id"],
            type=MemoryType(row["type"]),
            scope=MemoryScope(row["scope"]),
            content=row["content"],
            metadata=json.loads(row["metadata"] or "{}"),
            embedding=list(row["embedding"]) if row["embedding"] else None,
            embedding_model=row["embedding_model"] or "",
            entities=json.loads(row["entities"] or "[]"),
            relations=json.loads(row["relations"] or "[]"),
            timestamp=datetime.fromisoformat(row["timestamp"]),
            session_id=row["session_id"],
            experience_type=row["experience_type"] or "",
            importance=row["importance"],
            access_count=row["access_count"],
            last_accessed=datetime.fromisoformat(row["last_accessed"]) if row["last_accessed"] else None,
            version=row["version"],
            parent_id=row["parent_id"],
            is_deleted=bool(row["is_deleted"]),
            supersedes=_j("supersedes", []) if "supersedes" in keys else [],
            superseded_by=row["superseded_by"] if "superseded_by" in keys else None,
            is_current=bool(row["is_current"]) if "is_current" in keys else True,
            contradiction_of=row["contradiction_of"] if "contradiction_of" in keys else None,
            decay_score=row["decay_score"] if "decay_score" in keys else 1.0,
            next_review_at=datetime.fromisoformat(row["next_review_at"]) if ("next_review_at" in keys and row["next_review_at"]) else None,
            source=row["source"] or "user",
            confidence=row["confidence"],
            tags=set(json.loads(row["tags"] or "[]")),
        )

    # ============ Supersession / current view (explicit replace, never blind merge) ============

    def supersede(self, old_id: str, new_entry: MemoryEntry, reason: str = "") -> str:
        """Explicitly replace old memory with new one. Old stays for audit, flagged not-current."""
        old = self.get(old_id)
        new_id = self.add(new_entry)
        if old:
            old.superseded_by = new_id
            old.is_current = False
            old.metadata = {**(old.metadata or {}), "supersede_reason": reason,
                            "superseded_at": datetime.utcnow().isoformat()}
            self.update(old)
            new_entry.supersedes = [*new_entry.supersedes, old_id]
            new_entry.superseded_by = None
            new_entry.is_current = True
            # re-save new with link (add already persisted; update link)
            stored = self.get(new_id)
            if stored:
                stored.supersedes = new_entry.supersedes
                self.update(stored)
        return new_id

    def touch(self, memory_id: str, boost: float = 0.05) -> None:
        """Reinforce a memory on access (Ebbinghaus: bump decay, count, timestamp)."""
        entry = self.get(memory_id)
        if not entry:
            return
        entry.access_count += 1
        entry.last_accessed = datetime.utcnow()
        entry.decay_score = min(1.0, entry.decay_score + boost)
        self.update(entry)

    def apply_decay(self, half_life_days: float = 30.0) -> int:
        """Decay all current memories by elapsed time. Returns count touched."""
        from datetime import timedelta
        now = datetime.utcnow()
        n = 0
        with self._get_cursor() as cursor:
            cursor.execute("SELECT id, last_accessed, timestamp, decay_score FROM memories WHERE is_deleted=0 AND is_current=1")
            rows = cursor.fetchall()
        for r in rows:
            try:
                base = datetime.fromisoformat(r["last_accessed"]) if r["last_accessed"] else datetime.fromisoformat(r["timestamp"])
            except Exception:
                continue
            days = max(0.0, (now - base).total_seconds() / 86400.0)
            decayed = 0.5 ** (days / half_life_days)
            entry = self.get(r["id"])
            if entry:
                entry.decay_score = round(decayed, 4)
                self.update(entry)
                n += 1
        return n
    
    def _append_episodic(self, entry: MemoryEntry):
        """Append to episodic JSONL log"""
        try:
            with open(self.episodic_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write episodic log: {e}")
    
    # ============ Core Blocks (Letta-style) ============

    def upsert_core_block(self, block: CoreBlock) -> str:
        """Create or update a core block (enforces char_limit, bumps version)."""
        if len(block.content) > block.char_limit:
            block.content = block.content[-block.char_limit:]
        existing = None
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM core_blocks WHERE label=? AND COALESCE(agent_id,'')=COALESCE(?, '')",
                           (block.label, block.agent_id))
            row = cursor.fetchone()
            if row:
                existing = row
        if existing:
            block.id = existing["id"]
            block.version = (existing["version"] or 1) + 1
            block.updated_at = datetime.utcnow()
            with self._get_cursor() as cursor:
                cursor.execute("""UPDATE core_blocks SET content=?, description=?, scope=?,
                    agent_id=?, shared=?, char_limit=?, version=?, updated_at=? WHERE id=?""",
                    (block.content, block.description, block.scope.value, block.agent_id,
                     int(block.shared), block.char_limit, block.version,
                     block.updated_at.isoformat(), block.id))
        else:
            with self._get_cursor() as cursor:
                cursor.execute("""INSERT INTO core_blocks
                    (id,label,content,description,scope,agent_id,shared,char_limit,version,updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (block.id, block.label, block.content, block.description, block.scope.value,
                     block.agent_id, int(block.shared), block.char_limit, block.version,
                     block.updated_at.isoformat()))
        return block.id

    def get_core_block(self, label: str, agent_id: Optional[str] = None) -> Optional[CoreBlock]:
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM core_blocks WHERE label=? AND COALESCE(agent_id,'')=COALESCE(?, '')",
                           (label, agent_id))
            row = cursor.fetchone()
            if not row:
                return None
            return CoreBlock(
                id=row["id"], label=row["label"], content=row["content"] or "",
                description=row["description"] or "", scope=MemoryScope(row["scope"] or "user"),
                agent_id=row["agent_id"], shared=bool(row["shared"]),
                char_limit=row["char_limit"] or 4000, version=row["version"] or 1,
                updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.utcnow(),
            )

    def list_core_blocks(self, agent_id: Optional[str] = None, include_shared: bool = True) -> List[CoreBlock]:
        with self._get_cursor() as cursor:
            if agent_id is None:
                cursor.execute("SELECT * FROM core_blocks ORDER BY label")
            elif include_shared:
                cursor.execute("SELECT * FROM core_blocks WHERE agent_id IS NULL OR agent_id=? OR shared=1 ORDER BY label",
                               (agent_id,))
            else:
                cursor.execute("SELECT * FROM core_blocks WHERE agent_id=? ORDER BY label", (agent_id,))
            out = []
            for row in cursor.fetchall():
                out.append(CoreBlock(
                    id=row["id"], label=row["label"], content=row["content"] or "",
                    description=row["description"] or "", scope=MemoryScope(row["scope"] or "user"),
                    agent_id=row["agent_id"], shared=bool(row["shared"]),
                    char_limit=row["char_limit"] or 4000, version=row["version"] or 1,
                    updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else datetime.utcnow(),
                ))
            return out

    def append_core_block(self, label: str, content: str, agent_id: Optional[str] = None) -> Optional[CoreBlock]:
        """Append-safe edit for shared blocks (Letta concurrency lesson)."""
        block = self.get_core_block(label, agent_id)
        if not block:
            return None
        block.content = (block.content + "\n" + content)[-block.char_limit:]
        self.upsert_core_block(block)
        return self.get_core_block(label, agent_id)

    # ============ Community Summaries (GraphRAG-light) ============

    def save_community_summary(self, summary: CommunitySummary) -> str:
        with self._get_cursor() as cursor:
            cursor.execute("""INSERT OR REPLACE INTO community_summaries
                (id, level, member_entities, summary, source_memory_ids, created_at)
                VALUES (?,?,?,?,?,?)""",
                (summary.id, summary.level, json.dumps(summary.member_entities),
                 summary.summary, json.dumps(summary.source_memory_ids),
                 summary.created_at.isoformat()))
        return summary.id

    def list_community_summaries(self, level: Optional[int] = None, limit: int = 50) -> List[CommunitySummary]:
        with self._get_cursor() as cursor:
            if level is None:
                cursor.execute("SELECT * FROM community_summaries ORDER BY level, created_at DESC LIMIT ?", (limit,))
            else:
                cursor.execute("SELECT * FROM community_summaries WHERE level=? ORDER BY created_at DESC LIMIT ?",
                               (level, limit))
            out = []
            for row in cursor.fetchall():
                out.append(CommunitySummary(
                    id=row["id"], level=row["level"],
                    member_entities=json.loads(row["member_entities"] or "[]"),
                    summary=row["summary"] or "",
                    source_memory_ids=json.loads(row["source_memory_ids"] or "[]"),
                    created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.utcnow(),
                ))
            return out

    # ============ Context Snapshots (Guardian) ============

    def save_snapshot(self, session_id: str, window: list, rolling_summary: str,
                      topics: list, note: str = "") -> str:
        import uuid as _uuid
        sid = _uuid.uuid4().hex[:8]
        with self._get_cursor() as cursor:
            cursor.execute("""INSERT INTO context_snapshots
                (id, session_id, window_json, rolling_summary, topics_json, note)
                VALUES (?,?,?,?,?,?)""",
                (sid, session_id, json.dumps(window), rolling_summary,
                 json.dumps(topics), note))
        return sid

    def list_snapshots(self, session_id: str, limit: int = 20) -> list:
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM context_snapshots WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
                           (session_id, limit))
            return [dict(r) for r in cursor.fetchall()]

    def get_snapshot(self, snapshot_id: str) -> Optional[dict]:
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM context_snapshots WHERE id=?", (snapshot_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ============ Deferred Queue ============

    def enqueue_deferred(self, session_id: str, model: str, task_text: str,
                         task_needs: list, reason: str, complexity: int) -> str:
        import uuid as _uuid
        did = _uuid.uuid4().hex[:8]
        with self._get_cursor() as cursor:
            cursor.execute("""INSERT INTO deferred_tasks
                (id, session_id, model, task_text, task_needs, reason, complexity, status)
                VALUES (?,?,?,?,?,?,?, 'queued')""",
                (did, session_id, model, task_text, json.dumps(task_needs),
                 reason, complexity))
        return did

    def list_deferred(self, status: str = "queued", limit: int = 50) -> list:
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM deferred_tasks WHERE status=? ORDER BY created_at DESC LIMIT ?",
                           (status, limit))
            return [dict(r) for r in cursor.fetchall()]

    def resolve_deferred(self, task_id: str, status: str,
                         resolved_model: str = "") -> bool:
        if status not in ("approved", "cancelled", "assigned"):
            return False
        with self._get_cursor() as cursor:
            cursor.execute("""UPDATE deferred_tasks SET status=?, resolved_at=CURRENT_TIMESTAMP,
                resolved_model=? WHERE id=?""", (status, resolved_model, task_id))
            return cursor.rowcount > 0

    # ============ Knowledge Graph ============
    
    def add_kg_node(self, node: KnowledgeGraphNode) -> str:
        with self._get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO kg_nodes (id, label, type, properties, embedding)
                VALUES (?, ?, ?, ?, ?)
            """, (
                node.id, node.label, node.type,
                json.dumps(node.properties),
                node.embedding if node.embedding else None,
            ))
        return node.id
    
    def get_kg_node(self, node_id: str) -> Optional[KnowledgeGraphNode]:
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM kg_nodes WHERE id = ?", (node_id,))
            row = cursor.fetchone()
            if row:
                return KnowledgeGraphNode(
                    id=row["id"],
                    label=row["label"],
                    type=row["type"],
                    properties=json.loads(row["properties"] or "{}"),
                    embedding=list(row["embedding"]) if row["embedding"] else None,
                )
        return None
    
    def add_kg_edge(self, edge: KnowledgeGraphEdge) -> str:
        with self._get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO kg_edges (id, source, target, relation, properties, weight, confidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                edge.id, edge.source, edge.target, edge.relation,
                json.dumps(edge.properties), edge.weight, edge.confidence,
            ))
        return edge.id
    
    def get_kg_neighbors(self, node_id: str, max_depth: int = 1) -> List[KnowledgeGraphEdge]:
        """Get neighbors of a node up to max_depth"""
        edges = []
        visited = set()
        current_level = {node_id}
        
        for depth in range(max_depth):
            next_level = set()
            with self._get_cursor() as cursor:
                for node in current_level:
                    cursor.execute("""
                        SELECT * FROM kg_edges WHERE source = ? OR target = ?
                    """, (node, node))
                    for row in cursor.fetchall():
                        edge = KnowledgeGraphEdge(
                            id=row["id"],
                            source=row["source"],
                            target=row["target"],
                            relation=row["relation"],
                            properties=json.loads(row["properties"] or "{}"),
                            weight=row["weight"],
                            confidence=row["confidence"],
                        )
                        if edge.id not in edges:
                            edges.append(edge)
                        neighbor = edge.target if edge.source == node else edge.source
                        if neighbor not in visited:
                            next_level.add(neighbor)
            visited.update(current_level)
            current_level = next_level
            if not current_level:
                break
        return edges
    
    # ============ Document Chunks (RAG) ============
    
    def add_document_chunk(self, chunk: DocumentChunk) -> str:
        with self._get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO document_chunks (
                    id, document_id, content, metadata, embedding,
                    chunk_index, token_count, start_char, end_char
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk.id, chunk.document_id, chunk.content,
                json.dumps(chunk.metadata),
                chunk.embedding if chunk.embedding else None,
                chunk.chunk_index, chunk.token_count,
                chunk.start_char, chunk.end_char,
            ))
        
        # Add to vector store
        if chunk.embedding and self.vector_table:
            try:
                self.vector_table.add([{
                    "id": chunk.id,
                    "vector": chunk.embedding,
                    "memory_id": chunk.id,
                    "type": "document_chunk",
                    "scope": "global",
                    "content": chunk.content[:1000],
                    "metadata": json.dumps({"document_id": chunk.document_id, "chunk_index": chunk.chunk_index}),
                    "timestamp": datetime.utcnow().isoformat(),
                }])
            except Exception as e:
                logger.warning(f"Failed to add chunk to vector store: {e}")
        
        return chunk.id
    
    def search_chunks(self, query_embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """Search document chunks by vector similarity"""
        if not self.vector_table:
            return []
        
        try:
            results = self.vector_table.search(query_embedding).limit(top_k).to_list()
            chunks = []
            for row in results:
                with self._get_cursor() as cursor:
                    cursor.execute("SELECT * FROM document_chunks WHERE id = ?", (row["memory_id"],))
                    row = cursor.fetchone()
                    if row:
                        chunks.append({
                            "id": row["id"],
                            "document_id": row["document_id"],
                            "content": row["content"],
                            "metadata": json.loads(row["metadata"] or "{}"),
                            "score": 1.0 - row["_distance"],
                        })
            return chunks
        except Exception as e:
            logger.error(f"Chunk search failed: {e}")
            return []
    
    # ============ Episodic ============
    
    def get_episodic_log(self, session_id: Optional[str] = None, limit: int = 100) -> List[MemoryEntry]:
        """Read episodic log"""
        entries = []
        try:
            with open(self.episodic_log, "r", encoding="utf-8") as f:
                for line in f:
                    if len(entries) >= limit:
                        break
                    data = json.loads(line)
                    if data.get("type") == "episodic":
                        if session_id is None or data.get("session_id") == session_id:
                            entries.append(MemoryEntry.from_dict(data))
        except Exception as e:
            logger.error(f"Failed to read episodic log: {e}")
        return entries
    
    # ============ Stats ============
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory store statistics"""
        with self._get_cursor() as cursor:
            cursor.execute("SELECT type, COUNT(*) as count FROM memories WHERE is_deleted = 0 GROUP BY type")
            type_counts = {row["type"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("SELECT COUNT(*) as total FROM memories WHERE is_deleted = 0")
            total = cursor.fetchone()["total"]
            
            cursor.execute("SELECT COUNT(*) FROM kg_nodes")
            kg_nodes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM kg_edges")
            kg_edges = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            chunks = cursor.fetchone()[0]

        episodic_count = 0
        try:
            with open(self.episodic_log, "r") as f:
                episodic_count = sum(1 for _ in f)
        except Exception:
            pass

        return {
            "total_memories": total,
            "by_type": type_counts,
            "episodic_count": episodic_count,
            "kg_nodes": kg_nodes,
            "kg_edges": kg_edges,
            "document_chunks": chunks,
            "vector_store": "lancedb" if self.vector_table else "disabled",
        }
    
    # ============ Auto-Extraction & Consolidation ============
    
    def extract_entities_and_relations(self, text: str) -> tuple[List[str], List[Dict[str, str]]]:
        """
        Extract entities and relations from text.
        Placeholder for LLM-based extraction - in production use spaCy/Stanza + LLM.
        """
        # Simple regex-based extraction for demo
        import re
        
        # Extract capitalized words as potential entities
        entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities = list(set(e for e in entities if len(e) > 2))
        
        # Simple relation patterns
        relations = []
        patterns = [
            (r'(\w+)\s+is\s+(\w+)', 'is_a'),
            (r'(\w+)\s+has\s+(\w+)', 'has'),
            (r'(\w+)\s+works\s+(?:at|for)\s+(\w+)', 'works_at'),
            (r'(\w+)\s+likes\s+(\w+)', 'likes'),
        ]
        
        for pattern, relation in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                relations.append({
                    "source": match.group(1),
                    "target": match.group(2),
                    "relation": relation,
                })
        
        return entities, relations
    
    def extract_facts_from_conversation(self, messages: List[Dict[str, Any]], session_id: str) -> List[MemoryEntry]:
        """
        Extract structured facts from conversation messages.
        Creates semantic memories from conversation.
        """
        facts = []
        
        # Combine all messages
        full_text = " ".join([m.get("content", "") for m in messages if m.get("content")])
        
        # Extract entities and relations
        entities, relations = self.extract_entities_and_relations(full_text)
        
        # Create semantic memory entries for key facts
        # In production, use LLM to extract structured facts
        for entity in entities[:10]:  # Limit
            entry = MemoryEntry(
                type=MemoryType.SEMANTIC,
                scope=MemoryScope.SESSION,
                content=f"Entity mentioned: {entity}",
                session_id=session_id,
                experience_type="extracted_fact",
                source="extracted",
                tags={"entity", "auto-extracted"},
                entities=[entity],
                metadata={"source_text": full_text[:500]},
            )
            facts.append(entry)
        
        for rel in relations[:10]:
            entry = MemoryEntry(
                type=MemoryType.SEMANTIC,
                scope=MemoryScope.SESSION,
                content=f"Relation: {rel['source']} {rel['relation']} {rel['target']}",
                session_id=session_id,
                experience_type="extracted_relation",
                source="extracted",
                tags={"relation", "auto-extracted"},
                entities=[rel["source"], rel["target"]],
                relations=[rel],
                metadata={"source_text": full_text[:500]},
            )
            facts.append(entry)
        
        # Add to store
        for fact in facts:
            self.add(fact)
        
        return facts
    
    def consolidate_working_to_longterm(self, session_id: str, importance_threshold: float = 0.7) -> int:
        """
        Consolidate working/episodic memories from a session to long-term semantic memory.
        Moves important episodic memories to semantic memory.
        """
        episodic_entries = self.get_episodic_log(session_id=session_id, limit=1000)
        
        consolidated = 0
        for entry in episodic_entries:
            if entry.importance >= importance_threshold and entry.type == MemoryType.EPISODIC:
                # Create semantic version
                semantic_entry = MemoryEntry(
                    type=MemoryType.SEMANTIC,
                    scope=MemoryScope.USER,
                    content=f"From session {session_id}: {entry.content}",
                    metadata={
                        "original_session": session_id,
                        "original_timestamp": entry.timestamp.isoformat(),
                        "consolidated_from": entry.id,
                    },
                    importance=entry.importance,
                    source="consolidated",
                    tags=entry.tags | {"consolidated"},
                    entities=entry.entities,
                    confidence=entry.confidence * 0.9,  # Slightly lower confidence
                )
                
                self.add(semantic_entry)
                consolidated += 1
        
        logger.info(f"Consolidated {consolidated} memories from session {session_id}")
        return consolidated
    
    def summarize_session(self, session_id: str, max_length: int = 500) -> str:
        """Generate a summary of a session from episodic log"""
        entries = self.get_episodic_log(session_id=session_id, limit=200)
        
        if not entries:
            return "No conversation history found."
        
        # Simple summary - in production use LLM
        user_messages = [e.content for e in entries if e.metadata.get("role") == "user"]
        assistant_messages = [e.content for e in entries if e.metadata.get("role") == "assistant"]
        
        summary_parts = []
        if user_messages:
            summary_parts.append(f"User asked about: {', '.join(user_messages[:3])}")
        if assistant_messages:
            summary_parts.append(f"Assistant provided: {', '.join(assistant_messages[:3])}")
        
        summary = ". ".join(summary_parts)
        return summary[:max_length]
    
    def get_session_timeline(self, session_id: str) -> List[Dict[str, Any]]:
        """Get timeline of a session"""
        entries = self.get_episodic_log(session_id=session_id, limit=500)
        
        timeline = []
        for entry in entries:
            timeline.append({
                "timestamp": entry.timestamp.isoformat(),
                "type": entry.type.value,
                "content": entry.content[:200],
                "role": entry.metadata.get("role", "unknown"),
                "importance": entry.importance,
            })
        
        return timeline
    
    def get_memory_graph(self, center_entity: str, max_depth: int = 2) -> Dict[str, Any]:
        """Get subgraph around an entity for visualization"""
        nodes = []
        edges = []
        visited = set()
        
        def traverse(entity: str, depth: int):
            if depth > 2 or entity in visited:
                return
            visited.add(entity)
            
            # Add center node
            if entity not in [n["id"] for n in nodes]:
                nodes.append({
                    "id": entity,
                    "label": entity,
                    "type": "entity",
                })
            
            # Find related edges
            kg_edges = self.get_kg_neighbors(entity, max_depth=1)
            for edge in kg_edges:
                if edge.id not in [e["id"] for e in edges]:
                    edges.append({
                        "id": edge.id,
                        "source": edge.source,
                        "target": edge.target,
                        "relation": edge.relation,
                        "weight": edge.weight,
                    })
                
                # Traverse neighbors
                for edge in kg_edges:
                    neighbor = edge.target if edge.source == entity else edge.source
                    if neighbor not in visited:
                        if neighbor not in [n["id"] for n in nodes]:
                            nodes.append({
                                "id": neighbor,
                                "label": neighbor,
                                "type": "entity",
                            })
        
        traverse(center_entity, 0)
        
        return {"nodes": nodes, "edges": edges}
    
    def close(self):
        """Close connections"""
        if self.conn:
            self.conn.close()
        logger.info("MemoryStore closed")


# Global store instance
_store: Optional[MemoryStore] = None


def get_memory_store(data_dir: Optional[str] = None) -> MemoryStore:
    """Get or create global memory store"""
    global _store
    if _store is None:
        _store = MemoryStore(data_dir or "./data/memory")
    return _store