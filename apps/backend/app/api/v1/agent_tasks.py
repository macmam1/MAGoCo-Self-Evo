"""Agent Tasks API - background one-shots + cron schedules (durable)."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from magoco_core.agents.scheduler import get_scheduler, cron_due
from magoco_core.core.config import settings

router = APIRouter(prefix="/agent-tasks", tags=["agent-tasks"])


class BackgroundRequest(BaseModel):
    agent_name: str = "default"
    task: str
    provider_id: str = ""
    model: str = ""


class ScheduleCreate(BaseModel):
    agent_name: str = "default"
    task: str
    cron: str = "*/30 * * * *"
    provider_id: str = ""
    model: str = ""


def _guard() -> None:
    if not settings.SCHEDULER_ENABLED:
        raise HTTPException(status_code=403, detail="Scheduler disabled (SCHEDULER_ENABLED=false)")


@router.post("/background", response_model=Dict[str, Any])
async def start_background(req: BackgroundRequest):
    """Start a background task. Returns run id immediately; poll for result."""
    _guard()
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="task required")
    rid = await get_scheduler().run_background(req.agent_name, req.task,
                                               req.provider_id, req.model)
    return {"run_id": rid, "status": "running"}


@router.get("/background/{run_id}", response_model=Dict[str, Any])
async def check_background(run_id: str):
    run = get_scheduler().get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/runs", response_model=List[Dict[str, Any]])
async def list_runs(limit: int = 50):
    """Reviewable history of background + scheduled runs."""
    return get_scheduler().list_runs(limit)


@router.post("/schedules", response_model=Dict[str, Any])
async def create_schedule(req: ScheduleCreate):
    """Create a cron schedule (persisted across restarts)."""
    _guard()
    if not req.task.strip():
        raise HTTPException(status_code=400, detail="task required")
    try:
        return get_scheduler().add_schedule(req.agent_name, req.task, req.cron,
                                            req.provider_id, req.model)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/schedules", response_model=List[Dict[str, Any]])
async def list_schedules(enabled_only: bool = False):
    return get_scheduler().list_schedules(enabled_only)


@router.get("/schedules/{sid}", response_model=Dict[str, Any])
async def get_schedule(sid: str):
    s = get_scheduler().get_schedule(sid)
    if not s:
        raise HTTPException(status_code=404, detail="schedule not found")
    return s


@router.patch("/schedules/{sid}", response_model=Dict[str, Any])
async def toggle_schedule(sid: str, enabled: bool = True):
    if not get_scheduler().set_enabled(sid, enabled):
        raise HTTPException(status_code=404, detail="schedule not found")
    return get_scheduler().get_schedule(sid)


@router.delete("/schedules/{sid}")
async def delete_schedule(sid: str):
    if not get_scheduler().delete_schedule(sid):
        raise HTTPException(status_code=404, detail="schedule not found")
    return {"success": True}


@router.post("/cron-check", response_model=Dict[str, Any])
async def check_cron(cron: str):
    """Validate a cron expression + whether it fires right now."""
    try:
        return {"valid": True, "due_now": cron_due(cron)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status", response_model=Dict[str, Any])
async def scheduler_status():
    return {"enabled": settings.SCHEDULER_ENABLED,
            "tick_seconds": settings.SCHEDULER_TICK_SECONDS,
            "toggle_via": "env SCHEDULER_ENABLED=false"}
