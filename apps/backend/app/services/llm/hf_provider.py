"""Hugging Face Inference API provider."""
from typing import Any, AsyncIterator

import httpx

from app.core.config import settings
from app.services.llm.base import LLMError, LLMMessage, LLMProvider, LLMResponse


class HuggingFaceProvider(LLMProvider):
    """Hugging Face Inference API provider (رایگان برای مدل‌های public)."""

    name = "huggingface"
    default_model = "meta-llama/Llama-3.2-3B-Instruct"
    api_base = "https://api-inference.huggingface.co/models"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.HUGGINGFACE_API_KEY
        if not self.api_key:
            raise LLMError("HUGGINGFACE_API_KEY is not set")

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> LLMResponse:
        model_id = model or self.default_model
        # تبدیل messages به prompt ساده
        prompt = self._messages_to_prompt(messages)
        payload = {
            "inputs": prompt,
            "parameters": {
                "temperature": temperature,
                "max_new_tokens": max_tokens,
                "return_full_text": False,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.api_base}/{model_id}",
                    headers=self._headers(),
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                if isinstance(data, list) and data:
                    content = data[0].get("generated_text", "")
                elif isinstance(data, dict):
                    content = data.get("generated_text", "")
                else:
                    content = str(data)

                return LLMResponse(
                    content=content,
                    model=model_id,
                    provider=self.name,
                )
        except httpx.HTTPStatusError as e:
            raise LLMError(f"HF API error {e.response.status_code}: {e.response.text}") from e
        except Exception as e:
            raise LLMError(f"HF error: {e}") from e

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> AsyncIterator[LLMResponse]:
        # HF Inference API در حالت استریم ساده نیست — fallback به complete
        response = await self.complete(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        yield response

    def _messages_to_prompt(self, messages: list[LLMMessage]) -> str:
        """تبدیل messages به یه prompt ساده."""
        parts = []
        for m in messages:
            if m.role == "system":
                parts.append(f"System: {m.content}")
            elif m.role == "user":
                parts.append(f"User: {m.content}")
            elif m.role == "assistant":
                parts.append(f"Assistant: {m.content}")
        parts.append("Assistant:")
        return "\n\n".join(parts)
