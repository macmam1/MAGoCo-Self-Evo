"""LLM Provider Base Class and Gateway.

Supports: OpenAI (API), Ollama (Local), Anthropic, HuggingFace.
Auto-fallback, streaming, retry logic.
Rate limiting, fallback chain tracking, cost optimization.
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from asyncio import Lock
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from magoco_core.core.config import settings
from magoco_core.llm.models import ModelPricing, ModelTier, ModelCapability, get_model_pricing, find_models_by_capability, get_best_model_for_task

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

    def get_model_pricing(self, model_name: str) -> Optional["ModelPricing"]:
        """Returns pricing info for a specific model."""
        # Placeholder for now, to be implemented by concrete providers
        return None


@dataclass
class CacheEntry:
    response: LLMResponse
    timestamp: float
    # New: add cache invalidation logic, e.g., TTL


@dataclass
class RateLimitConfig:
    """Rate limiting configuration for a provider."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    tokens_per_minute: int = 100000
    burst_allowance: int = 10


@dataclass
class RateLimitState:
    """Current rate limit state for a provider."""
    minute_requests: deque = field(default_factory=lambda: deque(maxlen=100))
    hour_requests: deque = field(default_factory=lambda: deque(maxlen=10000))
    minute_tokens: deque = field(default_factory=lambda: deque(maxlen=10000))
    blocked_until: Optional[float] = None
    consecutive_failures: int = 0
    last_success: Optional[float] = None
    total_requests: int = 0
    total_tokens: int = 0


@dataclass
class FallbackAttempt:
    """Record of a fallback attempt."""
    provider_name: str
    model: str
    timestamp: datetime
    success: bool
    error: Optional[str] = None
    latency_ms: Optional[float] = None


@dataclass
class FallbackChain:
    """Tracks the fallback chain for a request."""
    original_provider: str
    original_model: str
    attempts: List["FallbackAttempt"] = field(default_factory=list)
    final_success: bool = False
    final_provider: Optional[str] = None
    final_model: Optional[str] = None
    total_latency_ms: float = 0.0


class LLMGateway:
    """Gateway managing multiple providers with auto-fallback, caching, cost optimization,
    rate limiting, and fallback chain tracking."""

    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.preferred_order: List[str] = []
        self._cache: Dict[str, CacheEntry] = {}  # In-memory cache
        self._lock = Lock()
        self._cost_lock = Lock()  # For cost-related operations
        self.usage_costs: Dict[str, float] = {}  # Tracks costs per provider
        
        # Rate limiting
        self._rate_limit_configs: Dict[str, RateLimitConfig] = {}
        self._rate_limit_states: Dict[str, RateLimitState] = {}
        
        # Fallback chain tracking
        self.fallback_chains: List["FallbackChain"] = []
        self._max_fallback_chains = 100  # Keep last 100 chains
        
        # Default rate limits per provider
        self._default_rate_limits = {
            "openai": RateLimitConfig(requests_per_minute=500, requests_per_hour=10000, tokens_per_minute=200000),
            "anthropic": RateLimitConfig(requests_per_minute=100, requests_per_hour=2000, tokens_per_minute=100000),
            "google": RateLimitConfig(requests_per_minute=60, requests_per_hour=1500, tokens_per_minute=150000),
            "ollama": RateLimitConfig(requests_per_minute=30, requests_per_hour=1000, tokens_per_minute=50000),
            "custom": RateLimitConfig(requests_per_minute=100, requests_per_hour=2000, tokens_per_minute=100000),
        }

    def register(self, provider: "LLMProvider"):
        self.providers[provider.name] = provider
        if provider.name not in self.preferred_order:
            self.preferred_order.append(provider.name)
        self.usage_costs[provider.name] = 0.0  # Initialize cost
        
        # Initialize rate limit state
        config = self._default_rate_limits.get(provider.name, RateLimitConfig())
        self._rate_limit_configs[provider.name] = config
        self._rate_limit_states[provider.name] = RateLimitState()

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
        model_name = response.model if hasattr(response, 'model') else "unknown"
        pricing = get_model_pricing(model_name)
        if pricing and response.usage:
            input_cost = (response.usage.get("prompt_tokens", 0) / 1_000_000) * pricing.input_price_per_million
            output_cost = (response.usage.get("completion_tokens", 0) / 1_000_000) * pricing.output_price_per_million
            total_cost = input_cost + output_cost
            async with self._cost_lock:
                self.usage_costs[provider_name] += total_cost
            logger.debug(f"Updated cost for {provider_name}: +${total_cost:.4f}, total: ${self.usage_costs[provider_name]:.4f}")

    def _check_rate_limit(self, provider_name: str, estimated_tokens: int = 0) -> Tuple[bool, Optional[str]]:
        """Check if request is within rate limits. Returns (allowed, error_message)."""
        now = time.time()
        state = self._rate_limit_states.get(provider_name, RateLimitState())
        config = self._rate_limit_configs.get(provider_name, RateLimitConfig())
        
        # Check if blocked
        if state.blocked_until and now < state.blocked_until:
            return False, f"Rate limited until {datetime.fromtimestamp(state.blocked_until).isoformat()}"
        
        # Clean old requests
        cutoff_minute = now - 60
        while state.minute_requests and state.minute_requests[0] < cutoff_minute:
            state.minute_requests.popleft()
        
        cutoff_hour = now - 3600
        while state.hour_requests and state.hour_requests[0] < cutoff_hour:
            state.hour_requests.popleft()
        
        # Check limits
        if len(state.minute_requests) >= config.requests_per_minute:
            return False, f"Rate limit exceeded: {config.requests_per_minute} req/min"
        
        if len(state.hour_requests) >= config.requests_per_hour:
            return False, f"Rate limit exceeded: {config.requests_per_hour} req/hour"
        
        if estimated_tokens and config.tokens_per_minute:
            # Estimate tokens per minute
            recent_tokens = sum(state.minute_tokens) if state.minute_tokens else 0
            if recent_tokens + estimated_tokens > config.tokens_per_minute:
                return False, f"Token rate limit exceeded: {config.tokens_per_minute} tokens/min"
        
        return True, None

    def _record_request(self, provider_name: str, tokens: int = 0):
        """Record a successful request for rate limiting."""
        now = time.time()
        state = self._rate_limit_states.get(provider_name, RateLimitState())
        state.minute_requests.append(now)
        state.hour_requests.append(now)
        if tokens:
            state.minute_tokens.append(tokens)
        state.total_requests += 1
        state.total_tokens += tokens
        state.last_success = now
        state.consecutive_failures = 0

    def _record_failure(self, provider_name: str):
        """Record a failure for rate limiting."""
        state = self._rate_limit_states.get(provider_name, RateLimitState())
        state.consecutive_failures += 1
        # Exponential backoff on consecutive failures
        if state.consecutive_failures >= 3:
            state.blocked_until = time.time() + (2 ** min(state.consecutive_failures, 6)) * 5

    async def complete(self, messages: List[LLMMessage], **kwargs) -> LLMResponse:
        """Try providers in preferred order until one succeeds, with caching, cost optimization, rate limiting, and fallback chain tracking."""
        cache_key = self._generate_cache_key(messages, **kwargs)
        if settings.LLM_CACHE_ENABLED:
            cached_response = await self._get_from_cache(cache_key)
            if cached_response:
                return cached_response

        # Create fallback chain tracker
        original_model = kwargs.get("model", "")
        fallback_chain = FallbackChain(
            original_provider=self.preferred_order[0] if self.preferred_order else "unknown",
            original_model=original_model or "auto",
        )

        last_error = None
        # Order providers dynamically based on cost, availability, or preferences
        model_hint = kwargs.get("model", "")
        sorted_providers = sorted(
            self.preferred_order,
            key=lambda p_name: (
                get_model_pricing(model_hint).tier.value
                if get_model_pricing(model_hint)
                else ModelTier.PREMIUM.value
            )
        )

        for provider_name in sorted_providers:
            provider = self.providers.get(provider_name)
            if provider is None:
                continue
            if not await provider.is_available():
                logger.warning(f"[LLM Gateway] {provider.name} not available, skipping.")
                fallback_chain.attempts.append(FallbackAttempt(
                    provider_name=provider_name,
                    model=kwargs.get("model", ""),
                    timestamp=datetime.now(),
                    success=False,
                    error="Provider not available",
                ))
                continue

            # Check rate limit
            estimated_tokens = kwargs.get("max_tokens", 1000)  # rough estimate
            allowed, error = self._check_rate_limit(provider_name, estimated_tokens)
            if not allowed:
                logger.warning(f"[LLM Gateway] {provider.name} rate limited: {error}")
                fallback_chain.attempts.append(FallbackAttempt(
                    provider_name=provider_name,
                    model=kwargs.get("model", ""),
                    timestamp=datetime.now(),
                    success=False,
                    error=error,
                ))
                continue

            try:
                start_time = time.time()
                response = await provider.complete(messages, **kwargs)
                latency_ms = (time.time() - start_time) * 1000
                
                # Record success
                self._record_request(provider_name, response.usage.get("total_tokens", 0) if response.usage else 0)
                
                # Update fallback chain
                fallback_chain.attempts.append(FallbackAttempt(
                    provider_name=provider_name,
                    model=response.model or kwargs.get("model", ""),
                    timestamp=datetime.now(),
                    success=True,
                    latency_ms=latency_ms,
                ))
                fallback_chain.final_success = True
                fallback_chain.final_provider = provider_name
                fallback_chain.final_model = response.model
                fallback_chain.total_latency_ms = latency_ms
                
                if settings.LLM_CACHE_ENABLED:
                    await self._set_to_cache(cache_key, response)
                await self._update_costs(provider_name, response)
                
                return response
            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000 if 'start_time' in locals() else 0
                last_error = e
                
                # Record failure
                self._record_failure(provider_name)
                logger.error(f"[LLM Gateway] {provider.name} failed: {e}, trying next...", exc_info=True)
                
                # Update fallback chain
                fallback_chain.attempts.append(FallbackAttempt(
                    provider_name=provider_name,
                    model=kwargs.get("model", ""),
                    timestamp=datetime.now(),
                    success=False,
                    error=str(e),
                    latency_ms=latency_ms,
                ))
                continue

        # No provider succeeded
        fallback_chain.final_success = False
        self._add_fallback_chain(fallback_chain)
        raise RuntimeError(f"No LLM provider available after trying all. Last error: {last_error}")

    def _add_fallback_chain(self, chain: "FallbackChain"):
        """Add a fallback chain to history."""
        self.fallback_chains.append(chain)
        if len(self.fallback_chains) > self._max_fallback_chains:
            self.fallback_chains = self.fallback_chains[-self._max_fallback_chains:]

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
        model_name = response.model if hasattr(response, 'model') else "unknown"
        pricing = get_model_pricing(model_name)
        if pricing and response.usage:
            input_cost = (response.usage.get("prompt_tokens", 0) / 1_000_000) * pricing.input_price_per_million
            output_cost = (response.usage.get("completion_tokens", 0) / 1_000_000) * pricing.output_price_per_million
            total_cost = input_cost + output_cost
            async with self._cost_lock:
                self.usage_costs[provider_name] += total_cost
            logger.debug(f"Updated cost for {provider_name}: +${total_cost:.4f}, total: ${self.usage_costs[provider_name]:.4f}")

    def get_available_models(self) -> List[str]:
        models = []
        for p in self.providers.values():
            models.extend(p.models)
        return models

    def get_current_costs(self) -> Dict[str, float]:
        return self.usage_costs

    def get_rate_limit_status(self, provider_name: str) -> Dict[str, Any]:
        """Get current rate limit status for a provider."""
        state = self._rate_limit_states.get(provider_name)
        config = self._rate_limit_configs.get(provider_name)
        if not state or not config:
            return {"available": False}
        
        now = time.time()
        cutoff_minute = now - 60
        recent = len([r for r in state.minute_requests if r > cutoff_minute])
        
        return {
            "provider": provider_name,
            "requests_this_minute": recent,
            "max_per_minute": config.requests_per_minute,
            "requests_this_hour": len(state.hour_requests),
            "max_per_hour": config.requests_per_hour,
            "total_requests": state.total_requests,
            "total_tokens": state.total_tokens,
            "consecutive_failures": state.consecutive_failures,
            "blocked": state.blocked_until is not None and state.blocked_until > time.time(),
            "blocked_until": datetime.fromtimestamp(state.blocked_until).isoformat() if state.blocked_until else None,
        }

    def get_fallback_chains(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent fallback chains for monitoring."""
        chains = self.fallback_chains[-limit:]
        return [
            {
                "original_provider": c.original_provider,
                "original_model": c.original_model,
                "final_success": c.final_success,
                "final_provider": c.final_provider,
                "final_model": c.final_model,
                "total_latency_ms": c.total_latency_ms,
                "attempts": [
                    {
                        "provider": a.provider_name,
                        "model": a.model,
                        "success": a.success,
                        "error": a.error,
                        "latency_ms": a.latency_ms,
                    }
                    for a in c.attempts
                ],
            }
            for c in chains
        ]

    # Smart Routing Methods
    def select_model_for_task(self, task_type: str, max_tier: "ModelTier" = ModelTier.PREMIUM) -> Optional[str]:
        """Select the best model for a specific task type across all registered providers."""
        # First check predefined models
        best = get_best_model_for_task(task_type, max_tier)
        if best:
            # Verify this model is available in registered providers
            for provider in self.providers.values():
                if best in provider.models:
                    return best
        
        # Fallback: find any model with matching capability in registered providers
        capability_map = {
            "coding": ModelCapability.CODING,
            "reasoning": ModelCapability.REASONING,
            "fast": ModelCapability.FAST,
            "vision": ModelCapability.VISION,
            "long_context": ModelCapability.LONG_CONTEXT,
            "analysis": ModelCapability.ANALYSIS,
            "creative": ModelCapability.CREATIVE,
            "multilingual": ModelCapability.MULTILINGUAL,
        }
        cap = capability_map.get(task_type.lower())
        if not cap:
            return None
        
        # Check registered providers for models with this capability
        for provider in self.providers.values():
            for model in provider.models:
                pricing = get_model_pricing(model)
                if pricing and cap in pricing.capabilities and pricing.tier <= max_tier:
                    return model
        return None

    async def complete_with_smart_routing(self, messages: List[LLMMessage], 
                                           task_type: str = "general",
                                           max_tier: "ModelTier" = ModelTier.PREMIUM,
                                           **kwargs) -> LLMResponse:
        """Complete with automatic model selection based on task type."""
        # If model not explicitly specified, select best one for task
        if "model" not in kwargs or not kwargs["model"]:
            selected_model = self.select_model_for_task(task_type, max_tier)
            if selected_model:
                kwargs["model"] = selected_model
                logger.info(f"[Smart Gateway] Auto-selected model '{selected_model}' for task '{task_type}'")
        
        return await self.complete(messages, **kwargs)


# Global gateway instance
llm_gateway = LLMGateway()