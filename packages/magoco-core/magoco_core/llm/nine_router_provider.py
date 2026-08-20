"""
NINE_ROUTER Provider for MAGoCo-Self-Evo LLM Gateway.

This provider connects to the NINE_ROUTER_API_KEY endpoint.
It will be used for testing chat interfaces and agents in the MAGoCo-Self-Evo
project after construction is complete.
"""

import os
import json
import httpx
from typing import List, Dict, Any, Optional

from magoco_core.llm.gateway import LLMProvider, LLMMessage, LLMResponse


class NineRouterProvider(LLMProvider):
    """
    NINE_ROUTER API provider.
    
    Supports:
    - Multiple models (configured via NINE_ROUTER_API_KEY)
    - Streaming responses
    - Tool calling (if supported)
    """
    
    name = "nine_router"
    models = [
        "gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet",
        "deepseek-chat", "qwen-max", "llama-3.1-70b"
    ]
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.9router.ai/v1"):
        self.api_key = api_key or os.environ.get("NINE_ROUTER_API_KEY")
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=60.0)
    
    async def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        if not self.api_key:
            raise ValueError("NINE_ROUTER_API_KEY not found in environment")
        
        payload = {
            "model": model or self.models[0],
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        if tools:
            payload["tools"] = tools
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self._client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            return LLMResponse(
                content=data["choices"][0]["message"]["content"],
                tool_calls=data["choices"][0]["message"].get("tool_calls"),
                usage=data.get("usage"),
                finish_reason=data["choices"][0].get("finish_reason", "stop")
            )
        
        except httpx.HTTPError as e:
            raise RuntimeError(f"NINE_ROUTER API error: {e}")
    
    async def is_available(self) -> bool:
        """Check if NINE_ROUTER is available"""
        if not self.api_key:
            return False
        try:
            # Quick health check
            response = await self._client.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.status_code == 200
        except:
            return False
