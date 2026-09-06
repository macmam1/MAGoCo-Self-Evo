"""Memory self-editing tools — Letta-style agent-managed memory.

The agent itself decides what to remember via tool calls:
- core_memory_append / core_memory_replace / core_memory_read (always-in-context blocks)
- archival_memory_insert / archival_memory_search (long-term semantic store)
- recall_search (episodic / conversation history)
- memory_supersede (explicit replace with audit trail — never blind merge)
- memory_distill (session -> facts promotion)
"""

from typing import Any

from magoco_core.tools.registry import Tool, ToolResult, tool_registry
from magoco_core.memory.models import CoreBlock, MemoryEntry, MemoryType, MemoryScope, MemoryQuery
from magoco_core.memory.store import get_memory_store


def _store():
    return get_memory_store()


class CoreMemoryReadTool(Tool):
    @property
    def name(self) -> str:
        return "core_memory_read"

    @property
    def description(self) -> str:
        return "Read always-in-context core memory blocks (persona/human/project). Use before answering when user facts may matter."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "Block label, empty for all"},
                "agent_id": {"type": "string", "description": "Agent id, empty for shared/global"},
            },
            "required": [],
        }

    async def execute(self, label: str = "", agent_id: str = "") -> ToolResult:
        try:
            store = _store()
            aid = agent_id or None
            if label:
                block = store.get_core_block(label, aid)
                if not block and aid:
                    block = store.get_core_block(label, None)  # fall back to shared
                if not block:
                    return ToolResult(success=False, content="", error=f"Block not found: {label}")
                return ToolResult(success=True, content=block.content,
                                  metadata={"label": block.label, "version": block.version})
            blocks = store.list_core_blocks(aid, include_shared=True)
            content = "\n\n".join(f"[{b.label}]: {b.content}" for b in blocks)
            return ToolResult(success=True, content=content or "(no core blocks)",
                              metadata={"count": len(blocks)})
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class CoreMemoryAppendTool(Tool):
    @property
    def name(self) -> str:
        return "core_memory_append"

    @property
    def description(self) -> str:
        return "Append a fact to a core memory block (safe for shared blocks, minimal race). Use for durable user/agent facts."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "label": {"type": "string", "description": "Block label e.g. human, persona"},
                "content": {"type": "string", "description": "Fact to append"},
                "agent_id": {"type": "string", "description": "Agent id, empty for shared"},
                "description": {"type": "string", "description": "Block description if creating"},
            },
            "required": ["label", "content"],
        }

    async def execute(self, label: str, content: str, agent_id: str = "", description: str = "") -> ToolResult:
        try:
            store = _store()
            aid = agent_id or None
            block = store.get_core_block(label, aid)
            if not block:
                block = CoreBlock(label=label, content=content, description=description or f"Core facts: {label}",
                                  agent_id=aid, shared=(aid is None))
                store.upsert_core_block(block)
                return ToolResult(success=True, content=f"Created block {label}", metadata={"label": label})
            updated = store.append_core_block(label, content, aid)
            if not updated:
                return ToolResult(success=False, content="", error="Append failed")
            return ToolResult(success=True, content=f"Appended to {label} (v{updated.version})",
                              metadata={"label": label, "version": updated.version})
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class CoreMemoryReplaceTool(Tool):
    @property
    def name(self) -> str:
        return "core_memory_replace"

    @property
    def description(self) -> str:
        return "Replace a span inside a core block. Single-writer only; prefer append for shared blocks."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "label": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
                "agent_id": {"type": "string"},
            },
            "required": ["label", "old_text", "new_text"],
        }

    async def execute(self, label: str, old_text: str, new_text: str, agent_id: str = "") -> ToolResult:
        try:
            store = _store()
            aid = agent_id or None
            block = store.get_core_block(label, aid)
            if not block:
                return ToolResult(success=False, content="", error=f"Block not found: {label}")
            if old_text not in block.content:
                return ToolResult(success=False, content="", error="old_text not found in block")
            block.content = block.content.replace(old_text, new_text, 1)
            store.upsert_core_block(block)
            return ToolResult(success=True, content=f"Replaced in {label} (v{block.version + 1})")
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class ArchivalMemoryInsertTool(Tool):
    @property
    def name(self) -> str:
        return "archival_memory_insert"

    @property
    def description(self) -> str:
        return "Store a fact in long-term archival memory (semantic, out-of-context)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "importance": {"type": "number", "default": 0.8},
            },
            "required": ["content"],
        }

    async def execute(self, content: str, tags: list = None, importance: float = 0.8) -> ToolResult:
        try:
            store = _store()
            entry = MemoryEntry(type=MemoryType.SEMANTIC, scope=MemoryScope.USER,
                                content=content, importance=importance,
                                source="agent", tags=set(tags or ["archival"]))
            mid = store.add(entry)
            return ToolResult(success=True, content=f"Stored archival memory {mid}", metadata={"id": mid})
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class ArchivalMemorySearchTool(Tool):
    @property
    def name(self) -> str:
        return "archival_memory_search"

    @property
    def description(self) -> str:
        return "Semantic/keyword search over archival memory. Returns current (non-superseded) facts by default."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 5},
                "current_only": {"type": "boolean", "default": True},
            },
            "required": ["query"],
        }

    async def execute(self, query: str, top_k: int = 5, current_only: bool = True) -> ToolResult:
        try:
            store = _store()
            q = MemoryQuery(query=query, top_k=top_k, current_only=current_only,
                            use_vector=False, use_keyword=True)
            results = store.search(q)
            for r in results:
                store.touch(r.entry.id)
            content = "\n\n".join(f"- {r.entry.content} (id={r.entry.id}, score={r.score:.2f})" for r in results)
            return ToolResult(success=True, content=content or "(no matches)",
                              metadata={"count": len(results)})
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class RecallSearchTool(Tool):
    @property
    def name(self) -> str:
        return "recall_search"

    @property
    def description(self) -> str:
        return "Search episodic / conversation history (recall storage)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "session_id": {"type": "string"},
                "top_k": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        }

    async def execute(self, query: str, session_id: str = "", top_k: int = 5) -> ToolResult:
        try:
            from magoco_core.memory.models import MemoryType as MT
            store = _store()
            q = MemoryQuery(query=query, types=[MT.EPISODIC], top_k=top_k,
                            session_id=session_id or None, use_vector=False, use_keyword=True)
            results = store.search(q)
            content = "\n\n".join(f"- {r.entry.content[:300]}" for r in results)
            return ToolResult(success=True, content=content or "(no episodic matches)",
                              metadata={"count": len(results)})
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class MemorySupersedeTool(Tool):
    @property
    def name(self) -> str:
        return "memory_supersede"

    @property
    def description(self) -> str:
        return "Explicitly replace an outdated memory with a corrected one. Old stays for audit (is_current=false). Never use for merely related facts."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "old_id": {"type": "string", "description": "ID of outdated memory"},
                "content": {"type": "string", "description": "Corrected content"},
                "reason": {"type": "string", "description": "Why it supersedes"},
            },
            "required": ["old_id", "content"],
        }

    async def execute(self, old_id: str, content: str, reason: str = "") -> ToolResult:
        try:
            store = _store()
            old = store.get(old_id)
            if not old:
                return ToolResult(success=False, content="", error=f"Not found: {old_id}")
            new_entry = MemoryEntry(type=old.type, scope=old.scope, content=content,
                                    importance=old.importance, source="agent",
                                    tags=set(old.tags) | {"superseding"},
                                    contradiction_of=old_id)
            new_id = store.supersede(old_id, new_entry, reason=reason)
            return ToolResult(success=True, content=f"Superseded {old_id} -> {new_id}",
                              metadata={"old_id": old_id, "new_id": new_id})
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


class MemoryDistillTool(Tool):
    @property
    def name(self) -> str:
        return "memory_distill"

    @property
    def description(self) -> str:
        return "Distill a session into long-term facts (consolidation). Moves important episodic memories to semantic."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "importance_threshold": {"type": "number", "default": 0.7},
            },
            "required": ["session_id"],
        }

    async def execute(self, session_id: str, importance_threshold: float = 0.7) -> ToolResult:
        try:
            store = _store()
            n = store.consolidate_working_to_longterm(session_id, importance_threshold)
            return ToolResult(success=True, content=f"Consolidated {n} memories from {session_id}",
                              metadata={"count": n})
        except Exception as e:
            return ToolResult(success=False, content="", error=str(e))


# Register all memory tools
tool_registry.register(CoreMemoryReadTool())
tool_registry.register(CoreMemoryAppendTool())
tool_registry.register(CoreMemoryReplaceTool())
tool_registry.register(ArchivalMemoryInsertTool())
tool_registry.register(ArchivalMemorySearchTool())
tool_registry.register(RecallSearchTool())
tool_registry.register(MemorySupersedeTool())
tool_registry.register(MemoryDistillTool())
