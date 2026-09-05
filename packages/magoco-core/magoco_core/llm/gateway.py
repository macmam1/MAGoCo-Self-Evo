"""LLM Provider Base Class and Gateway.

Supports: OpenAI (API), Ollama (Local), Anthropic, HuggingFace.
Auto-fallback, streaming, retry logic.
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from asyncio import Lock
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from magoco_core.core.config import settings
from magoco_core.llm.models import ModelPricing, ModelTier, get_model_pricing

logger = logging.getLogger(__name__)


@dataclass
class LLMMessage:
    role: str  # "system", "user", "assistant", "tool"
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
        }


@dataclass
class LLMResponse:
    content: str
    model: str = ""  # Track which model was used
    tool_calls: Optional[List[Dict]] = None
    usage: Optional[Dict[str, int]] = None
    finish_reason: str = "stop"
    cached: bool = False  # New: indicates if the response was from cache


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

    def get_model_pricing(self, model_name: str) -> Optional[ModelPricing]:
        """Returns pricing info for a specific model."""
        # Placeholder for now, to be implemented by concrete providers
        return None


@dataclass
class CacheEntry:
    response: LLMResponse
    timestamp: float
    # New: add cache invalidation logic, e.g., TTL


class LLMGateway:
    """Gateway managing multiple providers with auto-fallback, caching, and cost optimization."""

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.preferred_order: List[str] = []
        self._cache: Dict[str, CacheEntry] = {}  # In-memory cache
        self._lock = Lock()
        self._cost_lock = Lock()  # For cost-related operations
        self.usage_costs: Dict[str, float] = {}  # Tracks costs per provider


    def register(self, provider: LLMProvider):
        self.providers[provider.name] = provider
        if provider.name not in self.preferred_order:
            self.preferred_order.append(provider.name)
        self.usage_costs[provider.name] = 0.0 # Initialize cost

    def _generate_cache_key(self, messages: List[LLMMessage], **kwargs) -> str:
        # Create a deterministic key from messages and kwargs
        # Exclude non-deterministic items like temperature if caching is strict
        data = {"messages": [m.to_dict() for m in messages], "kwargs": kwargs}
        return hashlib.md5(json.dumps(data, sort_keys=True).encode("utf-8")).hexdigest()

    async def _get_from_cache(self, key: str) -> Optional[LLMResponse]:
        entry = self._cache.get(key)
        if entry and (time.time() - entry.timestamp < settings.LLM_CACHE_TTL_SECONDS):
            logger.info(f"Cache hit for key: {key}")
            response = entry.response
            response.cached = True
            return response
        return None

    async def _set_to_cache(self, key: str, response: LLMResponse):
        self._cache[key] = CacheEntry(response=response, timestamp=time.time())
        logger.info(f"Cache set for key: {key}")

    async def _update_costs(self, provider_name: str, response: LLMResponse):
        model_name = response.model if hasattr(response, 'model') else kwargs.get("model", "unknown")
        pricing = get_model_pricing(model_name)
        if pricing and response.usage:
            input_cost = (response.usage.get("prompt_tokens", 0) / 1_000_000) * pricing.input_price_per_million
            output_cost = (response.usage.get("completion_tokens", 0) / 1_000_000) * pricing.output_price_per_million
            total_cost = input_cost + output_cost
            async with self._cost_lock:
                self.usage_costs[provider_name] += total_cost
            logger.debug(f"Updated cost for {provider_name}: +${total_cost:.4f}, total: ${self.usage_costs[provider_name]:.4f}")


    async def complete(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Try providers in preferred order until one succeeds, with caching and cost optimization."""
        cache_key = self._generate_cache_key(messages, **kwargs)
        if settings.LLM_CACHE_ENABLED:
            cached_response = await self._get_from_cache(cache_key)
            if cached_response:
                return cached_response

        last_error = None
        # Order providers dynamically based on cost, availability, or preferences
        # For now, stick to preferred_order but consider cost/tier
        
        # New: Basic cost-aware provider selection (prioritize cheaper tiers)
        model_hint = kwargs.get("model", "")
        sorted_providers = sorted(
            self.preferred_order,
            key=lambda p_name: (
                get_model_pricing(model_hint).tier.value
                if get_model_pricing(model_hint)
                else ModelTier.PREMIUM.value
            )
        )

        for provider_name in sorted_providers: # Use sorted providers
            provider = self.providers.get(provider_name)
            if provider is None:
                continue
            if not await provider.is_available(): # Check availability first
                logger.warning(f"[LLM Gateway] {provider.name} not available, skipping.")
                continue

            try:
                response = await provider.complete(messages, **kwargs)
                if settings.LLM_CACHE_ENABLED:
                    await self._set_to_cache(cache_key, response)
                await self._update_costs(provider_name, response) # Update costs
                return response
            except Exception as e:
                last_error = e
                logger.error(f"[LLM Gateway] {provider.name} failed: {e}, trying next...", exc_info=True)
                continue

        raise RuntimeError(f"No LLM provider available after trying all. Last error: {last_error}")

    def get_available_models(self) -> List[str]:
        models = []
        for p in self.providers.values():
            models.extend(p.models)
        return models

    def get_current_costs(self) -> Dict[str, float]:
        return self.usage_costs


# Global gateway instance
llm_gateway = LLMGateway()

