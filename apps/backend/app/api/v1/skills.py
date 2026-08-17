"""Skills management API - install, list, enable, disable, configure skills."""

from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

import sys
sys.path.insert(0, "/tmp/MAGoCo-Self-Evo/packages/magoco-core")
from magoco_core.skills import (
    skill_registry, SkillLoader, SkillCategory, SkillScope,
)

router = APIRouter(prefix="/skills", tags=["skills"])
loader = SkillLoader()

# Load skills from disk on startup
SKILLS_DIR = Path("/tmp/MAGoCo-Self-Evo/packages/magoco-core/skills")
loader.discover_skills([SKILLS_DIR])


class SkillResponse(BaseModel):
    id: str
    name: str
    version: str
    description: str
    category: str
    scope: str
    tags: List[str]
    enabled: bool
    entry_points: List[Dict[str, Any]]
    source: str = "local"
    author: str = ""
    license: str = "MIT"


class SkillInstallRequest(BaseModel):
    name: str
    source: str = "local"  # local, github, marketplace
    path: Optional[str] = None


@router.get("/", response_model=List[SkillResponse])
async def list_skills(
    category: Optional[str] = Query(None),
    scope: Optional[str] = Query(None),
    enabled_only: bool = Query(True),
):
    """List all available skills."""
    cat = SkillCategory(category) if category else None
    scp = SkillScope(scope) if scope else None
    skills = skill_registry.list_skills(category=cat, scope=scp, enabled_only=enabled_only)
    
    return [
        SkillResponse(
            id=s.metadata.id,
            name=s.metadata.name,
            version=s.metadata.version,
            description=s.metadata.description,
            category=s.metadata.category.value,
            scope=s.metadata.scope.value,
            tags=s.metadata.tags,
            enabled=s.metadata.enabled,
            entry_points=[
                {"name": ep.name, "description": ep.description}
                for ep in s.metadata.entry_points
            ],
            source=s.metadata.source,
            author=s.metadata.author,
            license=s.metadata.license,
        )
        for s in skills
    ]


@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    """Get details of a specific skill."""
    skill = skill_registry.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return {
        "id": skill.metadata.id,
        "name": skill.metadata.name,
        "version": skill.metadata.version,
        "description": skill.metadata.description,
        "category": skill.metadata.category.value,
        "scope": skill.metadata.scope.value,
        "tags": skill.metadata.tags,
        "enabled": skill.metadata.enabled,
        "entry_points": [
            {
                "name": ep.name,
                "description": ep.description,
                "parameters": [
                    {"name": p.name, "type": p.type, "required": p.required, "description": p.description}
                    for p in ep.parameters
                ],
                "returns": ep.returns,
            }
            for ep in skill.metadata.entry_points
        ],
        "dependencies": [
            {"name": d.name, "version": d.version, "type": d.type}
            for d in skill.metadata.dependencies
        ],
        "config_schema": skill.metadata.config_schema,
        "default_config": skill.metadata.default_config,
        "source": skill.metadata.source,
        "path": skill.metadata.path,
        "author": skill.metadata.author,
        "license": skill.metadata.license,
        "homepage": skill.metadata.homepage,
    }


@router.post("/{skill_id}/enable")
async def enable_skill(skill_id: str):
    """Enable a skill."""
    if skill_registry.enable(skill_id):
        return {"status": "enabled", "skill_id": skill_id}
    raise HTTPException(status_code=404, detail="Skill not found")


@router.post("/{skill_id}/disable")
async def disable_skill(skill_id: str):
    """Disable a skill."""
    if skill_registry.disable(skill_id):
        return {"status": "disabled", "skill_id": skill_id}
    raise HTTPException(status_code=404, detail="Skill not found")


@router.delete("/{skill_id}")
async def uninstall_skill(skill_id: str):
    """Uninstall a skill."""
    if skill_registry.unregister(skill_id):
        return {"status": "uninstalled", "skill_id": skill_id}
    raise HTTPException(status_code=404, detail="Skill not found")


@router.post("/reload")
async def reload_skills():
    """Reload all skills from disk."""
    loaded = loader.discover_skills([SKILLS_DIR])
    return {
        "status": "reloaded",
        "count": len(loaded),
        "names": [s.metadata.name for s in loaded],
    }


@router.get("/categories/list")
async def list_categories():
    """List available skill categories."""
    return [
        {"value": cat.value, "count": len(skill_registry.get_by_category(cat))}
        for cat in SkillCategory
    ]