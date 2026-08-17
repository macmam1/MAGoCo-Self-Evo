"""Skill System - Core definitions and registry.

Inspired by Hermes Agent's skill system with YAML frontmatter.
"""

import os
import yaml
import uuid
import shutil
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Callable, Awaitable
from datetime import datetime
from enum import Enum


class SkillCategory(str, Enum):
    """Standard skill categories."""
    AGENT = "agent"           # Agent behaviors, prompts
    TOOL = "tool"             # Tool definitions
    WORKFLOW = "workflow"     # Workflow templates
    INTEGRATION = "integration"  # 3rd party integrations
    MEMORY = "memory"         # Memory strategies
    EVOLUTION = "evolution"   # Self-evolution patterns
    UTILITY = "utility"       # Helper skills
    CUSTOM = "custom"         # User-defined


class SkillScope(str, Enum):
    """Where the skill applies."""
    GLOBAL = "global"         # Available to all agents
    AGENT = "agent"           # Specific agent type
    WORKFLOW = "workflow"     # Specific workflow
    USER = "user"             # User-specific


@dataclass
class SkillParameter:
    """Parameter definition for skill configuration."""
    name: str
    type: str = "string"
    description: str = ""
    required: bool = False
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class SkillEntryPoint:
    """Entry point for skill execution."""
    name: str
    description: str
    handler: str  # Module:function path
    parameters: List[SkillParameter] = field(default_factory=list)
    returns: str = "any"


@dataclass
class SkillDependency:
    """Skill dependency on other skills or packages."""
    name: str
    version: str = "*"
    type: str = "skill"  # skill, pip, npm, system
    optional: bool = False


@dataclass
class SkillMetadata:
    """Complete skill metadata from frontmatter."""
    # Required
    name: str
    version: str
    description: str
    category: SkillCategory = SkillCategory.CUSTOM
    
    # Optional
    author: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Compatibility
    min_magoco_version: str = "0.1.0"
    max_magoco_version: str = ""
    python_version: str = ">=3.10"
    
    # Runtime
    scope: SkillScope = SkillScope.GLOBAL
    entry_points: List[SkillEntryPoint] = field(default_factory=list)
    dependencies: List[SkillDependency] = field(default_factory=list)
    
    # Configuration
    config_schema: Dict[str, Any] = field(default_factory=dict)
    default_config: Dict[str, Any] = field(default_factory=dict)
    
    # Lifecycle
    on_install: Optional[str] = None      # handler path
    on_uninstall: Optional[str] = None
    on_enable: Optional[str] = None
    on_disable: Optional[str] = None
    
    # Internal
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    installed_at: Optional[str] = None
    updated_at: Optional[str] = None
    enabled: bool = True
    source: str = "local"  # local, github, marketplace
    path: str = ""


@dataclass
class Skill:
    """Complete skill with metadata and loaded module."""
    metadata: SkillMetadata
    module: Any = None
    config: Dict[str, Any] = field(default_factory=dict)
    _handlers: Dict[str, Callable] = field(default_factory=dict)
    
    def get_handler(self, entry_point: str) -> Optional[Callable]:
        """Get handler function for entry point."""
        return self._handlers.get(entry_point)
    
    def set_handler(self, entry_point: str, handler: Callable):
        """Register a handler for entry point."""
        self._handlers[entry_point] = handler
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize for storage."""
        return {
            "metadata": asdict(self.metadata),
            "config": self.config,
        }


class SkillRegistry:
    """Central registry for all skills."""
    
    def __init__(self, skills_dir: Optional[str] = None):
        self.skills: Dict[str, Skill] = {}
        self.skills_dir = Path(skills_dir) if skills_dir else Path.home() / ".magoco" / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._category_index: Dict[SkillCategory, List[str]] = {}
        self._scope_index: Dict[SkillScope, List[str]] = {}
    
    def _rebuild_indexes(self):
        """Rebuild category and scope indexes."""
        self._category_index = {cat: [] for cat in SkillCategory}
        self._scope_index = {scope: [] for scope in SkillScope}
        for skill_id, skill in self.skills.items():
            self._category_index[skill.metadata.category].append(skill_id)
            self._scope_index[skill.metadata.scope].append(skill_id)
    
    def register(self, skill: Skill) -> bool:
        """Register a skill."""
        skill_id = skill.metadata.name
        if skill_id in self.skills:
            return False
        self.skills[skill_id] = skill
        self._rebuild_indexes()
        return True
    
    def unregister(self, skill_id: str) -> bool:
        """Unregister a skill."""
        if skill_id not in self.skills:
            return False
        del self.skills[skill_id]
        self._rebuild_indexes()
        return True
    
    def get(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID."""
        return self.skills.get(skill_id)
    
    def list_skills(
        self,
        category: Optional[SkillCategory] = None,
        scope: Optional[SkillScope] = None,
        enabled_only: bool = True
    ) -> List[Skill]:
        """List skills with optional filters."""
        skills = list(self.skills.values())
        if enabled_only:
            skills = [s for s in skills if s.metadata.enabled]
        if category:
            skills = [s for s in skills if s.metadata.category == category]
        if scope:
            skills = [s for s in skills if s.metadata.scope == scope]
        return skills
    
    def get_by_category(self, category: SkillCategory) -> List[Skill]:
        """Get skills by category."""
        return [self.skills[sid] for sid in self._category_index.get(category, []) if sid in self.skills]
    
    def get_by_scope(self, scope: SkillScope) -> List[Skill]:
        """Get skills by scope."""
        return [self.skills[sid] for sid in self._scope_index.get(scope, []) if sid in self.skills]
    
    def enable(self, skill_id: str) -> bool:
        """Enable a skill."""
        skill = self.skills.get(skill_id)
        if not skill:
            return False
        skill.metadata.enabled = True
        return True
    
    def disable(self, skill_id: str) -> bool:
        """Disable a skill."""
        skill = self.skills.get(skill_id)
        if not skill:
            return False
        skill.metadata.enabled = False
        return True


# Global registry instance
skill_registry = SkillRegistry()