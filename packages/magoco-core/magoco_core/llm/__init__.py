"""LLM module — providers and gateway."""

from magoco_core.llm.gateway import LLMGateway, LLMProvider, LLMMessage, LLMResponse, llm_gateway
from magoco_core.llm.openai_provider import OpenAIProvider
from magoco_core.llm.ollama_provider import OllamaProvider
from magoco_core.llm.providers import (
    ProviderKind, ProviderConfig, CompatibleProvider, fetch_models, detect_ollama,
)
from magoco_core.llm.vault import encrypt_secret, decrypt_secret

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
]

def init_llm():
    """Initialize LLM gateway with available providers."""
    if OpenAIProvider().is_available():
        llm_gateway.register(OpenAIProvider())
    if OllamaProvider().is_available():
        llm_gateway.register(OllamaProvider())
    return llm_gateway