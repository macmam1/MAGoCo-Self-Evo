"""Approvals API - matches ApprovalGates frontend contract + growth gating."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from magoco_core.evolution.approvals_store import get_approvals_store

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalCreate(BaseModel):
    agent_name: str = "unknown-agent"
    action_description: str = ""
    proposed_input: Dict[str, Any] = {}


class ApprovalResolve(BaseModel):
    status: str = "approved"
    comment: Optional[str] = None
    decided_by: str = "human"


@router.get("/pending")
async def list_pending():
    store = get_approvals_store()
    return store.list(status="pending")


@router.get("/")
async def list_all(status: Optional[str] = None, limit: int = 100):
    store = get_approvals_store()
    return store.list(status=status, limit=limit)


@router.post("/")
async def create_approval(req: ApprovalCreate):
    store = get_approvals_store()
    return store.create(req.agent_name, req.action_description, req.proposed_input)


@router.get("/{request_id}")
async def get_approval(request_id: str):
    store = get_approvals_store()
    r = store.get(request_id)
    if not r:
        raise HTTPException(status_code=404, detail="not found")
    return r


@router.post("/sweep-expired")
async def sweep_expired(limit: int = 100):
    """Auto-expire stale pending approvals (housekeeping; safe to cron)."""
    store = get_approvals_store()
    return {"expired": store.sweep_expired(limit)}


@router.post("/{request_id}/resolve")
async def resolve_approval(request_id: str, req: ApprovalResolve):
    store = get_approvals_store()
    # side-effect: mirror growth suggestion status
    r = store.get(request_id)
    if not r:
        raise HTTPException(status_code=404, detail="not found")
    try:
        out = store.resolve(request_id, req.status, req.comment,
                            decided_by=req.decided_by or "human")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    sid = (r.get("proposed_input") or {}).get("suggestion_id")
    if sid:
        try:
            from magoco_core.growth import get_growth_engine
            eng = get_growth_engine()
            eng.set_suggestion_status(sid, "approved" if req.status == "approved" else "rejected")
        except Exception:
            pass
    return out
