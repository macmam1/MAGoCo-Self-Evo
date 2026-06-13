"""Agent base class — LLM + Tools + Memory + Role."""
from dataclasses import dataclass, field
from typing import Any

from app.services.agents.tool import Tool, ToolRegistry
from app.services.llm import LLMMessage, LLMProvider, LLMResponse, get_provider
from app.models.agent import LLMProvider as LLMProviderEnum


@dataclass
class AgentMemory:
    """Simple short-term memory for an agent."""

    messages: list[LLMMessage] = field(default_factory=list)
    max_size: int = 50

    def add(self, message: LLMMessage) -> None:
        self.messages.append(message)
        # Trim to max size
        if len(self.messages) > self.max_size:
            # نگه داشتن system message (index 0) و آخرین‌ها
            system = self.messages[0] if self.messages[0].role == "system" else None
            recent = self.messages[-(self.max_size - (1 if system else 0)):]
            self.messages = ([system] + recent) if system else recent

    def clear(self) -> None:
        # فقط نگه داشتن system prompt
        system = next((m for m in self.messages if m.role == "system"), None)
        self.messages = [system] if system else []

    def to_list(self) -> list[LLMMessage]:
        return list(self.messages)


@dataclass
class AgentConfig:
    """Agent configuration."""

    name: str
    role: str
    system_prompt: str = ""
    llm_provider: LLMProviderEnum = LLMProviderEnum.OPENAI
    model_name: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2048
    tool_names: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRunResult:
    """Result of running an agent."""

    content: str
    model: str
    provider: str
    tokens_input: int = 0
    tokens_output: int = 0
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


class Agent:
    """AI Agent — role + LLM + tools + memory."""

    def __init__(self, config: AgentConfig, llm: LLMProvider | None = None) -> None:
        self.config = config
        self.llm = llm or get_provider(config.llm_provider)
        self.memory = AgentMemory()
        if config.system_prompt:
            self.memory.add(LLMMessage(role="system", content=config.system_prompt))
        self._tools: dict[str, Tool] = self._load_tools(config.tool_names)

    def _load_tools(self, names: list[str]) -> dict[str, Tool]:
        tools: dict[str, Tool] = {}
        for name in names:
            tool = ToolRegistry.get(name)
            if tool:
                tools[name] = tool
        return tools

    def add_tool(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def reset_memory(self) -> None:
        self.memory.clear()
        if self.config.system_prompt:
            self.memory.add(LLMMessage(role="system", content=self.config.system_prompt))

    async def run(
        self,
        user_message: str,
        *,
        stream: bool = False,
    ) -> AgentRunResult:
        """اجرای agent با یه پیام کاربر."""
        self.memory.add(LLMMessage(role="user", content=user_message))

        response: LLMResponse = await self.llm.complete(
            self.memory.to_list(),
            model=self.config.model_name,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        self.memory.add(LLMMessage(role="assistant", content=response.content))

        return AgentRunResult(
            content=response.content,
            model=response.model,
            provider=response.provider,
            tokens_input=response.tokens_input,
            tokens_output=response.tokens_output,
        )

    async def stream(self, user_message: str):
        """Stream agent response."""
        self.memory.add(LLMMessage(role="user", content=user_message))
        full = ""
        async for chunk in self.llm.stream(
            self.memory.to_list(),
            model=self.config.model_name,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        ):
            full += chunk.content
            yield chunk
        self.memory.add(LLMMessage(role="assistant", content=full))

    def to_dict(self) -> dict[str, Any]:
        """Serialize for debugging/logging."""
        return {
            "name": self.config.name,
            "role": self.config.role,
            "llm_provider": self.config.llm_provider.value,
            "model": self.config.model_name,
            "tools": list(self._tools.keys()),
            "memory_size": len(self.memory.messages),
        }
