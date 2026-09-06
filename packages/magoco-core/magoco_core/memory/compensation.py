"""Model Capability Compensator — covers weak/medium model memory gaps.

Idea: the OS, not the model, owns memory discipline.
- Weak models: explicit everything — core blocks injected verbatim, distilled facts,
  step-by-step reminders, smaller window + summary, verification checklist.
- Medium: balanced — summary + scoped recall.
- Strong: lean — minimal injection, trust reasoning.

Profiles are data (flexible), not hardcoded branches: tune per deployment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from magoco_core.llm.models import ModelTier, get_model_pricing


@dataclass
class CompensationProfile:
    tier: ModelTier
    inject_core_blocks: bool = True
    max_core_chars: int = 2000
    inject_distilled_facts: int = 5
    inject_rolling_summary: bool = True
    window_size: int = 12
    add_step_reminder: bool = True
    add_verification: bool = True
    explicit_tool_hints: bool = True


PROFILES: Dict[ModelTier, CompensationProfile] = {
    # Weak/small/local: compensate heavily
    ModelTier.FREE: CompensationProfile(
        tier=ModelTier.FREE, max_core_chars=3000, inject_distilled_facts=8,
        window_size=8, add_step_reminder=True, add_verification=True,
        explicit_tool_hints=True,
    ),
    ModelTier.ECONOMY: CompensationProfile(
        tier=ModelTier.ECONOMY, max_core_chars=2000, inject_distilled_facts=5,
        window_size=12, add_step_reminder=True, add_verification=True,
        explicit_tool_hints=True,
    ),
    ModelTier.STANDARD: CompensationProfile(
        tier=ModelTier.STANDARD, max_core_chars=1200, inject_distilled_facts=3,
        window_size=16, add_step_reminder=False, add_verification=False,
        explicit_tool_hints=False,
    ),
    ModelTier.PREMIUM: CompensationProfile(
        tier=ModelTier.PREMIUM, max_core_chars=600, inject_distilled_facts=2,
        window_size=20, add_step_reminder=False, add_verification=False,
        explicit_tool_hints=False,
    ),
    ModelTier.UNKNOWN: CompensationProfile(tier=ModelTier.UNKNOWN),
}


MODEL_OVERRIDES: Dict[str, CompensationProfile] = {}
"""Per-model tunable overrides (flexible: user/deployment can specialize one model)."""


def register_model_override(model_name: str, profile: CompensationProfile) -> None:
    """Register or replace a per-model compensation profile."""
    MODEL_OVERRIDES[model_name] = profile


def profile_for_model(model_name: str) -> CompensationProfile:
    if model_name in MODEL_OVERRIDES:
        return MODEL_OVERRIDES[model_name]
    pricing = get_model_pricing(model_name or "")
    tier = pricing.tier if pricing else ModelTier.UNKNOWN
    return PROFILES.get(tier, PROFILES[ModelTier.UNKNOWN])


def detect_capability_gaps(model_name: str, task_needs: List[str]) -> List[str]:
    """Which task-needed capabilities does this model lack? (explicit, no guessing).

    task_needs: e.g. ["tool_use", "vision", "long_context", "multilingual"].
    Uses the pricing/capability table; unknown model => all needs reported as gaps.
    """
    from magoco_core.llm.models import ModelCapability
    pricing = get_model_pricing(model_name or "")
    if not pricing:
        return list(task_needs)
    have = {c.value if isinstance(c, ModelCapability) else str(c) for c in (pricing.capabilities or [])}
    # supports_tools/supports_vision flags are authoritative for those two
    if pricing.supports_tools:
        have.add("tool_use")
    if pricing.supports_vision:
        have.add("vision")
    return [n for n in task_needs if n not in have]


def _budget_for_model(model_name: str, fraction: float = 0.15) -> int:
    """Max preamble chars as a fraction of the model's context window."""
    pricing = get_model_pricing(model_name or "")
    window = pricing.context_window if pricing and pricing.context_window else 8192
    return max(800, int(window * fraction))


# ---------- Escalation policy (weak tries first, cost-aware) ----------

ESCALATION_LADDER: List[ModelTier] = [
    ModelTier.FREE, ModelTier.ECONOMY, ModelTier.STANDARD, ModelTier.PREMIUM,
]


def next_stronger_tier(tier: ModelTier) -> Optional[ModelTier]:
    """Next rung up the cost ladder, or None if already top."""
    try:
        i = ESCALATION_LADDER.index(tier)
    except ValueError:
        return ModelTier.ECONOMY
    return ESCALATION_LADDER[i + 1] if i + 1 < len(ESCALATION_LADDER) else None


def should_escalate(error: str = "", confidence: float = 1.0,
                    attempts: int = 1, max_attempts: int = 2) -> Dict[str, Any]:
    """Rule-based escalation decision (explicit, auditable).

    Escalate when: tool/JSON failure signals, low confidence, or attempts exhausted.
    Never loops forever: capped by max_attempts.
    """
    err = (error or "").lower()
    failure_signals = ["tool", "json", "parse", "timeout", "format", "schema",
                       "function", "invalid", "failed"]
    hit = any(s in err for s in failure_signals)
    if attempts >= max_attempts or hit or confidence < 0.4:
        return {"escalate": True,
                "reason": "attempts-exhausted" if attempts >= max_attempts
                else ("low-confidence" if confidence < 0.4 else "failure-signal")}
    return {"escalate": False, "reason": "retry-same-tier"}


def json_contract(schema_desc: str, example: str = "") -> str:
    """Strict JSON contract for weak models (schema + repair rule)."""
    ex = f"\nExample:\n{example}" if example else ""
    return (
        "OUTPUT CONTRACT (must follow exactly):\n"
        f"Return ONLY valid JSON matching: {schema_desc}{ex}\n"
        "Rules: no prose outside JSON, no trailing commas, quote all keys. "
        "If you cannot comply, return {\"error\": \"<reason>\"} instead of guessing."
    )


def record_model_failure(model_name: str, task_type: str, error: str) -> str:
    """Persist a model failure as semantic memory for routing feedback."""
    from magoco_core.memory.models import MemoryEntry, MemoryType, MemoryScope
    from magoco_core.memory.store import get_memory_store
    store = get_memory_store()
    entry = MemoryEntry(
        type=MemoryType.SEMANTIC, scope=MemoryScope.GLOBAL,
        content=f"Model failure: {model_name} on {task_type}: {error[:300]}",
        importance=0.6, source="os-feedback",
        tags={"model-feedback", "failure", task_type, model_name},
        metadata={"model": model_name, "task_type": task_type},
    )
    return store.add(entry)


def build_augmented_context(
    model_name: str,
    core_blocks: List[Dict[str, str]] | None = None,
    distilled_facts: List[str] | None = None,
    rolling_summary: str = "",
    task_hint: str = "",
    task_needs: List[str] | None = None,
    max_preamble_chars: Optional[int] = None,
) -> Dict[str, Any]:
    """Build the memory preamble the OS injects for a given model strength.

    Budget-aware: total preamble capped to a fraction of the model's context
    window so heavy compensation never overflows weak/small-context models.
    """
    prof = profile_for_model(model_name)
    budget = max_preamble_chars or _budget_for_model(model_name)
    parts: List[str] = []

    gaps = detect_capability_gaps(model_name, task_needs or [])

    if prof.inject_core_blocks and core_blocks:
        total = 0
        block_lines = []
        for b in core_blocks:
            chunk = f"[{b.get('label')}]: {b.get('content', '')}"
            if total + len(chunk) > prof.max_core_chars:
                break
            block_lines.append(chunk)
            total += len(chunk)
        if block_lines:
            parts.append("CORE FACTS (always true, do not re-ask):\n" + "\n".join(block_lines))

    if distilled_facts and prof.inject_distilled_facts > 0:
        facts = distilled_facts[: prof.inject_distilled_facts]
        parts.append("RELEVANT PAST LEARNINGS:\n" + "\n".join(f"- {f}" for f in facts))

    if prof.inject_rolling_summary and rolling_summary:
        parts.append(f"CONVERSATION SO FAR (summary, don't lose it):\n{rolling_summary[-1200:]}")

    if gaps:
        parts.append(
            "MODEL LIMITS (compensate explicitly): lacking "
            + ", ".join(gaps)
            + " — break the task into smaller steps, ask for missing info instead of assuming."
        )
    if prof.add_step_reminder:
        parts.append(
            "PROCEDURE: 1) restate the goal in one line 2) list needed facts "
            "3) act with tools 4) verify result before answering."
        )
    if prof.add_verification:
        parts.append(
            "VERIFY BEFORE ANSWERING: quote the fact you used + its source "
            "(core/archival/history). If unsure, say so instead of guessing."
        )
    if prof.explicit_tool_hints and task_hint:
        parts.append(f"CURRENT TASK: {task_hint}")

    preamble = "\n\n".join(parts)
    truncated = False
    if len(preamble) > budget:
        # Keep head (core facts) + tail (procedure/verification); cut the middle
        head = preamble[: budget - 400]
        tail = preamble[-400:]
        preamble = head + "\n\n[... trimmed by OS memory budget ...]\n\n" + tail
        truncated = True

    return {
        "model": model_name or "auto",
        "tier": prof.tier.name,
        "preamble": preamble,
        "preamble_chars": len(preamble),
        "budget_chars": budget,
        "truncated": truncated,
        "capability_gaps": gaps,
        "window_size": prof.window_size,
    }
