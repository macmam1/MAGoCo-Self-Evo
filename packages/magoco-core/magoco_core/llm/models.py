"""LLM Models and Pricing for Smart Gateway."""
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class ModelTier(IntEnum):
    """Model tiers for cost optimization (lower = cheaper/faster)."""
    FREE = 0        # Free models (Groq, free tiers, local)
    ECONOMY = 1     # Very cheap (e.g., gpt-4o-mini, claude-3-haiku)
    STANDARD = 2    # Balanced (e.g., gpt-4o, claude-3.5-sonnet)
    PREMIUM = 3     # Highest capability (e.g., gpt-4-turbo, opus)
    UNKNOWN = 4     # Fallback


@dataclass
class ModelPricing:
    """Pricing information for a model."""
    input_price_per_million: float  # USD per 1M input tokens
    output_price_per_million: float  # USD per 1M output tokens
    tier: ModelTier = ModelTier.UNKNOWN
    context_window: int = 4096
    supports_tools: bool = True
    supports_vision: bool = False
    provider_name: str = "unknown"


# Predefined model pricing (update periodically)
MODEL_PRICING: dict[str, ModelPricing] = {
    # OpenAI
    "gpt-4o": ModelPricing(2.50, 10.00, ModelTier.STANDARD, 128000, True, True, "openai"),
    "gpt-4o-mini": ModelPricing(0.15, 0.60, ModelTier.ECONOMY, 128000, True, True, "openai"),
    "gpt-4-turbo": ModelPricing(10.00, 30.00, ModelTier.PREMIUM, 128000, True, True, "openai"),
    "gpt-3.5-turbo": ModelPricing(0.50, 1.50, ModelTier.ECONOMY, 16384, True, False, "openai"),
    "o1-preview": ModelPricing(15.00, 60.00, ModelTier.PREMIUM, 128000, True, False, "openai"),
    "o1-mini": ModelPricing(3.00, 12.00, ModelTier.STANDARD, 128000, True, False, "openai"),

    # Anthropic
    "claude-3.5-sonnet": ModelPricing(3.00, 15.00, ModelTier.STANDARD, 200000, True, True, "anthropic"),
    "claude-3.5-haiku": ModelPricing(1.00, 5.00, ModelTier.ECONOMY, 200000, True, True, "anthropic"),
    "claude-3-opus": ModelPricing(15.00, 75.00, ModelTier.PREMIUM, 200000, True, True, "anthropic"),

    # Google
    "gemini-1.5-pro": ModelPricing(3.50, 10.50, ModelTier.STANDARD, 2000000, True, True, "google"),
    "gemini-1.5-flash": ModelPricing(0.35, 1.05, ModelTier.ECONOMY, 2000000, True, True, "google"),

    # Free/Local (estimated/zero cost)
    "llama3.1:8b": ModelPricing(0.0, 0.0, ModelTier.FREE, 128000, True, False, "ollama"),
    "llama3.1:70b": ModelPricing(0.0, 0.0, ModelTier.FREE, 128000, True, False, "ollama"),
    "qwen2.5:72b": ModelPricing(0.0, 0.0, ModelTier.FREE, 128000, True, False, "ollama"),
    "mistral:7b": ModelPricing(0.0, 0.0, ModelTier.FREE, 32768, True, False, "ollama"),
    "mixtral:8x7b": ModelPricing(0.0, 0.0, ModelTier.FREE, 32768, True, False, "ollama"),

    # Groq (Free tier)
    "llama-3.1-70b-versatile": ModelPricing(0.0, 0.0, ModelTier.FREE, 128000, True, False, "groq"),
    "llama-3.1-8b-instant": ModelPricing(0.0, 0.0, ModelTier.FREE, 128000, True, False, "groq"),
    "mixtral-8x7b-32768": ModelPricing(0.0, 0.0, ModelTier.FREE, 32768, True, False, "groq"),
    "gemma2-9b-it": ModelPricing(0.0, 0.0, ModelTier.FREE, 8192, True, False, "groq"),
}

# Aliases for fuzzy matching
MODEL_ALIASES = {
    "gpt4o": "gpt-4o",
    "gpt4omini": "gpt-4o-mini",
    "sonnet": "claude-3.5-sonnet",
    "haiku": "claude-3.5-haiku",
    "opus": "claude-3-opus",
    "gemini-pro": "gemini-1.5-pro",
    "gemini-flash": "gemini-1.5-flash",
}


def get_model_pricing(model_name: str) -> Optional[ModelPricing]:
    """Get pricing info for a model, with fuzzy matching."""
    # Exact match
    if model_name in MODEL_PRICING:
        return MODEL_PRICING[model_name]

    # Fuzzy match via aliases
    normalized = model_name.lower().replace("-", "").replace("_", "").replace(".", "")
    if normalized in MODEL_ALIASES:
        return MODEL_PRICING[MODEL_ALIASES[normalized]]

    # Partial match
    for key, pricing in MODEL_PRICING.items():
        if key in model_name.lower() or model_name.lower() in key:
            return pricing

    return None