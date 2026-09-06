"""Provider Groups API - Group providers for team-based routing."""

from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from magoco_core.llm.registry import get_provider_registry
from magoco_core.llm.groups import get_group_store

router = APIRouter(prefix="/provider-groups", tags=["provider-groups"])


# ===== Models =====

class ProviderGroupCreate(BaseModel):
    name: str
    description: str = ""
    provider_ids: List[str] = []  # List of provider IDs in this group
    default_model: str = ""
    task_routing: Dict[str, str] = {}  # task_type -> provider_id/model
    metadata: Dict[str, Any] = {}


class ProviderGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    provider_ids: Optional[List[str]] = None
    default_model: Optional[str] = None
    task_routing: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Any]] = None


class GroupRecommendation(BaseModel):
    group_id: str
    group_name: str
    reason: str
    confidence: float


# ===== Persistent storage (SQLite — survives restarts) =====

def _get_group(group_id: str) -> Dict[str, Any]:
    group = get_group_store().get(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def _validate_providers(provider_ids: List[str]) -> List[str]:
    """Validate that all provider IDs exist in registry."""
    reg = get_provider_registry()
    valid = []
    for pid in provider_ids:
        if reg.get(pid):
            valid.append(pid)
        else:
            raise HTTPException(status_code=400, detail=f"Provider not found: {pid}")
    return valid


# ===== CRUD =====

@router.post("/", response_model=Dict[str, Any])
async def create_group(req: ProviderGroupCreate):
    """Create a new provider group."""
    import uuid
    validated_ids = _validate_providers(req.provider_ids)

    group_id = req.name.lower().strip().replace(" ", "-") or uuid.uuid4().hex[:8]
    if get_group_store().get(group_id):
        raise HTTPException(status_code=400, detail="Group with this name already exists")

    group = {
        "id": group_id,
        "name": req.name,
        "description": req.description,
        "provider_ids": validated_ids,
        "default_model": req.default_model,
        "task_routing": req.task_routing,
        "metadata": req.metadata,
    }
    return get_group_store().create(group)


@router.get("/", response_model=List[Dict[str, Any]])
async def list_groups():
    """List all provider groups."""
    return get_group_store().list()


@router.get("/{group_id}", response_model=Dict[str, Any])
async def get_group(group_id: str):
    """Get a specific provider group."""
    return _get_group(group_id)


@router.patch("/{group_id}", response_model=Dict[str, Any])
async def update_group(group_id: str, req: ProviderGroupUpdate):
    """Update a provider group."""
    _get_group(group_id)  # 404 if missing
    fields = req.model_dump(exclude_none=True)
    if "provider_ids" in fields:
        fields["provider_ids"] = _validate_providers(fields["provider_ids"])
    updated = get_group_store().update(group_id, fields)
    return updated


@router.delete("/{group_id}")
async def delete_group(group_id: str):
    """Delete a provider group."""
    if get_group_store().delete(group_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Group not found")


# ===== Smart Routing =====

@router.post("/{group_id}/route", response_model=Dict[str, Any])
async def route_task(group_id: str, task_type: str, 
                      user_provider: Optional[str] = None,
                      user_model: Optional[str] = None):
    """Get the best provider/model for a task type within a group."""
    group = _get_group(group_id)
    reg = get_provider_registry()
    
    # Priority 1: User explicit choice
    if user_provider:
        cfg = reg.get(user_provider)
        if cfg and cfg.id in group["provider_ids"]:
            model = user_model or group.get("default_model") or (cfg.models[0] if cfg.models else "")
            return {
                "provider_id": cfg.id,
                "model": model,
                "reason": "user_specified",
                "confidence": 1.0
            }
    
    # Priority 2: Group task routing
    if task_type in group.get("task_routing", {}):
        route = group["task_routing"][task_type]
        # route format: "provider_id:model" or just "provider_id"
        parts = route.split(":", 1)
        provider_id = parts[0]
        model = parts[1] if len(parts) > 1 else group.get("default_model", "")
        cfg = reg.get(provider_id)
        if cfg and cfg.id in group["provider_ids"]:
            return {
                "provider_id": provider_id,
                "model": model or (cfg.models[0] if cfg.models else ""),
                "reason": "group_task_routing",
                "confidence": 0.9
            }
    
    # Priority 3: Group default model
    if group.get("default_model"):
        # Find provider that has this model
        for pid in group["provider_ids"]:
            cfg = reg.get(pid)
            if cfg and group["default_model"] in cfg.models:
                return {
                    "provider_id": cfg.id,
                    "model": group["default_model"],
                    "reason": "group_default_model",
                    "confidence": 0.7
                }
    
    # Priority 4: First available provider in group
    for pid in group["provider_ids"]:
        cfg = reg.get(pid)
        if cfg and await is_provider_available(cfg):
            model = cfg.models[0] if cfg.models else ""
            return {
                "provider_id": cfg.id,
                "model": model,
                "reason": "first_available",
                "confidence": 0.5
            }
    
    # Fallback: no provider available in group
    return {
        "provider_id": "",
        "model": "",
        "reason": "none_available",
        "confidence": 0.0,
        "error": "No available providers in group"
    }


@router.get("/{group_id}/recommendations", response_model=List[GroupRecommendation])
async def get_group_recommendations(group_id: str):
    """Get smart recommendations for which group to use for different tasks."""
    group = _get_group(group_id)
    reg = get_provider_registry()
    
    recommendations = []
    
    # Analyze providers in group for capabilities
    capabilities = {}
    for pid in group["provider_ids"]:
        cfg = reg.get(pid)
        if not cfg:
            continue
        for model in cfg.models:
            # This would use the ModelCapability system from llm.models
            pass
    
    return recommendations


async def is_provider_available(cfg) -> bool:
    """Check if a provider is currently available."""
    try:
        from magoco_core.llm.registry import get_provider_registry
        reg = get_provider_registry()
        runtime = reg.to_runtime(cfg)
        return await runtime.is_available()
    except Exception:
        return False