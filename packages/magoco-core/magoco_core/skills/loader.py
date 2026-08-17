"""Skill Loader - Parses .skill.md files with YAML frontmatter and loads modules."""

import re
import yaml
import importlib.util
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import asdict

from magoco_core.skills.registry import (
    Skill, SkillMetadata, SkillRegistry, SkillCategory, SkillScope,
    SkillEntryPoint, SkillParameter, SkillDependency, skill_registry
)


class SkillLoader:
    """Loads skills from .skill.md files."""
    
    FRONTMATTER_PATTERN = re.compile(r'^---\n(.*?)\n---', re.DOTALL)
    
    def __init__(self, registry: Optional[SkillRegistry] = None):
        self.registry = registry or skill_registry
    
    def parse_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """Parse YAML frontmatter from skill file."""
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            return {}, content
        
        frontmatter_str = match.group(1)
        body = content[match.end():].lstrip()
        
        try:
            metadata = yaml.safe_load(frontmatter_str) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML frontmatter: {e}")
        
        return metadata, body
    
    def metadata_from_dict(self, data: Dict[str, Any]) -> SkillMetadata:
        """Convert dict to SkillMetadata with proper enums."""
        # Convert enums
        if "category" in data and isinstance(data["category"], str):
            data["category"] = SkillCategory(data["category"])
        if "scope" in data and isinstance(data["scope"], str):
            data["scope"] = SkillScope(data["scope"])
        
        # Convert entry_points
        if "entry_points" in data:
            eps = []
            for ep in data["entry_points"]:
                params = []
                for p in ep.get("parameters", []):
                    params.append(SkillParameter(**p))
                ep["parameters"] = params
                eps.append(SkillEntryPoint(**ep))
            data["entry_points"] = eps
        
        # Convert dependencies
        if "dependencies" in data:
            deps = [SkillDependency(**d) for d in data["dependencies"]]
            data["dependencies"] = deps
        
        return SkillMetadata(**data)
    
    def load_skill_file(self, filepath: Path) -> Optional[Skill]:
        """Load a single .skill.md file."""
        content = filepath.read_text(encoding="utf-8")
        metadata_dict, body = self.parse_frontmatter(content)
        
        if not metadata_dict:
            return None
        
        # Ensure required fields
        if "name" not in metadata_dict:
            metadata_dict["name"] = filepath.stem
        if "version" not in metadata_dict:
            metadata_dict["version"] = "1.0.0"
        if "description" not in metadata_dict:
            metadata_dict["description"] = ""
        
        metadata = self.metadata_from_dict(metadata_dict)
        metadata.path = str(filepath)
        metadata.source = "local"
        
        skill = Skill(metadata=metadata)
        
        # Load Python module if exists (same name .py file)
        py_file = filepath.with_suffix(".py")
        if py_file.exists():
            skill.module = self._load_module(py_file)
            self._register_handlers(skill, body)
        
        # Also check for handlers in the markdown body (code blocks)
        self._extract_handlers_from_markdown(skill, body)
        
        return skill
    
    def _load_module(self, py_file: Path) -> Any:
        """Load Python module from file."""
        spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[py_file.stem] = module
            spec.loader.exec_module(module)
            return module
        return None
    
    def _register_handlers(self, skill: Skill, body: str):
        """Register handlers from loaded module."""
        if not skill.module:
            return
        
        for ep in skill.metadata.entry_points:
            handler_name = ep.handler.split(":")[-1] if ":" in ep.handler else ep.handler
            if hasattr(skill.module, handler_name):
                handler = getattr(skill.module, handler_name)
                skill.set_handler(ep.name, handler)
    
    def _extract_handlers_from_markdown(self, skill: Skill, body: str):
        """Extract handler functions from markdown code blocks."""
        # Look for ```python code blocks with handler functions
        code_blocks = re.findall(r'```python\n(.*?)\n```', body, re.DOTALL)
        for block in code_blocks:
            # Execute in a namespace to find handler functions
            namespace = {}
            try:
                exec(block, namespace)
                for ep in skill.metadata.entry_points:
                    handler_name = ep.handler.split(":")[-1] if ":" in ep.handler else ep.handler
                    if handler_name in namespace:
                        skill.set_handler(ep.name, namespace[handler_name])
            except Exception:
                pass  # Ignore invalid code blocks
    
    def load_from_directory(self, directory: Path) -> List[Skill]:
        """Load all .skill.md files from directory."""
        skills = []
        for skill_file in directory.rglob("*.skill.md"):
            try:
                skill = self.load_skill_file(skill_file)
                if skill:
                    self.registry.register(skill)
                    skills.append(skill)
            except Exception as e:
                print(f"Failed to load skill {skill_file}: {e}")
        return skills
    
    def discover_skills(self, paths: List[Path] = None) -> List[Skill]:
        """Discover skills from multiple paths."""
        if paths is None:
            paths = [self.registry.skills_dir]
        
        all_skills = []
        for path in paths:
            if path.exists():
                all_skills.extend(self.load_from_directory(path))
        return all_skills


# Convenience function
def load_skill(filepath: Path) -> Optional[Skill]:
    """Load a single skill file."""
    return SkillLoader().load_skill_file(filepath)