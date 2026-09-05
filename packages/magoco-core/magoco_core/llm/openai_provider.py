"""OpenAI Provider (API-based)."""

import os
from typing import AsyncGenerator, List, Dict, Any, Optional
from openai import AsyncOpenAI

from magoco_core.llm.gateway import LLMProvider, LLMMessage, LLMResponse


class OpenAIProvider(LLMProvider):
    name = "openai"
    models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
        "o1-preview",
        "o1-mini",
    ]

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=self.api_key) if self.api_key else None

    async def is_available(self) -> bool:
        return self.api_key is not None and self.client is not None

    async def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        if not self.client:
            raise RuntimeError("OpenAI API key not configured")

        # Convert to OpenAI format
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]
        if tools:
            openai_tools = [{"type": "function", "function": t} for t in tools]
        else:
            openai_tools = None

        model = model or "gpt-4o-mini"

        if stream:
            return self._stream_complete(openai_messages, model, temperature, max_tokens, openai_tools)
        else:
            response = await self.client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=openai_tools,
                tool_choice="auto" if openai_tools else None,
            )
            
            choice = response.choices[0]
            return LLMResponse(
                content=choice.message.content or "",
                model=model,
                tool_calls=[
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in choice.message.tool_calls or []
                ],
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                } if response.usage else None,
                finish_reason=choice.finish_reason,
            )

    async def _stream_complete(
        self,
        messages: List[Dict],
        model: str,
        temperature: float,
        max_tokens: int,
        tools: Optional[List[Dict]],
    ) -> AsyncGenerator[str, None]:
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,
            tool_choice="auto" if tools else None,
            stream=True,
        )
        
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content