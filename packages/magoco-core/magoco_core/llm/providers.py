"""Provider configs + generic OpenAI-compatible runtime.

Two kinds only (by design — see README):
- ollama-local: local runtime (Ollama/LM Studio/llama.cpp...), key ignored
- openai-compatible: any base_url + api_key + model (covers OpenAI, Azure,
  gateways like OpenRouter/LiteLLM/Portkey/9Router-as-endpoint, vLLM, ...)

The model id is an opaque string passed through verbatim.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from magoco_core.llm.gateway import LLMProvider, LLMMessage, LLMResponse


class ProviderKind(str, Enum):
    OLLAMA_LOCAL = "ollama-local"
    OPENAI_COMPATIBLE = "openai-compatible"


@dataclass
class ProviderConfig:
    """User-configured provider. api_key_encrypted at rest, never logged."""
    id: str
    name: str
    kind: ProviderKind = ProviderKind.OPENAI_COMPATIBLE
    base_url: str = ""
    api_key_encrypted: str = ""
    models: List[str] = field(default_factory=list)
    default_model: str = ""
    enabled: bool = True
    timeout: float = 120.0
    extra_headers: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self, include_secret: bool = False) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind.value,
            "base_url": self.base_url,
            "has_key": bool(self.api_key_encrypted),
            "api_key_encrypted": self.api_key_encrypted if include_secret else "***",
            "models": self.models,
            "default_model": self.default_model,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "extra_headers": self.extra_headers,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProviderConfig":
        kind = data.get("kind", "openai-compatible")
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            kind=ProviderKind(kind),
            base_url=data.get("base_url", "").rstrip("/"),
            api_key_encrypted=data.get("api_key_encrypted", ""),
            models=list(data.get("models", [])),
            default_model=data.get("default_model", ""),
            enabled=data.get("enabled", True),
            timeout=float(data.get("timeout", 120.0)),
            extra_headers=dict(data.get("extra_headers", {})),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )


class CompatibleProvider(LLMProvider):
    """Runtime: any OpenAI-compatible endpoint via httpx. Key may be '' for local."""

    def __init__(self, base_url: str, api_key: str = "", name: str = "custom",
                 models: Optional[List[str]] = None, timeout: float = 120.0,
                 extra_headers: Optional[Dict[str, str]] = None):
        self._name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or "not-needed"
        self.models = models or []
        self.timeout = timeout
        self.extra_headers = extra_headers or {}

    @property
    def name(self) -> str:
        return self._name

    async def is_available(self) -> bool:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{self.base_url}/models",
                                     headers=self._headers())
                return r.status_code < 500
        except Exception:
            return False

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        h.update(self.extra_headers)
        return h

    async def complete(
        self,
        messages: List[LLMMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        tools: Optional[List[Dict]] = None,
    ) -> LLMResponse:
        import httpx
        body: Dict[str, Any] = {
            "model": model or (self.models[0] if self.models else ""),
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            body["tools"] = [{"type": "function", "function": t} for t in tools]
            body["tool_choice"] = "auto"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.base_url}/chat/completions",
                                  headers=self._headers(), json=body)
            r.raise_for_status()
            data = r.json()
        choice = data["choices"][0]
        msg = choice.get("message", {})
        tool_calls = [
            {"id": tc.get("id"), "type": "function",
             "function": {"name": tc["function"]["name"], "arguments": tc["function"].get("arguments", "")}}
            for tc in (msg.get("tool_calls") or [])
        ]
        usage = data.get("usage") or {}
        return LLMResponse(
            content=msg.get("content") or "",
            tool_calls=tool_calls,
            usage={"prompt_tokens": usage.get("prompt_tokens", 0),
                   "completion_tokens": usage.get("completion_tokens", 0),
                   "total_tokens": usage.get("total_tokens", 0)} if usage else None,
            finish_reason=choice.get("finish_reason", "stop"),
        )


async def fetch_models(base_url: str, api_key: str = "",
                       extra_headers: Optional[Dict[str, str]] = None,
                       timeout: float = 10.0) -> List[str]:
    """GET {base}/models -> list of ids. Raises on failure (caller surfaces message)."""
    import httpx
    headers = {"Authorization": f"Bearer {api_key or 'not-needed'}"}
    headers.update(extra_headers or {})
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(f"{base_url.rstrip('/')}/models", headers=headers)
        r.raise_for_status()
        data = r.json()
    items = data.get("data", data if isinstance(data, list) else [])
    return [m["id"] for m in items if isinstance(m, dict) and m.get("id")]


async def detect_ollama(candidates: Optional[List[str]] = None) -> Optional[str]:
    """Return first reachable Ollama-compatible base URL, else None."""
    import httpx
    for base in candidates or ["http://localhost:11434", "http://127.0.0.1:11434",
                               "http://host.docker.internal:11434"]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{base}/api/tags")
                if r.status_code == 200:
                    return base
        except Exception:
            continue
    return None
