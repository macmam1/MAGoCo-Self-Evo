"""Skill auto-detection — the OS suggests/activates skills by itself.

Three layers (safe by default):
1. suggest_for_text(): deterministic keyword/tag/category scoring over the
   registry. No LLM needed, no false API calls.
2. suggest_for_project(): project_type (blueprint) -> skill categories/tags.
   Used at project start to pre-activate relevant skills.
3. skill_search agent tool: runtime discovery mid-run (Claude Code's
   ToolSearchTool lesson) — agents find skills when the task needs them.

All suggestions are ADVISORY unless auto_activate=True is explicitly passed
(and the project bootstrap passes it only when the kill-switch allows).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from magoco_core.skills.models import SkillSearchQuery

_WORD_RE = re.compile(r"[a-zA-Z\u0600-\u06FF0-9]{3,}")


@dataclass
class SkillSuggestion:
    skill_id: str
    display_name: str
    category: str
    score: float
    matched: List[str] = field(default_factory=list)
    reason: str = ""


def _keywords(text: str) -> set:
    return set(_WORD_RE.findall((text or "").lower()))


def suggest_for_text(text: str, top_k: int = 5,
                     registry=None) -> List[SkillSuggestion]:
    """Score registry skills against free text (task, message, goal)."""
    from magoco_core.skills import get_skills_registry
    reg = registry or get_skills_registry()
    try:
        manifests = [r.skill for r in reg.search(SkillSearchQuery(query="", page_size=500))]
    except Exception:
        return []
    words = _keywords(text)
    out: List[SkillSuggestion] = []
    for m in manifests:
        hay = _keywords(f"{m.name} {m.display_name} {m.description} {' '.join(m.tags)}")
        hit = words & hay
        if not hit:
            continue
        # Tag hits weigh more than description hits
        tag_hit = words & {t.lower() for t in m.tags}
        score = round(len(tag_hit) * 2.0 + len(hit) * 0.5, 2)
        out.append(SkillSuggestion(
            skill_id=m.id, display_name=m.display_name,
            category=m.category.value if hasattr(m.category, "value") else str(m.category),
            score=score, matched=sorted(hit)[:8],
            reason=f"matched: {', '.join(sorted(hit)[:5])}"))
    out.sort(key=lambda s: -s.score)
    return out[:top_k]


# Project type -> skill tags/categories to pre-activate at project start.
PROJECT_SKILL_MAP: Dict[str, Dict[str, List[str]]] = {
    "web_app": {"tags": ["frontend", "testing", "seo-audit", "playwright", "review"],
                "categories": ["development"]},
    "game": {"tags": ["testing", "review", "planning"],
             "categories": ["development"]},
    "saas": {"tags": ["stripe", "payments", "testing", "seo-audit", "review", "security"],
             "categories": ["development", "security", "api_integration"]},
    "api_service": {"tags": ["testing", "review", "security", "debugging"],
                    "categories": ["development", "security"]},
    "generic": {"tags": ["planning", "review", "testing"],
                "categories": ["development", "productivity"]},
}


def suggest_for_project(project_type: str, goal: str = "",
                        top_k: int = 8, registry=None) -> List[SkillSuggestion]:
    """Skills to activate when a project of this type starts."""
    from magoco_core.skills import get_skills_registry
    from magoco_core.skills.models import SkillCategory
    reg = registry or get_skills_registry()
    mapping = PROJECT_SKILL_MAP.get(project_type, PROJECT_SKILL_MAP["generic"])
    want_tags = {t.lower() for t in mapping["tags"]}
    want_cats = set(mapping["categories"])
    goal_words = _keywords(goal)

    try:
        manifests = [r.skill for r in reg.search(SkillSearchQuery(query="", page_size=500))]
    except Exception:
        return []
    out: List[SkillSuggestion] = []
    for m in manifests:
        cat = m.category.value if hasattr(m.category, "value") else str(m.category)
        tags = {t.lower() for t in m.tags}
        score = 0.0
        matched: List[str] = []
        tag_hit = tags & want_tags
        if tag_hit:
            score += len(tag_hit) * 3.0
            matched += sorted(tag_hit)
        if cat in want_cats:
            score += 1.0
        gw = goal_words & _keywords(f"{m.name} {m.display_name} {m.description} {' '.join(m.tags)}")
        if gw:
            score += len(gw) * 0.5
            matched += sorted(gw)[:4]
        if score > 0:
            out.append(SkillSuggestion(
                skill_id=m.id, display_name=m.display_name, category=cat,
                score=round(score, 2), matched=matched[:8],
                reason=f"project_type={project_type}"))
    out.sort(key=lambda s: -s.score)
    return out[:top_k]
