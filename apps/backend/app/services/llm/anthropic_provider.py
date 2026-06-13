"""Anthropic provider (Claude)."""
from typing import Any, AsyncIterator

from anthropic import AsyncAnthropic, RateLimitError

from app.core.config import settings
from app.services.llm.base import (
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMRateLimitError,
    LLMResponse,
)


class AnthropicProvider(LLMProvider):
    """Anthropic provider (Claude 3.5 Sonnet, Haiku, و غیره)."""

    name = "anthropic"
    default_model = "claude-3-5-sonnet-20241022"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        if not self.api_key:
            raise LLMError("ANTHROPIC_API_KEY is not set")
        self.client = AsyncAnthropic(api_key=self.api_key)

    def is_available(self) -> bool:
        return bool(self.api_key)

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        # Anthropic needs system message separate
        system_msg = None
        converted = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                converted.append({"role": m.role, "content": m.content})

        try:
            response = await self.client.messages.create(
                model=model or self.default_model,
                system=system_msg or "You are a helpful assistant.",
                messages=converted,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            content = "".join(
                block.text for block in response.content if hasattr(block, "text")
            )
            return LLMResponse(
                content=content,
                model=response.model,
                provider=self.name,
                tokens_input=response.usage.input_tokens,
                tokens_output=response.usage.output_tokens,
                finish_reason=response.stop_reason or "stop",
            )
        except RateLimitError as e:
            raise LLMRateLimitError(f"Anthropic rate limit: {e}") from e
        except Exception as e:
            raise LLMError(f"Anthropic error: {e}") from e

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> AsyncIterator[LLMResponse]:
        system_msg = None
        converted = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content
            else:
                converted.append({"role": m.role, "content": m.content})

        try:
            async with self.client.messages.stream(
                model=model or self.default_model,
                system=system_msg or "You are a helpful assistant.",
                messages=converted,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            ) as stream:
                async for text in stream.text_stream:
                    yield LLMResponse(
                        content=text,
                        model=model or self.default_model,
                        provider=self.name,
                    )
        except RateLimitError as e:
            raise LLMRateLimitError(f"Anthropic rate limit: {e}") from e
        except Exception as e:
            raise LLMError(f"Anthropic error: {e}") from e
