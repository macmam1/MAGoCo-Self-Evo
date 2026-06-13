"""LLM Provider factory — auto-detect + create."""
from functools import lru_cache

from app.core.config import settings
from app.models.agent import LLMProvider as LLMProviderEnum
from app.services.llm.base import LLMProvider


@lru_cache(maxsize=1)
def _build_providers() -> dict[LLMProviderEnum, LLMProvider]:
    """ساخت همه provider های موجود."""
    from app.services.llm.anthropic_provider import AnthropicProvider
    from app.services.llm.hf_provider import HuggingFaceProvider
    from app.services.llm.ollama_provider import OllamaProvider
    from app.services.llm.openai_provider import OpenAIProvider

    providers: dict[LLMProviderEnum, LLMProvider] = {}

    if settings.OPENAI_API_KEY:
        providers[LLMProviderEnum.OPENAI] = OpenAIProvider()
    if settings.ANTHROPIC_API_KEY:
        providers[LLMProviderEnum.ANTHROPIC] = AnthropicProvider()
    if settings.HUGGINGFACE_API_KEY:
        providers[LLMProviderEnum.HUGGINGFACE] = HuggingFaceProvider()

    # Ollama همیشه (فرض می‌کنیم local در دسترسه)
    providers[LLMProviderEnum.OLLAMA] = OllamaProvider()

    return providers


def get_provider(name: LLMProviderEnum | str) -> LLMProvider:
    """دریافت provider با نام. اگه موجود نباشه، اولین provider در دسترس رو برمی‌گردونه."""
    if isinstance(name, str):
        try:
            name = LLMProviderEnum(name)
        except ValueError as e:
            raise ValueError(f"Unknown LLM provider: {name}") from e

    providers = _build_providers()
    if name in providers:
        return providers[name]

    # Fallback: اولین provider در دسترس
    if providers:
        return next(iter(providers.values()))

    raise RuntimeError("No LLM provider available. Set OPENAI_API_KEY or other provider keys.")


def list_available_providers() -> list[str]:
    """لیست provider های در دسترس."""
    return [p.name for p in _build_providers().values()]


def reset_cache() -> None:
    """Reset cache (برای تست یا تغییر env)."""
    _build_providers.cache_clear()
