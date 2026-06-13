"""OpenAI provider."""
from typing import Any, AsyncIterator

from openai import AsyncOpenAI, RateLimitError

from app.core.config import settings
from app.services.llm.base import (
    LLMError,
    LLMMessage,
    LLMProvider,
    LLMRateLimitError,
    LLMResponse,
)


class OpenAIProvider(LLMProvider):
    """OpenAI provider (GPT-4o, GPT-4o-mini, و غیره)."""

    name = "openai"
    default_model = "gpt-4o-mini"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY is not set")
        self.client = AsyncOpenAI(api_key=self.api_key)

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
        try:
            response = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            choice = response.choices[0]
            usage = response.usage
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                provider=self.name,
                tokens_input=usage.prompt_tokens if usage else 0,
                tokens_output=usage.completion_tokens if usage else 0,
                finish_reason=choice.finish_reason or "stop",
            )
        except RateLimitError as e:
            raise LLMRateLimitError(f"OpenAI rate limit: {e}") from e
        except Exception as e:
            raise LLMError(f"OpenAI error: {e}") from e

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> AsyncIterator[LLMResponse]:
        try:
            stream = await self.client.chat.completions.create(
                model=model or self.default_model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield LLMResponse(
                        content=chunk.choices[0].delta.content,
                        model=model or self.default_model,
                        provider=self.name,
                    )
        except RateLimitError as e:
            raise LLMRateLimitError(f"OpenAI rate limit: {e}") from e
        except Exception as e:
            raise LLMError(f"OpenAI error: {e}") from e
