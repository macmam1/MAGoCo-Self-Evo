"""LLM module — providers and gateway."""

from magoco_core.llm.gateway import LLMGateway, LLMProvider, LLMMessage, LLMResponse, llm_gateway
from magoco_core.llm.openai_provider import OpenAIProvider
from magoco_core.llm.ollama_provider import OllamaProvider

__all__ = [
    "LLMGateway",
    "LLMProvider",
    "LLMMessage",
    "LLMResponse",
    "llm_gateway",
    "OpenAIProvider",
    "OllamaProvider",
]

def init_llm():
    """Initialize LLM gateway with available providers."""
    if OpenAIProvider().is_available():
        llm_gateway.register(OpenAIProvider())
    if OllamaProvider().is_available():
        llm_gateway.register(OllamaProvider())
    return llm_gateway