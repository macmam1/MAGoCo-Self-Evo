"""Tool system — agent tools that LLM می‌تونه فراخوانی کنه."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolParameter:
    """Schema for a tool parameter."""

    name: str
    type: str  # "string" | "number" | "boolean" | "object"
    description: str
    required: bool = True
    enum: list[Any] | None = None


@dataclass
class ToolSchema:
    """Schema describing a tool for the LLM."""

    name: str
    description: str
    parameters: list[ToolParameter] = field(default_factory=list)


class Tool(ABC):
    """Base class for agent tools."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def parameters(self) -> list[ToolParameter]: ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        """Run the tool and return a string result."""
        ...

    def to_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )


class ToolRegistry:
    """Global registry of available tools (plugin pattern)."""

    _tools: dict[str, Tool] = {}

    @classmethod
    def register(cls, tool: Tool) -> None:
        cls._tools[tool.name] = tool

    @classmethod
    def unregister(cls, name: str) -> None:
        cls._tools.pop(name, None)

    @classmethod
    def get(cls, name: str) -> Tool | None:
        return cls._tools.get(name)

    @classmethod
    def list_all(cls) -> list[Tool]:
        return list(cls._tools.values())

    @classmethod
    def names(cls) -> list[str]:
        return list(cls._tools.keys())

    @classmethod
    def clear(cls) -> None:
        cls._tools.clear()
