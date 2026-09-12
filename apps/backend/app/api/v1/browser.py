"""Browser sessions API - REST mirror of the live in-memory sessions (process manager)."""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any

from app.services.browser_service import browser_service

router = APIRouter(prefix="/browser", tags=["browser"])


@router.get("/sessions", response_model=List[Dict[str, Any]])
async def list_sessions():
    """Live browser tabs (AI-controlled). Screenshots excluded (use WS frames)."""
    out = []
    for sid, s in browser_service.sessions.items():
        out.append({
            "id": sid,
            "url": s.url,
            "title": s.title,
            "status": s.status,
            "actions_pending": s.actions_pending,
            "created_at": s.created_at,
        })
    return out


@router.post("/sessions/{session_id}/close", response_model=Dict[str, Any])
async def close_session(session_id: str):
    """Kill a browser tab."""
    if not await browser_service.close_session(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    return {"id": session_id, "status": "closed"}
