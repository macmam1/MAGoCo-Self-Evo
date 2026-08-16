"""Tool Registry - Central registry for all available tools."""

from abc import ABC, abstractmethod
from typing import Any
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    content: str
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """Base class for all tools."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON schema for tool parameters."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass


class ToolRegistry:
    """Central registry for managing tools."""
    
    def __init__(self):
        self._tools: dict[str, Tool] = {}
    
    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> list[Tool]:
        """List all registered tools."""
        return list(self._tools.values())
    
    def get_schemas(self) -> list[dict[str, Any]]:
        """Get OpenAI-compatible function schemas for all tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]


# Global registry instance
tool_registry = ToolRegistry()