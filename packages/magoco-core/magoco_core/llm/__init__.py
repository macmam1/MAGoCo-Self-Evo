"""LLM module — providers and gateway."""

from magoco_core.llm.gateway import LLMGateway, LLMProvider, LLMMessage, LLMResponse, llm_gateway
from magoco_core.llm.openai_provider import OpenAIProvider
from magoco_core.llm.ollama_provider import OllamaProvider
from magoco_core.llm.providers import (
    ProviderKind, ProviderConfig, CompatibleProvider, fetch_models, detect_ollama,
)
from magoco_core.llm.vault import encrypt_secret, decrypt_secret
from magoco_core.llm.registry import get_provider_registry

__all__ = [
    "LLMGateway",
    "LLMProvider",
    "LLMMessage",
    "LLMResponse",
    "llm_gateway",
    "OpenAIProvider",
    "OllamaProvider",
    "ProviderKind",
    "ProviderConfig",
    "CompatibleProvider",
    "fetch_models",
    "detect_ollama",
    "encrypt_secret",
    "decrypt_secret",
    "ModelTier",
    "ModelCapability",
    "ModelPricing",
    "get_model_pricing",
    "find_models_by_capability",
    "get_best_model_for_task",
]


def init_llm():
    """Initialize LLM gateway with available providers."""
    if OpenAIProvider().is_available():
        llm_gateway.register(OpenAIProvider())
    if OllamaProvider().is_available():
        llm_gateway.register(OllamaProvider())
    return llm_gateway


async def register_user_providers():
    """Register user-configured providers from the registry."""
    try:
        reg = get_provider_registry()
        configs = reg.list(enabled_only=True)
        for cfg in configs:
            if cfg.kind == ProviderKind.OPENAI_COMPATIBLE:
                provider = CompatibleProvider(
                    base_url=cfg.base_url,
                    api_key=reg.decrypt_key(cfg),
                    name=cfg.id,
                    models=cfg.models,
                    timeout=cfg.timeout,
                    extra_headers=cfg.extra_headers,
                )
                llm_gateway.register(provider)
    except Exception as e:
        # Registry might not be initialized yet
        pass