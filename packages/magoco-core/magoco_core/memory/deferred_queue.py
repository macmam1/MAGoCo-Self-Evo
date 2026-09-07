"""Capability Gate + Deferred Queue — protects weak models from complex tasks.

Flow (only when enabled):
1. Estimate task complexity (0-3 scale ~ tiers).
2. Score model capability from tier + capability gaps.
3. If gap >= threshold -> DEFER: persist task to queue with reason, tell user plainly.
4. When a stronger model is available (or user approves), drain queue.

Safety:
- Global kill-switch: settings.DEFERRED_QUEUE_ENABLED (env: DEFERRED_QUEUE_ENABLED=false).
- Per-request override: enabled=False bypasses the gate entirely.
- Conservative default: only defers on LARGE gaps (>=2 tiers), never silently drops.
- Every deferred task is reviewable: list / approve-now / cancel.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from magoco_core.core.config import settings
from magoco_core.llm.models import ModelTier, get_model_pricing
from magoco_core.memory.compensation import detect_capability_gaps

TIER_SCORE = {
    ModelTier.FREE: 0,
    ModelTier.ECONOMY: 1,
    ModelTier.STANDARD: 2,
    ModelTier.PREMIUM: 3,
    ModelTier.UNKNOWN: 1,  # treat unknown as economy (cautious, not blind)
}

_COMPLEXITY_SIGNALS = [
    (r"\b(multi-?step|step[- ]by[- ]step|pipeline|orchestrat\w+|plan|architect)\b", 1),
    (r"\b(code|refactor|debug|implement|migrat\w+|algorithm)\b", 1),
    (r"\b(proof|theorem|math|reason|analy[sz]e deeply|compare|evaluate)\b", 1),
    (r"\b(tool|function|api|webhook|automat\w+|schedul\w+)\b", 1),
    (r"\b(long|entire|whole|all files|codebase|repo)\b", 1),
]


def estimate_complexity(task_text: str, task_needs: List[str] | None = None) -> Dict[str, Any]:
    """Heuristic 0-3 complexity score with transparent reasons."""
    text = task_text or ""
    score = 0
    reasons: List[str] = []
    if len(text) > 800:
        score += 1
        reasons.append("long-prompt")
    for pattern, weight in _COMPLEXITY_SIGNALS:
        if re.search(pattern, text, re.IGNORECASE):
            score += weight
            reasons.append(f"signal:{pattern[:24]}")
            if len(reasons) >= 4:
                break
    needs = task_needs or []
    if len(needs) >= 3:
        score += 1
        reasons.append("many-capability-needs")
    return {"score": min(3, score), "reasons": reasons}


def model_score(model_name: str, task_needs: List[str] | None = None) -> Dict[str, Any]:
    """Capability score 0-3 for a model, penalized by missing needs."""
    pricing = get_model_pricing(model_name or "")
    tier = pricing.tier if pricing else ModelTier.UNKNOWN
    base = TIER_SCORE.get(tier, 1)
    gaps = detect_capability_gaps(model_name, task_needs or [])
    penalized = max(0, base - (1 if gaps else 0))
    return {"score": penalized, "tier": tier.name, "gaps": gaps}


def gate_check(model_name: str, task_text: str,
               task_needs: List[str] | None = None,
               enabled: Optional[bool] = None,
               min_gap: Optional[int] = None) -> Dict[str, Any]:
    """Decide assign vs defer. Pure function — no side effects (testable)."""
    on = settings.DEFERRED_QUEUE_ENABLED if enabled is None else enabled
    if not on:
        return {"decision": "assign", "reason": "gate-disabled", "deferred": False}
    complexity = estimate_complexity(task_text, task_needs)
    cap = model_score(model_name, task_needs)
    gap = complexity["score"] - cap["score"]
    threshold = settings.DEFERRED_QUEUE_MIN_GAP if min_gap is None else min_gap
    if gap >= threshold:
        return {
            "decision": "defer",
            "deferred": True,
            "reason": f"complexity {complexity['score']} > capability {cap['score']} (gap {gap} >= {threshold})",
            "complexity": complexity,
            "capability": cap,
        }
    return {
        "decision": "assign",
        "deferred": False,
        "reason": f"within capability (gap {gap} < {threshold})",
        "complexity": complexity,
        "capability": cap,
    }
