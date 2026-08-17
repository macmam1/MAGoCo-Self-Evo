"""LLM Provider Base Class and Gateway.

Supports: OpenAI (API), Ollama (Local), Anthropic, HuggingFace.
Auto-fallback, streaming, retry logic.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from asyncio import Lock


@dataclass
class LLMMessage:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None


@dataclass
class LLMResponse:
    content: str
    tool_calls: Optional[List[Dict]] = None
    usage: Optional[Dict[str, int]] = None
    finish_reason: str = "stop"


class LLMProvider(ABC):
    """Base class for all LLM providers."""

    name: str
    models: List[str]

    @abstractmethod
    async def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass


class LLMGateway:
    """Gateway managing multiple providers with auto-fallback."""

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.preferred_order: List[str] = []
        self._lock = Lock()

    def register(self, provider: LLMProvider):
        self.providers[provider.name] = provider
        if provider.name not in self.preferred_order:
            self.preferred_order.append(provider.name)

    async def complete(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Try providers in preferred order until one succeeds."""
        last_error = None

        for provider_name in self.preferred_order:
            provider = self.providers.get(provider_name)
            if provider is None:
                continue
            if await provider.is_available():
                try:
                    return await provider.complete(messages, **kwargs)
                except Exception as e:
                    last_error = e
                    print(f"[LLM Gateway] {provider.name} failed: {e}, trying next...")
                    continue

        raise RuntimeError(f"No LLM provider available. Last error: {last_error}")

    def get_available_models(self) -> List[str]:
        models = []
        for p in self.providers.values():
            models.extend(p.models)
        return models


# Global gateway instance
llm_gateway = LLMGateway()
