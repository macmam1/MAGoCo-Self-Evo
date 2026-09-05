"""LLM Models and Pricing for Smart Gateway."""
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, List


class ModelTier(IntEnum):
    """Model tiers for cost optimization (lower = cheaper/faster)."""
    FREE = 0        # Free models (Groq, free tiers, local)
    ECONOMY = 1     # Very cheap (e.g., gpt-4o-mini, claude-3-haiku)
    STANDARD = 2    # Balanced (e.g., gpt-4o, claude-3.5-sonnet)
    PREMIUM = 3     # Highest capability (e.g., gpt-4-turbo, opus)
    UNKNOWN = 4     # Fallback


class ModelCapability(str, Enum):
    """Model capabilities for smart routing."""
    CODING = "coding"           # Strong at code generation/analysis
    REASONING = "reasoning"     # Strong at complex reasoning/math
    FAST = "fast"               # Low latency, high throughput
    VISION = "vision"           # Supports image input
    LONG_CONTEXT = "long_context"  # 100k+ context window
    TOOL_USE = "tool_use"       # Strong function calling
    CREATIVE = "creative"       # Good at writing/creative tasks
    ANALYSIS = "analysis"       # Good at data analysis
    MULTILINGUAL = "multilingual"  # Strong non-English support


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
    capabilities: List[ModelCapability] = field(default_factory=list)


# Predefined model pricing (update periodically)
MODEL_PRICING: dict[str, ModelPricing] = {
    # OpenAI
    "gpt-4o": ModelPricing(2.50, 10.00, ModelTier.STANDARD, 128000, True, True, "openai", 
                           [ModelCapability.CODING, ModelCapability.REASONING, ModelCapability.VISION, ModelCapability.TOOL_USE, ModelCapability.LONG_CONTEXT]),
    "gpt-4o-mini": ModelPricing(0.15, 0.60, ModelTier.ECONOMY, 128000, True, True, "openai",
                                [ModelCapability.CODING, ModelCapability.FAST, ModelCapability.VISION, ModelCapability.TOOL_USE, ModelCapability.LONG_CONTEXT]),
    "gpt-4-turbo": ModelPricing(10.00, 30.00, ModelTier.PREMIUM, 128000, True, True, "openai",
                                [ModelCapability.CODING, ModelCapability.REASONING, ModelCapability.VISION, ModelCapability.TOOL_USE]),
    "gpt-3.5-turbo": ModelPricing(0.50, 1.50, ModelTier.ECONOMY, 16384, True, False, "openai",
                                  [ModelCapability.FAST, ModelCapability.TOOL_USE]),
    "o1-preview": ModelPricing(15.00, 60.00, ModelTier.PREMIUM, 128000, True, False, "openai",
                               [ModelCapability.REASONING, ModelCapability.CODING]),
    "o1-mini": ModelPricing(3.00, 12.00, ModelTier.STANDARD, 128000, True, False, "openai",
                            [ModelCapability.REASONING, ModelCapability.CODING, ModelCapability.FAST]),

    # Anthropic
    "claude-3.5-sonnet": ModelPricing(3.00, 15.00, ModelTier.STANDARD, 200000, True, True, "anthropic",
                                      [ModelCapability.CODING, ModelCapability.REASONING, ModelCapability.VISION, ModelCapability.TOOL_USE, ModelCapability.LONG_CONTEXT]),
    "claude-3.5-haiku": ModelPricing(1.00, 5.00, ModelTier.ECONOMY, 200000, True, True, "anthropic",
                                     [ModelCapability.FAST, ModelCapability.CODING, ModelCapability.VISION, ModelCapability.TOOL_USE, ModelCapability.LONG_CONTEXT]),
    "claude-3-opus": ModelPricing(15.00, 75.00, ModelTier.PREMIUM, 200000, True, True, "anthropic",
                                  [ModelCapability.REASONING, ModelCapability.CODING, ModelCapability.VISION, ModelCapability.TOOL_USE, ModelCapability.LONG_CONTEXT]),

    # Google
    "gemini-1.5-pro": ModelPricing(3.50, 10.50, ModelTier.STANDARD, 2000000, True, True, "google",
                                   [ModelCapability.REASONING, ModelCapability.LONG_CONTEXT, ModelCapability.VISION, ModelCapability.TOOL_USE]),
    "gemini-1.5-flash": ModelPricing(0.35, 1.05, ModelTier.ECONOMY, 2000000, True, True, "google",
                                     [ModelCapability.FAST, ModelCapability.LONG_CONTEXT, ModelCapability.VISION, ModelCapability.TOOL_USE]),

    # Free/Local (estimated/zero cost)
    "llama3.1:8b": ModelPricing(0.0, 0.0, ModelTier.FREE, 128000, True, False, "ollama",
                                [ModelCapability.FAST, ModelCapability.CODING, ModelCapability.MULTILINGUAL]),
    "llama3.1:70b": ModelPricing(0.0, 0.0, ModelTier.FREE, 128000, True, False, "ollama",
                                 [ModelCapability.CODING, ModelCapability.REASONING, ModelCapability.MULTILINGUAL]),
    "qwen2.5:72b": ModelPricing(0.0, 0.0, ModelTier.FREE, 128000, True, False, "ollama",
                                [ModelCapability.CODING, ModelCapability.REASONING, ModelCapability.MULTILINGUAL]),
    "mistral:7b": ModelPricing(0.0, 0.0, ModelTier.FREE, 32768, True, False, "ollama",
                               [ModelCapability.FAST, ModelCapability.MULTILINGUAL]),
    "mixtral:8x7b": ModelPricing(0.0, 0.0, ModelTier.FREE, 32768, True, False, "ollama",
                                 [ModelCapability.REASONING, ModelCapability.MULTILINGUAL]),

    # Groq (Free tier)
    "llama-3.1-70b-versatile": ModelPricing(0.0, 0.0, ModelTier.FREE, 128000, True, False, "groq",
                                            [ModelCapability.FAST, ModelCapability.CODING, ModelCapability.REASONING]),
    "llama-3.1-8b-instant": ModelPricing(0.0, 0.0, ModelTier.FREE, 128000, True, False, "groq",
                                         [ModelCapability.FAST, ModelCapability.CODING]),
    "mixtral-8x7b-32768": ModelPricing(0.0, 0.0, ModelTier.FREE, 32768, True, False, "groq",
                                       [ModelCapability.REASONING, ModelCapability.FAST]),
    "gemma2-9b-it": ModelPricing(0.0, 0.0, ModelTier.FREE, 8192, True, False, "groq",
                                 [ModelCapability.FAST, ModelCapability.MULTILINGUAL]),
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


def find_models_by_capability(capability: ModelCapability, max_tier: ModelTier = ModelTier.PREMIUM) -> List[str]:
    """Find models that have a specific capability, filtered by max tier."""
    models = []
    for name, pricing in MODEL_PRICING.items():
        if capability in pricing.capabilities and pricing.tier <= max_tier:
            models.append(name)
    # Sort by tier (cheaper/better first)
    models.sort(key=lambda m: MODEL_PRICING[m].tier)
    return models


def get_best_model_for_task(task_type: str, max_tier: ModelTier = ModelTier.PREMIUM) -> Optional[str]:
    """Get the best model for a specific task type."""
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
    models = find_models_by_capability(cap, max_tier)
    return models[0] if models else None