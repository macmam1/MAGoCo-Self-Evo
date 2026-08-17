"""Skills module — registry, loader, and utilities."""

from magoco_core.skills.registry import (
    SkillRegistry,
    Skill,
    SkillMetadata,
    SkillCategory,
    SkillScope,
    SkillEntryPoint,
    SkillParameter,
    SkillDependency,
    skill_registry,
)

from magoco_core.skills.loader import SkillLoader, load_skill

__all__ = [
    "SkillRegistry",
    "Skill",
    "SkillMetadata",
    "SkillCategory",
    "SkillScope",
    "SkillEntryPoint",
    "SkillParameter",
    "SkillDependency",
    "skill_registry",
    "SkillLoader",
    "load_skill",
]