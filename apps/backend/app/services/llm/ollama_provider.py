"""Ollama provider (local LLM)."""
from typing import Any, AsyncIterator

import httpx

from app.core.config import settings
from app.services.llm.base import LLMError, LLMMessage, LLMProvider, LLMResponse


class OllamaProvider(LLMProvider):
    """Ollama provider (local LLM server).

    نیاز به اجرای ollama server در سیستم یا در container جدا.
    """

    name = "ollama"
    default_model = "llama3.2"

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    def is_available(self) -> bool:
        # چک کردن در دسترس بودن نیاز به async call داره — فرض می‌کنیم در دسترسه
        return True

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        model_name = model or self.default_model
        payload = {
            "model": model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "")
                return LLMResponse(
                    content=content,
                    model=model_name,
                    provider=self.name,
                    tokens_input=data.get("prompt_eval_count", 0),
                    tokens_output=data.get("eval_count", 0),
                    finish_reason=data.get("done_reason", "stop"),
                )
        except httpx.HTTPStatusError as e:
            raise LLMError(f"Ollama error {e.response.status_code}: {e.response.text}") from e
        except Exception as e:
            raise LLMError(f"Ollama connection error: {e}") from e

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> AsyncIterator[LLMResponse]:
        model_name = model or self.default_model
        payload = {
            "model": model_name,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            import json
                            data = json.loads(line)
                            content = data.get("message", {}).get("content", "")
                            if content:
                                yield LLMResponse(
                                    content=content,
                                    model=model_name,
                                    provider=self.name,
                                )
        except Exception as e:
            raise LLMError(f"Ollama stream error: {e}") from e
