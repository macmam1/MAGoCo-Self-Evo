"""Ollama Provider (Local LLM - no API key needed)."""

import os
import httpx
from typing import AsyncGenerator, List, Dict, Any, Optional

from magoco_core.llm.gateway import LLMProvider, LLMMessage, LLMResponse


class OllamaProvider(LLMProvider):
    name = "ollama"
    models = [
        "llama3.1:8b",
        "llama3.1:70b",
        "llama3.2:3b",
        "qwen2.5:7b",
        "qwen2.5:14b",
        "codellama:13b",
        "mistral:7b",
        "phi3:14b",
    ]

    def __init__(self):
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)

    async def is_available(self) -> bool:
        try:
            resp = await self.client.get("/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        if not await self.is_available():
            raise RuntimeError("Ollama server not reachable")

        model = model or "llama3.1:8b"
        
        # Convert messages to Ollama format
        ollama_messages = [{"role": m.role, "content": m.content} for m in messages]
        
        payload = {
            "model": model,
            "messages": ollama_messages,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": stream,
        }

        if stream:
            return self._stream_complete(payload)
        else:
            resp = await self.client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            
            return LLMResponse(
                content=data.get("message", {}).get("content", ""),
                tool_calls=None,  # Ollama native tool calling needs special format
                usage=None,
                finish_reason="stop",
            )

    async def _stream_complete(self, payload: Dict) -> AsyncGenerator[str, None]:
        async with self.client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.strip():
                    import json
                    data = json.loads(line)
                    if "message" in data and "content" in data["message"]:
                        yield data["message"]["content"]
                    if data.get("done", False):
                        break