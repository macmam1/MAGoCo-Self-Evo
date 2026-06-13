"""LLM Provider abstraction — protocol/interface.

هر provider باید این interface رو پیاده‌سازی کنه.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class LLMMessage:
    """یه پیام برای LLM."""

    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """پاسخ LLM."""

    content: str
    model: str
    provider: str
    tokens_input: int = 0
    tokens_output: int = 0
    finish_reason: str = "stop"
    extra: dict[str, Any] = field(default_factory=dict)


class LLMError(Exception):
    """خطای LLM provider."""


class LLMRateLimitError(LLMError):
    """Rate limit exceeded."""


class LLMProvider(ABC):
    """Interface برای همه LLM provider ها."""

    name: str = "base"

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate completion از messages."""
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ):
        """Stream completion (async generator)."""
        ...
        yield LLMResponse  # type: ignore

    def is_available(self) -> bool:
        """آیا provider در دسترسه (API key داره)؟"""
        return True
