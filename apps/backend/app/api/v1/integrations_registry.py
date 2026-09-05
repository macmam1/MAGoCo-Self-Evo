"""Integrations Registry API - marketplace + instances + webhooks."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from magoco_core.integrations import get_integrations_registry
from magoco_core.integrations.models import IntegrationSearchQuery, IntegrationCategory

router = APIRouter(prefix="/integrations-registry", tags=["integrations-registry"])


class SearchRequest(BaseModel):
    query: str = ""
    category: Optional[str] = None
    free_only: bool = False
    featured_only: bool = False
    page: int = 1
    page_size: int = 20


@router.get("/stats")
async def registry_stats():
    reg = get_integrations_registry()
    return reg.get_stats()


@router.post("/search")
async def search_integrations(req: SearchRequest):
    reg = get_integrations_registry()
    cat = None
    if req.category:
        try:
            cat = IntegrationCategory(req.category)
        except ValueError:
            raise HTTPException(status_code=400, detail="invalid category")
    q = IntegrationSearchQuery(
        query=req.query, category=cat,
        free_only=req.free_only, featured_only=req.featured_only,
        page=req.page, page_size=req.page_size,
    )
    results = reg.search(q)
    return [{"integration": r.integration.to_dict(), "score": r.score} for r in results]


@router.get("/templates")
async def list_templates():
    from magoco_core.integrations.models import CONNECTOR_TEMPLATES
    return [
        {"id": t.id, "name": t.name, "description": t.description,
         "category": t.category.value, "difficulty": t.difficulty, "tags": t.tags}
        for t in CONNECTOR_TEMPLATES
    ]


@router.post("/seed")
async def seed_integrations():
    from app.services.integrations.seed import seed_registry
    return seed_registry()


@router.get("/{integration_id}")
async def get_integration(integration_id: str):
    reg = get_integrations_registry()
    m = reg.get(integration_id)
    if not m:
        raise HTTPException(status_code=404, detail="not found")
    return m.to_dict()
