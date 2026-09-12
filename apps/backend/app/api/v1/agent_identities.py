"""Agent identities API - issue scoped keys, verify, revoke."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from magoco_core.agents.identities import get_identity_store, DEFAULT_SCOPES
from app.api.deps import get_identity

router = APIRouter(prefix="/agent-identities", tags=["agent-identities"])


class AgentCreate(BaseModel):
    name: str
    owner: str = "system"
    scopes: Optional[List[str]] = None


@router.post("/", response_model=Dict[str, Any])
async def create_agent(req: AgentCreate):
    """Issue a new agent identity. The api_key is shown ONCE — store it now."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="name required")
    rec = get_identity_store().create(req.name, req.owner, req.scopes or list(DEFAULT_SCOPES))
    return rec


@router.get("/", response_model=List[Dict[str, Any]])
async def list_agents():
    """List identities (secrets never leave the server)."""
    return get_identity_store().list()


@router.get("/me", response_model=Dict[str, Any])
async def who_am_i(ident: dict = Depends(get_identity)):
    """Verify a credential (JWT or agent key) and show what it resolves to."""
    return ident


@router.delete("/{agent_id}", response_model=Dict[str, Any])
async def revoke_agent(agent_id: str):
    """Revoke an agent identity. Outstanding keys stop working immediately."""
    if not get_identity_store().revoke(agent_id):
        raise HTTPException(status_code=404, detail="agent not found or already revoked")
    return {"id": agent_id, "status": "revoked"}
