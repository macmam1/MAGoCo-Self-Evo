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


def profile_for_model(model_name: str) -> CompensationProfile:
    pricing = get_model_pricing(model_name or "")
    tier = pricing.tier if pricing else ModelTier.UNKNOWN
    return PROFILES.get(tier, PROFILES[ModelTier.UNKNOWN])


def build_augmented_context(
    model_name: str,
    core_blocks: List[Dict[str, str]] | None = None,
    distilled_facts: List[str] | None = None,
    rolling_summary: str = "",
    task_hint: str = "",
) -> Dict[str, Any]:
    """Build the memory preamble the OS injects for a given model strength."""
    prof = profile_for_model(model_name)
    parts: List[str] = []

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

    return {
        "model": model_name or "auto",
        "tier": prof.tier.name,
        "preamble": "\n\n".join(parts),
        "window_size": prof.window_size,
    }
