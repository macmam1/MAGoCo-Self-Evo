"""Three-Layer Memory System for Agents.

1. Working Context: Active short-term window.
2. Full Verbatim History: Complete record of all turns.
3. Distilled Knowledge: Extracted persistent facts.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryMessage:
    role: str
    content: str
    timestamp: float = 0.0


class ThreeLayerMemory:
    """Manages agent memory across three distinct layers."""
    
    def __init__(self, max_working_size: int = 20):
        self.max_working_size = max_working_size
        self.working_context: list[MemoryMessage] = []
        self.verbatim_history: list[MemoryMessage] = []
        self.distilled_knowledge: dict[str, Any] = {}
    
    def add_turn(self, role: str, content: str) -> None:
        """Add a conversation turn to working context and verbatim history."""
        msg = MemoryMessage(role=role, content=content)
        self.verbatim_history.append(msg)
        self.working_context.append(msg)
        
        # Trim working context if exceeds limit
        if len(self.working_context) > self.max_working_size:
            # Keep system prompt if present, remove oldest messages
            self.working_context = self.working_context[-self.max_working_size:]
    
    def store_knowledge(self, key: str, value: Any) -> None:
        """Store distilled knowledge."""
        self.distilled_knowledge[key] = value
    
    def get_knowledge(self, key: str) -> Any:
        """Retrieve distilled knowledge."""
        return self.distilled_knowledge.get(key)
    
    def clear_working(self) -> None:
        """Clear active working context."""
        self.working_context.clear()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "working_context_size": len(self.working_context),
            "verbatim_history_size": len(self.verbatim_history),
            "distilled_knowledge_keys": list(self.distilled_knowledge.keys()),
        }
